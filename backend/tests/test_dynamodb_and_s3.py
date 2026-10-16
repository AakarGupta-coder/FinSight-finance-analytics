"""DynamoDB and S3 implementations, tested against moto's in-memory AWS mocks.

No real AWS resources are created by these tests.
"""

import datetime as dt
import os

import boto3
import pytest
from moto import mock_aws

from app.domain.models import AnomalyAlert, Budget, BudgetAlertEvent, Expense, Goal, Preferences, Receipt, User
from app.errors import Conflict
from app.repositories.dynamodb_repo import DynamoDBRepository
from app.services.receipts.storage import S3ReceiptStorage

REGION = "ap-south-1"


@pytest.fixture
def aws_env(monkeypatch):
    for key, value in {"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing",
                       "AWS_DEFAULT_REGION": REGION}.items():
        monkeypatch.setenv(key, value)
    with mock_aws():
        yield


def create_table(name="finance-test"):
    client = boto3.client("dynamodb", region_name=REGION)
    client.create_table(
        TableName=name,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": n, "AttributeType": "S"} for n in ("PK", "SK", "GSI1PK", "GSI1SK")],
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        GlobalSecondaryIndexes=[{
            "IndexName": "GSI1",
            "KeySchema": [{"AttributeName": "GSI1PK", "KeyType": "HASH"}, {"AttributeName": "GSI1SK", "KeyType": "RANGE"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )
    return DynamoDBRepository(name, REGION)


def test_dynamodb_repository_roundtrip(aws_env):
    repo = create_table()
    user = User(id="u1", email="a@example.com", name="A", password_hash="h")
    repo.create_user(user)
    with pytest.raises(Conflict):
        repo.create_user(User(id="u2", email="A@example.com", name="B"))
    assert repo.get_user_by_email("a@example.com").id == "u1"

    e1 = Expense(user_id="u1", amount_minor=12345, date=dt.date(2026, 9, 1), category="food", description="a")
    e2 = Expense(user_id="u1", amount_minor=500, date=dt.date(2026, 10, 1), category="food", description="b")
    other = Expense(user_id="u2", amount_minor=1, date=dt.date(2026, 10, 1), category="food", description="c")
    for e in (e1, e2, other):
        repo.put_expense(e)
    assert repo.get_expense("u1", e1.id).amount_minor == 12345
    assert repo.get_expense("u2", e1.id) is None  # partition-key isolation
    assert {e.id for e in repo.list_expenses("u1")} == {e1.id, e2.id}
    assert [e.id for e in repo.list_expenses("u1", dt.date(2026, 9, 15), dt.date(2026, 10, 31))] == [e2.id]
    assert [e.id for e in repo.list_expenses("u1", dt.date(2026, 9, 1), dt.date(2026, 9, 1))] == [e1.id]

    e2.date = dt.date(2026, 8, 1)  # date change must move the GSI sort key
    repo.put_expense(e2)
    assert [e.id for e in repo.list_expenses("u1", dt.date(2026, 8, 1), dt.date(2026, 8, 31))] == [e2.id]

    b = Budget(user_id="u1", amount_minor=100, effective_from="2026-01")
    repo.put_budget(b)
    assert repo.list_budgets("u1")[0].id == b.id
    event = BudgetAlertEvent(user_id="u1", month="2026-10", budget_key="food", threshold=75, spent_minor=1, budget_minor=1)
    assert repo.record_budget_alert_event(event) is True
    assert repo.record_budget_alert_event(event) is False

    alert = AnomalyAlert(user_id="u1", expense_id=e1.id, rule="duplicate", dedup_key=f"duplicate:{e1.id}",
                         severity="medium", reason="r", comparison={"ratio": 2.5, "ids": ["x"]})
    assert repo.create_alert_if_absent(alert) is True
    assert repo.create_alert_if_absent(alert.model_copy(update={"id": "other"})) is False
    stored = repo.get_alert("u1", alert.id)
    assert stored.comparison == {"ratio": 2.5, "ids": ["x"]}
    assert repo.delete_alert("u1", alert.id)
    assert repo.create_alert_if_absent(alert) is True  # dedup guard removed with the alert

    goal = Goal(user_id="u1", name="G", target_minor=1000)
    repo.put_goal(goal)
    repo.put_receipt(Receipt(user_id="u1", storage_key="u1/" + "a" * 32 + ".png", content_type="image/png"))
    repo.put_preferences(Preferences(user_id="u1", currency="USD"))
    assert repo.get_preferences("u1").currency == "USD"

    repo.delete_all_user_data("u1", include_user=True)
    assert repo.list_expenses("u1") == [] and repo.list_goals("u1") == [] and repo.get_user("u1") is None
    assert repo.get_user_by_email("a@example.com") is None
    assert len(repo.list_expenses("u2")) == 1  # other user untouched


def test_full_api_on_dynamodb(aws_env, settings, tmp_path, today):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.services.receipts.storage import LocalReceiptStorage
    from tests.conftest import add_expense, register, headers

    repo = create_table("finance-api")
    client = TestClient(create_app(settings=settings, repo=repo, storage=LocalReceiptStorage(tmp_path / "r")))
    auth = headers(register(client))
    add_expense(client, auth, 4500, today, "food", "Lunch")
    assert client.get("/api/v1/expenses", headers=auth).json()["total_amount_minor"] == 4500
    assert client.post("/api/v1/demo-data", headers=auth).status_code == 200
    dash = client.get("/api/v1/dashboard", headers=auth)
    assert dash.status_code == 200 and dash.json()["summary"]["total_minor"] > 0


def test_s3_storage_private_presigned_flow(aws_env):
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket="receipts-test", CreateBucketConfiguration={"LocationConstraint": REGION})
    storage = S3ReceiptStorage("receipts-test", REGION, client=s3)
    key = "user-1/" + "b" * 32 + ".png"
    storage.save(key, b"data", "image/png")
    assert storage.exists(key) and storage.load(key) == b"data"
    head = s3.head_object(Bucket="receipts-test", Key=key)
    assert head["ServerSideEncryption"] == "AES256"

    import base64
    import json

    post = storage.presigned_upload(key, "image/png", 1024)
    assert post["fields"]["key"] == key
    policy = json.loads(base64.b64decode(post["fields"]["policy"]))
    assert ["content-length-range", 1, 1024] in policy["conditions"]
    assert {"Content-Type": "image/png"} in policy["conditions"]
    url = storage.presigned_get(key)
    assert "X-Amz-Expires=120" in url and "X-Amz-Signature" in url
    storage.delete(key)
    assert not storage.exists(key)


def test_s3_presigned_urls_use_regional_endpoint(aws_env):
    # New buckets outside us-east-1 answer the global endpoint with 307 redirects, which break
    # browser presigned POST uploads; the default client must sign against the regional host.
    storage = S3ReceiptStorage("receipts-test", REGION)
    key = "user-1/" + "c" * 32 + ".png"
    assert storage.presigned_upload(key, "image/png", 1024)["url"] == f"https://receipts-test.s3.{REGION}.amazonaws.com/"
    assert storage.presigned_get(key).startswith(f"https://receipts-test.s3.{REGION}.amazonaws.com/{key}?")
