"""AWS Lambda entry points.

Each Lambda function serves one route group using the same FastAPI code that
runs locally (adapted by Mangum), so business logic is never duplicated.
API Gateway routes map /api/v1/<group>/* to the matching function, and each
function gets an IAM role with only the permissions its group needs.

Handler strings (see infra/template.yaml):
    app.handlers.expenses.handler
    app.handlers.budgets.handler
    ...
"""

from __future__ import annotations

from functools import lru_cache


def build_handler(*groups: str):
    from mangum import Mangum

    from app.main import create_app

    @lru_cache(maxsize=1)
    def _adapter():
        # Built once per warm container.
        return Mangum(create_app(groups=groups), lifespan="off", api_gateway_base_path="/")

    def handler(event, context):
        return _adapter()(event, context)

    return handler
