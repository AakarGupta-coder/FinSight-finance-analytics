import datetime as dt

import jwt

from app.auth.tokens import LOCAL_ISSUER
from tests.conftest import add_expense, headers, register

PRIVATE_ENDPOINTS = [
    ("get", "/api/v1/expenses"), ("post", "/api/v1/expenses"), ("get", "/api/v1/budgets"),
    ("get", "/api/v1/dashboard"), ("get", "/api/v1/insights"), ("get", "/api/v1/anomalies"),
    ("get", "/api/v1/goals"), ("post", "/api/v1/assistant/query"), ("post", "/api/v1/simulations"),
    ("get", "/api/v1/receipts"), ("get", "/api/v1/me"), ("post", "/api/v1/demo-data"),
]


def test_unauthenticated_requests_rejected(client):
    for method, path in PRIVATE_ENDPOINTS:
        resp = getattr(client, method)(path)
        assert resp.status_code == 401, path
        assert resp.json()["error"]["code"] == "unauthorized"


def test_invalid_tokens_rejected(client, settings):
    bad_sig = jwt.encode({"sub": "x", "iss": LOCAL_ISSUER, "iat": dt.datetime.now(dt.UTC),
                          "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)}, "wrong-secret-wrong-secret-wrong-secret!",
                         algorithm="HS256")
    expired = jwt.encode({"sub": "x", "iss": LOCAL_ISSUER, "iat": dt.datetime.now(dt.UTC) - dt.timedelta(hours=3),
                          "exp": dt.datetime.now(dt.UTC) - dt.timedelta(hours=1)}, settings.jwt_secret, algorithm="HS256")
    none_alg = jwt.encode({"sub": "x", "iss": LOCAL_ISSUER}, None, algorithm="none")
    for token in ("garbage", bad_sig, expired, none_alg):
        resp = client.get("/api/v1/expenses", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    expired_resp = client.get("/api/v1/expenses", headers={"Authorization": f"Bearer {expired}"})
    assert expired_resp.json()["error"]["code"] == "token_expired"
    assert client.get("/api/v1/expenses", headers={"Authorization": "Basic abc"}).status_code == 401


def test_cannot_access_or_modify_another_users_records(client, today):
    alice = headers(register(client, "alice@example.com"))
    bob = headers(register(client, "bob@example.com", "Bob"))
    expense = add_expense(client, alice, 5000, today, "food", "Alice lunch")
    goal = client.post("/api/v1/goals", headers=alice, json={"name": "A", "target_minor": 100}).json()
    budget = client.post("/api/v1/budgets", headers=alice, json={"amount_minor": 100}).json()

    assert client.get(f"/api/v1/expenses/{expense['id']}", headers=bob).status_code == 404
    body = {"amount_minor": 1, "date": today.isoformat(), "category": "food", "description": "hacked"}
    assert client.put(f"/api/v1/expenses/{expense['id']}", headers=bob, json=body).status_code == 404
    assert client.delete(f"/api/v1/expenses/{expense['id']}", headers=bob).status_code == 404
    assert client.get(f"/api/v1/goals/{goal['id']}", headers=bob).status_code == 404
    assert client.put(f"/api/v1/budgets/{budget['id']}", headers=bob, json={"amount_minor": 1}).status_code == 404
    assert client.get("/api/v1/expenses", headers=bob).json()["total_count"] == 0
    # Alice's data is untouched.
    assert client.get(f"/api/v1/expenses/{expense['id']}", headers=alice).json()["description"] == "Alice lunch"


def test_client_supplied_user_id_is_rejected(client, auth, today):
    resp = client.post("/api/v1/expenses", headers=auth, json={
        "amount_minor": 100, "date": today.isoformat(), "category": "food", "description": "x", "user_id": "someone"})
    assert resp.status_code == 422


def test_cannot_attach_another_users_receipt(client, today):
    import io

    from PIL import Image

    alice = headers(register(client, "alice2@example.com"))
    bob = headers(register(client, "bob2@example.com", "Bob"))
    buf = io.BytesIO()
    Image.new("RGB", (200, 200), "white").save(buf, "PNG")
    rid = client.post("/api/v1/receipts", headers=alice, files={"file": ("r.png", buf.getvalue(), "image/png")}).json()["id"]
    assert client.get(f"/api/v1/receipts/{rid}/image", headers=bob).status_code == 404
    resp = client.post("/api/v1/expenses", headers=bob, json={
        "amount_minor": 100, "date": today.isoformat(), "category": "food", "description": "x", "receipt_id": rid})
    assert resp.status_code == 422


def test_login_failures_and_rate_limit(client):
    register(client, "carol@example.com", "Carol")
    wrong = {"email": "carol@example.com", "password": "nope-wrong-1"}
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json=wrong).status_code == 401
    assert client.post("/api/v1/auth/login", json=wrong).status_code == 429
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "x1234567"})
    assert unknown.status_code == 401 and "Incorrect email or password" in unknown.json()["error"]["message"]


def test_weak_password_and_duplicate_email(client):
    weak = client.post("/api/v1/auth/register", json={"name": "D", "email": "d@example.com", "password": "short"})
    assert weak.status_code == 422
    register(client, "dup@example.com")
    dup = client.post("/api/v1/auth/register", json={"name": "D", "email": "DUP@example.com", "password": "Passw0rd!"})
    assert dup.status_code == 409


def test_passwords_are_hashed(client, repo):
    register(client, "erin@example.com", "Erin")
    user = repo.get_user_by_email("erin@example.com")
    assert user.password_hash.startswith("scrypt$") and "Passw0rd!" not in user.password_hash


def test_security_headers_and_cors(client):
    resp = client.get("/api/v1/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    preflight = client.options("/api/v1/expenses", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert preflight.headers.get("access-control-allow-origin") != "https://evil.example"
    ok = client.options("/api/v1/expenses", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_errors_do_not_leak_internals(client, auth):
    resp = client.get("/api/v1/expenses/does-not-exist", headers=auth)
    assert resp.status_code == 404 and "Traceback" not in resp.text


def test_delete_all_data_requires_password(client, today):
    auth = headers(register(client, "frank@example.com", "Frank"))
    add_expense(client, auth, 100, today)
    bad = client.post("/api/v1/account/delete-data", headers=auth, json={"confirm": "DELETE", "password": "wrong"})
    assert bad.status_code == 422
    ok = client.post("/api/v1/account/delete-data", headers=auth, json={"confirm": "DELETE", "password": "Passw0rd!"})
    assert ok.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": "frank@example.com", "password": "Passw0rd!"})
    assert login.status_code == 401
