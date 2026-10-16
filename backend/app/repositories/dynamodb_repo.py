"""Amazon DynamoDB implementation of the repository (single-table design).

Key layout (see docs/PROJECT_DOCUMENTATION.md §11):

    PK                      SK                                        entity
    USER#<uid>              PROFILE                                   user (local auth only)
    EMAIL#<email>           EMAIL                                     email uniqueness guard
    USER#<uid>              EXPENSE#<id>                              expense  (GSI1: USER#<uid>#EXPENSE / <date>#<id>)
    USER#<uid>              BUDGET#<id>                               budget
    USER#<uid>              BUDGETALERT#<month>#<key>#<threshold>     budget threshold event (dedup)
    USER#<uid>              GOAL#<id>                                 savings goal
    USER#<uid>              ANOMALY#<id>                              anomaly alert
    USER#<uid>              ANOMALYKEY#<dedup_key>                    anomaly dedup guard
    USER#<uid>              RECEIPT#<id>                              receipt metadata
    USER#<uid>              PREFERENCES                               preferences

All user data shares the partition key USER#<uid>, so every query is scoped to
one user by construction and IAM policies can additionally restrict access
with dynamodb:LeadingKeys if desired.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from typing import Any, TypeVar

from pydantic import BaseModel

from app.domain.models import (
    AnomalyAlert,
    Budget,
    BudgetAlertEvent,
    Expense,
    Goal,
    Preferences,
    Receipt,
    User,
)
from app.errors import Conflict
from app.repositories.base import Repository

T = TypeVar("T", bound=BaseModel)
KEY_ATTRS = {"PK", "SK", "GSI1PK", "GSI1SK", "entity"}


def _to_item(model: BaseModel, **keys: str) -> dict[str, Any]:
    item = json.loads(model.model_dump_json(), parse_float=Decimal)
    item.update(keys)
    return item


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def _from_item(model: type[T], item: dict[str, Any]) -> T:
    return model.model_validate({k: _plain(v) for k, v in item.items() if k not in KEY_ATTRS})


def _user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


class DynamoDBRepository(Repository):
    def __init__(self, table_name: str, region: str, *, resource=None):
        import boto3
        from boto3.dynamodb.conditions import Key

        self._Key = Key
        self._resource = resource or boto3.resource("dynamodb", region_name=region)
        # The resource's client accepts plain Python values (it serializes them itself).
        self._client = self._resource.meta.client
        self.table = self._resource.Table(table_name)
        self.table_name = table_name

    # ---- helpers ----
    def _get(self, pk: str, sk: str) -> dict | None:
        return self.table.get_item(Key={"PK": pk, "SK": sk}).get("Item")

    def _delete(self, pk: str, sk: str) -> bool:
        resp = self.table.delete_item(Key={"PK": pk, "SK": sk}, ReturnValues="ALL_OLD")
        return "Attributes" in resp

    def _query_prefix(self, pk: str, prefix: str) -> list[dict]:
        items: list[dict] = []
        condition = self._Key("PK").eq(pk)
        if prefix:
            condition = condition & self._Key("SK").begins_with(prefix)
        kwargs = {"KeyConditionExpression": condition}
        while True:
            resp = self.table.query(**kwargs)
            items.extend(resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                return items
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    def _conditional_put(self, item: dict) -> bool:
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(SK)")
            return True
        except self._client.exceptions.ConditionalCheckFailedException:
            return False

    # ---- users ----
    def create_user(self, user: User) -> None:
        email = user.email.lower()
        try:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": {"PK": f"EMAIL#{email}", "SK": "EMAIL", "entity": "email", "user_id": user.id},
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": _to_item(user, PK=_user_pk(user.id), SK="PROFILE", entity="user"),
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                ]
            )
        except self._client.exceptions.TransactionCanceledException as exc:
            raise Conflict("An account with this email already exists.") from exc

    def get_user(self, user_id: str) -> User | None:
        item = self._get(_user_pk(user_id), "PROFILE")
        return _from_item(User, item) if item else None

    def get_user_by_email(self, email: str) -> User | None:
        guard = self._get(f"EMAIL#{email.lower()}", "EMAIL")
        return self.get_user(guard["user_id"]) if guard else None

    def update_user(self, user: User) -> None:
        self.table.put_item(Item=_to_item(user, PK=_user_pk(user.id), SK="PROFILE", entity="user"))

    # ---- expenses ----
    def put_expense(self, expense: Expense) -> None:
        self.table.put_item(
            Item=_to_item(
                expense,
                PK=_user_pk(expense.user_id),
                SK=f"EXPENSE#{expense.id}",
                GSI1PK=f"USER#{expense.user_id}#EXPENSE",
                GSI1SK=f"{expense.date.isoformat()}#{expense.id}",
                entity="expense",
            )
        )

    def get_expense(self, user_id: str, expense_id: str) -> Expense | None:
        item = self._get(_user_pk(user_id), f"EXPENSE#{expense_id}")
        return _from_item(Expense, item) if item else None

    def delete_expense(self, user_id: str, expense_id: str) -> bool:
        return self._delete(_user_pk(user_id), f"EXPENSE#{expense_id}")

    def list_expenses(self, user_id: str, start: dt.date | None = None, end: dt.date | None = None) -> list[Expense]:
        low = start.isoformat() if start else "0000-00-00"
        high = (end.isoformat() if end else "9999-12-31") + "#~"
        kwargs = {
            "IndexName": "GSI1",
            "KeyConditionExpression": self._Key("GSI1PK").eq(f"USER#{user_id}#EXPENSE")
            & self._Key("GSI1SK").between(low, high),
        }
        items: list[dict] = []
        while True:
            resp = self.table.query(**kwargs)
            items.extend(resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                break
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        return [_from_item(Expense, item) for item in items]

    # ---- budgets ----
    def put_budget(self, budget: Budget) -> None:
        self.table.put_item(Item=_to_item(budget, PK=_user_pk(budget.user_id), SK=f"BUDGET#{budget.id}", entity="budget"))

    def get_budget(self, user_id: str, budget_id: str) -> Budget | None:
        item = self._get(_user_pk(user_id), f"BUDGET#{budget_id}")
        return _from_item(Budget, item) if item else None

    def delete_budget(self, user_id: str, budget_id: str) -> bool:
        return self._delete(_user_pk(user_id), f"BUDGET#{budget_id}")

    def list_budgets(self, user_id: str) -> list[Budget]:
        return [_from_item(Budget, i) for i in self._query_prefix(_user_pk(user_id), "BUDGET#")]

    def record_budget_alert_event(self, event: BudgetAlertEvent) -> bool:
        sk = f"BUDGETALERT#{event.month}#{event.budget_key}#{event.threshold:03d}"
        return self._conditional_put(_to_item(event, PK=_user_pk(event.user_id), SK=sk, entity="budget_alert"))

    def list_budget_alert_events(self, user_id: str, month: str | None = None) -> list[BudgetAlertEvent]:
        prefix = f"BUDGETALERT#{month}#" if month else "BUDGETALERT#"
        return [_from_item(BudgetAlertEvent, i) for i in self._query_prefix(_user_pk(user_id), prefix)]

    def delete_budget_alert_events(self, user_id: str, month: str | None = None, budget_key: str | None = None) -> int:
        prefix = f"BUDGETALERT#{month}#" if month else "BUDGETALERT#"
        if month and budget_key:
            prefix += f"{budget_key}#"
        items = self._query_prefix(_user_pk(user_id), prefix)
        if budget_key and not month:
            items = [i for i in items if i.get("budget_key") == budget_key]
        with self.table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
        return len(items)

    # ---- goals ----
    def put_goal(self, goal: Goal) -> None:
        self.table.put_item(Item=_to_item(goal, PK=_user_pk(goal.user_id), SK=f"GOAL#{goal.id}", entity="goal"))

    def get_goal(self, user_id: str, goal_id: str) -> Goal | None:
        item = self._get(_user_pk(user_id), f"GOAL#{goal_id}")
        return _from_item(Goal, item) if item else None

    def delete_goal(self, user_id: str, goal_id: str) -> bool:
        return self._delete(_user_pk(user_id), f"GOAL#{goal_id}")

    def list_goals(self, user_id: str) -> list[Goal]:
        return [_from_item(Goal, i) for i in self._query_prefix(_user_pk(user_id), "GOAL#")]

    # ---- anomaly alerts ----
    def create_alert_if_absent(self, alert: AnomalyAlert) -> bool:
        pk = _user_pk(alert.user_id)
        try:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": {"PK": pk, "SK": f"ANOMALYKEY#{alert.dedup_key}", "entity": "anomaly_key", "alert_id": alert.id},
                            "ConditionExpression": "attribute_not_exists(SK)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": _to_item(alert, PK=pk, SK=f"ANOMALY#{alert.id}", entity="anomaly"),
                        }
                    },
                ]
            )
            return True
        except self._client.exceptions.TransactionCanceledException:
            return False

    def put_alert(self, alert: AnomalyAlert) -> None:
        self.table.put_item(Item=_to_item(alert, PK=_user_pk(alert.user_id), SK=f"ANOMALY#{alert.id}", entity="anomaly"))

    def get_alert(self, user_id: str, alert_id: str) -> AnomalyAlert | None:
        item = self._get(_user_pk(user_id), f"ANOMALY#{alert_id}")
        return _from_item(AnomalyAlert, item) if item else None

    def delete_alert(self, user_id: str, alert_id: str) -> bool:
        alert = self.get_alert(user_id, alert_id)
        if not alert:
            return False
        self._delete(_user_pk(user_id), f"ANOMALYKEY#{alert.dedup_key}")
        return self._delete(_user_pk(user_id), f"ANOMALY#{alert_id}")

    def list_alerts(self, user_id: str) -> list[AnomalyAlert]:
        return [_from_item(AnomalyAlert, i) for i in self._query_prefix(_user_pk(user_id), "ANOMALY#")]

    # ---- receipts ----
    def put_receipt(self, receipt: Receipt) -> None:
        self.table.put_item(Item=_to_item(receipt, PK=_user_pk(receipt.user_id), SK=f"RECEIPT#{receipt.id}", entity="receipt"))

    def get_receipt(self, user_id: str, receipt_id: str) -> Receipt | None:
        item = self._get(_user_pk(user_id), f"RECEIPT#{receipt_id}")
        return _from_item(Receipt, item) if item else None

    def delete_receipt(self, user_id: str, receipt_id: str) -> bool:
        return self._delete(_user_pk(user_id), f"RECEIPT#{receipt_id}")

    def list_receipts(self, user_id: str) -> list[Receipt]:
        return [_from_item(Receipt, i) for i in self._query_prefix(_user_pk(user_id), "RECEIPT#")]

    # ---- preferences ----
    def get_preferences(self, user_id: str) -> Preferences | None:
        item = self._get(_user_pk(user_id), "PREFERENCES")
        return _from_item(Preferences, item) if item else None

    def put_preferences(self, prefs: Preferences) -> None:
        self.table.put_item(Item=_to_item(prefs, PK=_user_pk(prefs.user_id), SK="PREFERENCES", entity="preferences"))

    # ---- bulk ----
    def delete_all_user_data(self, user_id: str, *, include_user: bool = False) -> None:
        pk = _user_pk(user_id)
        user = self.get_user(user_id) if include_user else None
        items = self._query_prefix(pk, "")
        with self.table.batch_writer() as batch:
            for item in items:
                if item["SK"] == "PROFILE" and not include_user:
                    continue
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
            if user:
                batch.delete_item(Key={"PK": f"EMAIL#{user.email.lower()}", "SK": "EMAIL"})

    def health_check(self) -> bool:
        self.table.load()
        return True
