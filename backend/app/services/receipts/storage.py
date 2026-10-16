"""Private receipt file storage: local directory or Amazon S3.

Object keys are always generated server-side as ``<user_id>/<receipt_id>.<ext>``
and validated before use, so user input can never influence file paths.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from app.errors import NotFound, ValidationFailed

KEY_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}/[a-f0-9]{32}\.(jpg|png|webp)$")


def build_key(user_id: str, receipt_id: str, ext: str) -> str:
    key = f"{user_id}/{receipt_id}.{ext}"
    if not KEY_PATTERN.fullmatch(key):
        raise ValidationFailed("Invalid receipt storage key.")
    return key


class ReceiptStorage(ABC):
    supports_presigned_upload = False

    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def load(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalReceiptStorage(ReceiptStorage):
    """Stores files under a private directory that is never served statically."""

    def __init__(self, base_dir: Path):
        self.base = Path(base_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not KEY_PATTERN.fullmatch(key):
            raise ValidationFailed("Invalid receipt storage key.")
        path = (self.base / key).resolve()
        if self.base not in path.parents:
            raise ValidationFailed("Invalid receipt storage key.")
        return path

    def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def load(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise NotFound("Receipt file not found.")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


class S3ReceiptStorage(ReceiptStorage):
    """Private S3 bucket. The browser only ever receives short-lived presigned URLs."""

    supports_presigned_upload = True

    def __init__(self, bucket: str, region: str, client=None):
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        # Regional virtual-hosted endpoint (https://<bucket>.s3.<region>.amazonaws.com). The global
        # endpoint answers a newly created bucket outside us-east-1 with 307 redirects, which breaks
        # browser uploads with presigned POSTs (and their CORS preflight).
        self.client = client or boto3.client(
            "s3", region_name=region, endpoint_url=f"https://s3.{region}.amazonaws.com",
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )

    def save(self, key: str, data: bytes, content_type: str) -> None:
        if not KEY_PATTERN.fullmatch(key):
            raise ValidationFailed("Invalid receipt storage key.")
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type,
                               ServerSideEncryption="AES256")

    def load(self, key: str) -> bytes:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.client.exceptions.NoSuchKey as exc:
            raise NotFound("Receipt file not found.") from exc

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def presigned_upload(self, key: str, content_type: str, max_bytes: int, expires: int = 300) -> dict:
        return self.client.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Fields={"Content-Type": content_type, "x-amz-server-side-encryption": "AES256"},
            Conditions=[
                {"Content-Type": content_type},
                {"x-amz-server-side-encryption": "AES256"},
                ["content-length-range", 1, max_bytes],
            ],
            ExpiresIn=expires,
        )

    def presigned_get(self, key: str, expires: int = 120) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires
        )


def build_storage(settings) -> ReceiptStorage:
    if settings.receipt_storage == "s3":
        return S3ReceiptStorage(settings.receipt_bucket, settings.aws_region)
    return LocalReceiptStorage(settings.receipt_dir)
