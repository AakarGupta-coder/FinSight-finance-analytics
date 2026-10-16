"""Upload validation: size, declared type, magic bytes and decodability."""

from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError

from app.errors import ValidationFailed

ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_PIXELS = 40_000_000  # guard against decompression bombs
MIN_DIMENSION = 50

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def sniff_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(data: bytes, declared_type: str | None, max_bytes: int) -> tuple[str, str]:
    """Validate an uploaded receipt image. Returns (content_type, extension)."""
    if not data:
        raise ValidationFailed("The uploaded file is empty.")
    if len(data) > max_bytes:
        raise ValidationFailed(f"File is too large. Maximum size is {max_bytes // (1024 * 1024)} MB.", code="file_too_large")
    actual = sniff_type(data)
    if actual is None:
        raise ValidationFailed("Unsupported file. Upload a JPEG, PNG or WebP image.", code="unsupported_file_type")
    if declared_type and declared_type.split(";")[0].strip().lower() not in (actual, "application/octet-stream"):
        raise ValidationFailed("File content does not match its declared type.", code="type_mismatch")
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError) as exc:
        raise ValidationFailed("The image could not be read. It may be corrupted.", code="unreadable_image") from exc
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise ValidationFailed("Image is too small to contain a readable receipt.", code="unreadable_image")
    if width * height > MAX_PIXELS:
        raise ValidationFailed("Image dimensions are too large.", code="file_too_large")
    return actual, ALLOWED_TYPES[actual]
