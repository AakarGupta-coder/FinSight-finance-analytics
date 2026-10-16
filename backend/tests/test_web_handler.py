"""Static frontend Lambda (infra/web/handler.py) used for FrontendHosting=apigateway."""

import base64
import importlib.util
import json
from pathlib import Path

import pytest

HANDLER = Path(__file__).resolve().parents[2] / "infra" / "web" / "handler.py"


@pytest.fixture
def web(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("web_handler", HANDLER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<!doctype html><div id=\"root\"></div>", encoding="utf-8")
    (static / "assets" / "index-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (static / "favicon.ico").write_bytes(b"\x00\x01binary")
    (tmp_path / "secret.txt").write_text("outside static", encoding="utf-8")
    monkeypatch.setattr(mod, "STATIC", static.resolve())
    mod._cache.clear()
    return mod


def call(web, path, method="GET"):
    return web.handler({"rawPath": path, "requestContext": {"http": {"method": method}}}, None)


def test_index_and_spa_fallback(web):
    for path in ("/", "/app/budgets", "/login"):
        r = call(web, path)
        assert r["statusCode"] == 200 and 'id="root"' in r["body"]
        assert r["headers"]["cache-control"] == "no-cache"
        assert r["headers"]["content-type"].startswith("text/html")


def test_hashed_assets_cached_long_and_binary_base64(web):
    r = call(web, "/assets/index-abc123.js")
    assert r["statusCode"] == 200 and "immutable" in r["headers"]["cache-control"]
    assert r["headers"]["content-type"].startswith("application/javascript")
    ico = call(web, "/favicon.ico")
    assert ico["isBase64Encoded"] and base64.b64decode(ico["body"]) == b"\x00\x01binary"


def test_missing_asset_is_404_not_html(web):
    r = call(web, "/assets/missing.js")
    assert r["statusCode"] == 404 and "root" not in r["body"]


def test_path_traversal_blocked(web):
    r = call(web, "/../secret.txt")
    assert r["statusCode"] == 404 and "outside static" not in r["body"]
    r = call(web, "/assets/../../secret.txt")
    assert "outside static" not in r["body"]


def test_api_paths_never_fall_through_to_spa(web):
    r = call(web, "/api/v1/unknown")
    assert r["statusCode"] == 404 and json.loads(r["body"])["error"]["code"] == "not_found"


def test_security_headers_and_methods(web):
    r = call(web, "/")
    for h in ("strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy"):
        assert h in r["headers"]
    assert call(web, "/", "POST")["statusCode"] == 405
    assert call(web, "/", "HEAD")["body"] == ""
