"""Static frontend server for API Gateway hosting (FrontendHosting=apigateway).

Used when CloudFront is not available on the account: the same HTTP API that serves /api/v1/*
also serves the built SPA (frontend/dist, staged into ./static by infra/prepare_build.py), so the
site and the API share one HTTPS origin and the browser needs no CORS for API calls.

* /assets/* (content-hashed) are cached for a year; everything else must revalidate.
* Unknown paths without a file extension return index.html (client-side routing / deep links).
* Missing files with an extension return 404 (never HTML in place of a script or image).
* /api/* never falls through to the SPA: unknown API paths get the API's JSON 404 envelope.
* Security headers mirror CloudFront's managed SecurityHeadersPolicy.
Standard library only; files are read once per warm container.
"""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

STATIC = (Path(__file__).resolve().parent / "static").resolve()
TEXT_TYPES = ("text/", "application/javascript", "application/json", "application/manifest+json", "image/svg+xml")
SECURITY_HEADERS = {
    "strict-transport-security": "max-age=31536000",
    "x-content-type-options": "nosniff",
    "x-frame-options": "SAMEORIGIN",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-xss-protection": "1; mode=block",
}
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("image/svg+xml", ".svg")

_cache: dict[Path, bytes] = {}


def _read(path: Path) -> bytes:
    if path not in _cache:
        _cache[path] = path.read_bytes()
    return _cache[path]


def _response(status: int, body: bytes, content_type: str, cache: str, head: bool = False) -> dict:
    is_text = content_type.startswith(TEXT_TYPES)
    headers = {"content-type": content_type + ("; charset=utf-8" if is_text and "charset" not in content_type else ""),
               "cache-control": cache, **SECURITY_HEADERS}
    if head:
        return {"statusCode": status, "headers": headers, "body": ""}
    if is_text:
        return {"statusCode": status, "headers": headers, "body": body.decode("utf-8"), "isBase64Encoded": False}
    return {"statusCode": status, "headers": headers, "body": base64.b64encode(body).decode("ascii"), "isBase64Encoded": True}


def resolve(raw_path: str) -> tuple[Path | None, bool]:
    """Map a request path to (file, is_spa_fallback). Returns (None, False) for a missing asset."""
    rel = raw_path.split("?", 1)[0].lstrip("/")
    if rel:
        candidate = (STATIC / rel).resolve()
        if STATIC in candidate.parents and candidate.is_file():
            return candidate, False
        if "." in rel.rsplit("/", 1)[-1]:
            return None, False
    return STATIC / "index.html", True


def handler(event, context):  # noqa: ARG001 - Lambda signature
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath") or "/"
    if path.startswith("/api/"):
        body = json.dumps({"error": {"code": "not_found", "message": "Resource not found."}}).encode()
        return _response(404, body, "application/json", "no-store")
    if method not in ("GET", "HEAD"):
        return _response(405, b"Method not allowed", "text/plain", "no-store")
    file, spa = resolve(path)
    if file is None:
        return _response(404, b"Not found", "text/plain", "no-cache", method == "HEAD")
    content_type = "text/html" if spa else (mimetypes.guess_type(file.name)[0] or "application/octet-stream")
    cache = "public,max-age=31536000,immutable" if file.parent.name == "assets" else "no-cache"
    return _response(200, _read(file), content_type, cache, method == "HEAD")
