"""Select the repository implementation from configuration."""

from __future__ import annotations

from app.config import Settings
from app.repositories.base import Repository


def build_repository(settings: Settings) -> Repository:
    if settings.data_backend == "dynamodb":
        from app.repositories.dynamodb_repo import DynamoDBRepository

        return DynamoDBRepository(settings.dynamodb_table, settings.aws_region)
    from app.repositories.sqlite_repo import SQLiteRepository

    return SQLiteRepository(settings.sqlite_path)
