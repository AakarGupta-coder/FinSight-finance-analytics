"""Live end-to-end tests against the deployed FinSight stack (real Cognito, API Gateway, Lambda,
DynamoDB, S3, CloudFront). Uses synthetic data and test users only.

Usage:  backend\\.venv\\Scripts\\python.exe infra\\live_test.py [--profile finsight] [--keep-users]

* Reads every URL / id from the CloudFormation stack outputs.
* Test users are created through the public Cognito SignUp API (the same call the web app makes) and
  confirmed with AdminConfirmSignUp (no inbox access needed). Their random passwords are written only to
  the git-ignored file backend/data/AWS_LIVE_TEST_ACCOUNTS.txt and are never printed.
* Results: docs/evidence/09_testing/live_api_results.json (no tokens, signed URLs or passwords).
* User B (isolation test) is deleted at the end; user A is kept as the live demo account unless
  --delete-all is given.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import secrets
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path

import boto3
import httpx

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "docs" / "evidence" / "09_testing" / "live_api_results.json"
ACCOUNTS = ROOT / "backend" / "data" / "AWS_LIVE_TEST_ACCOUNTS.txt"
RECEIPT = ROOT / "docs" / "report_assets" / "generators" / "sample_receipt_generated.png"
REGION = "ap-south-1"

results: list[dict] = []


def record(tid: str, feature: str, method: str, expected: str, ok: bool, actual: str, status: str | None = None) -> bool:
    status = status or ("PASS" if ok else "FAIL")
    results.append({"id": tid, "feature": feature, "method": method, "expected": expected, "actual": actual, "status": status})
    print(f"{status}  {tid:<6} {feature}: {actual}")
    return ok


def session(profile: str | None) -> boto3.Session:
    """Short-lived credentials from the AWS CLI (works with `aws login` sessions)."""
    aws = shutil.which("aws") or r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
    cmd = [aws, "configure", "export-credentials", "--format", "process"] + (["--profile", profile] if profile else [])
    creds = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    return boto3.Session(aws_access_key_id=creds["AccessKeyId"], aws_secret_access_key=creds["SecretAccessKey"],
                         aws_session_token=creds.get("SessionToken"), region_name=REGION)


def password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Fs" + "".join(secrets.choice(alphabet) for _ in range(14)) + "9"


class Api:
    def __init__(self, base: str, token: str | None = None):
        self.base = base.rstrip("/") + "/api/v1"
        self.token = token
        self.c = httpx.Client(timeout=90)

    def __call__(self, method: str, path: str, **kw) -> httpx.Response:
        headers = kw.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        # The test machine's network occasionally resets connections; retry transport errors only.
        for attempt in range(4):
            try:
                return self.c.request(method, self.base + path, headers=headers, **kw)
            except httpx.TransportError:
                if attempt == 3:
                    raise
                time.sleep(2 * (attempt + 1))
                self.c = httpx.Client(timeout=90)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="finsight")
    parser.add_argument("--stack", default="finance-intelligence-prod")
    parser.add_argument("--delete-all", action="store_true", help="also delete user A and its data at the end")
    args = parser.parse_args()

    s = session(args.profile)
    outputs = {o["OutputKey"]: o["OutputValue"] for o in
               s.client("cloudformation").describe_stacks(StackName=args.stack)["Stacks"][0]["Outputs"]}
    api_url, web_url = outputs["ApiUrl"], outputs["WebUrl"]
    pool, client_id = outputs["UserPoolId"], outputs["UserPoolClientId"]
    idp = s.client("cognito-idp")
    anon = Api(api_url)

    # Remove synthetic users left by earlier runs (their data via the API, then the Cognito user).
    if ACCOUNTS.exists():
        pairs, email = [], None
        for line in ACCOUNTS.read_text(encoding="utf-8").splitlines():
            if line.startswith("user_") and "_email=" in line:
                email = line.split("=", 1)[1]
            elif line.startswith("user_") and "_password=" in line and email:
                pairs.append((email, line.split("=", 1)[1]))
                email = None
        for old_email, old_pw in pairs:
            try:
                tok = idp.initiate_auth(ClientId=client_id, AuthFlow="USER_PASSWORD_AUTH",
                                        AuthParameters={"USERNAME": old_email, "PASSWORD": old_pw})["AuthenticationResult"]["AccessToken"]
                Api(api_url, tok)("POST", "/account/delete-data", json={"confirm": "DELETE"})
                idp.admin_delete_user(UserPoolId=pool, Username=old_email)
            except Exception:  # noqa: BLE001 - already deleted
                pass
        ACCOUNTS.unlink()
    today = dt.date.today().isoformat()
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")

    # ---------------------------------------------------------------- frontend / CloudFront
    web = httpx.Client(timeout=30, follow_redirects=False)
    r = web.get(web_url + "/")
    record("FE-01", "Web app (SPA) served over HTTPS", "GET WebUrl /", "200 text/html, FinSight title",
           r.status_code == 200 and "FinSight" in r.text, f"{r.status_code} {r.headers.get('content-type')}")
    r2 = web.get(web_url + "/app/budgets")
    record("FE-02", "Deep link fallback", "GET /app/budgets", "200 index.html (SPA routing)",
           r2.status_code == 200 and '<div id="root">' in r2.text, f"{r2.status_code}")
    hdrs = {k: r.headers.get(k) for k in ("strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy")}
    record("FE-03", "Security headers", "GET / response headers", "HSTS, nosniff, frame options, referrer policy",
           all(hdrs.values()), json.dumps(hdrs))
    same_origin = outputs.get("FrontendHosting") == "apigateway"
    try:
        r3 = web.get(web_url.replace("https://", "http://") + "/", timeout=8)
        plain = f"{r3.status_code} {r3.headers.get('location', '')[:30]}"
        ok = r3.status_code in (301, 302) and r3.headers.get("location", "").startswith("https://")
    except httpx.HTTPError as exc:
        plain, ok = f"no plain-HTTP listener ({type(exc).__name__})", same_origin
    record("FE-04", "No plain-HTTP access", "GET http://…/", "redirect to https (CloudFront) or no HTTP listener (API Gateway)", ok, plain)
    asset = next((p for p in r.text.split('"') if p.startswith("/assets/") and p.endswith(".js")), None)
    ra = web.get(web_url + asset) if asset else None
    record("FE-05", "Hashed JS asset cached long-term", f"GET {asset}", "200, immutable cache-control",
           bool(ra and ra.status_code == 200 and "immutable" in ra.headers.get("cache-control", "")),
           f"{ra.status_code if ra else 'no asset'} {ra.headers.get('cache-control') if ra else ''}")
    bundles = [web.get(web_url + p).text for p in [x for x in r.text.split('"') if x.startswith("/assets/") and x.endswith(".js")]]
    if same_origin:
        record("FE-06", "Bundle uses the same-origin API (no localhost/dev URLs)", "scan JS bundles", "no 'localhost' / '127.0.0.1'",
               bool(bundles) and not any("localhost:8000" in b or "127.0.0.1" in b for b in bundles), f"{len(bundles)} bundle(s) scanned")
    else:
        record("FE-06", "Bundle points at the deployed API", "bundle contains ApiUrl", "API Gateway URL compiled in",
               any(api_url in b for b in bundles), api_url.split("//")[1].split(".")[0] + ".execute-api…")

    # ---------------------------------------------------------------- public API
    r = anon("GET", "/health")
    record("API-01", "Health (public)", "GET /health", "200, database ok, dynamodb backend",
           r.status_code == 200 and r.json().get("database") == "ok" and r.json().get("data_backend") == "dynamodb", r.text[:120])
    r = anon("GET", "/config")
    cfg = r.json()
    record("API-02", "Public config", "GET /config", "auth_mode cognito, presigned uploads",
           cfg.get("auth_mode") == "cognito" and cfg.get("receipt_upload_mode") == "presigned"
           and cfg["cognito"]["client_id"] == client_id, f"auth_mode={cfg.get('auth_mode')} upload={cfg.get('receipt_upload_mode')}")
    r = httpx.get(api_url + "/api/docs")
    r2 = httpx.get(api_url + "/api/openapi.json")
    record("API-03", "No OpenAPI docs in production", "GET /api/docs, /api/openapi.json", "404 (not routed / disabled)",
           r.status_code == 404 and r2.status_code == 404, f"{r.status_code}/{r2.status_code}")

    # ---------------------------------------------------------------- unauthenticated / invalid tokens
    for i, (m, p) in enumerate([("GET", "/expenses"), ("POST", "/expenses"), ("GET", "/dashboard"), ("GET", "/budgets"),
                                 ("GET", "/goals"), ("GET", "/receipts"), ("POST", "/assistant/query"), ("GET", "/me")], 1):
        r = anon(m, p)
        record(f"SEC-{i:02d}", "Unauthenticated request rejected", f"{m} {p} (no token)", "401 from the JWT authorizer",
               r.status_code == 401, f"{r.status_code}")
    bad = Api(api_url, token="eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.invalid")
    r = bad("GET", "/expenses")
    record("SEC-09", "Malformed/forged token rejected", "GET /expenses (forged JWT)", "401", r.status_code == 401, f"{r.status_code}")

    # ---------------------------------------------------------------- Cognito sign-up / sign-in
    users = {}
    for label in ("a", "b"):
        email = f"finsight.live.{label}.{stamp}@example.com"
        pw = password()
        idp_public = s.client("cognito-idp")  # SignUp is an unauthenticated API; same request the browser sends
        idp_public.sign_up(ClientId=client_id, Username=email, Password=pw,
                           UserAttributes=[{"Name": "email", "Value": email}, {"Name": "name", "Value": f"Live Test {label.upper()}"}])
        idp.admin_confirm_sign_up(UserPoolId=pool, Username=email)
        auth = idp.initiate_auth(ClientId=client_id, AuthFlow="USER_PASSWORD_AUTH",
                                 AuthParameters={"USERNAME": email, "PASSWORD": pw})["AuthenticationResult"]
        users[label] = {"email": email, "password": pw, "access": auth["AccessToken"], "refresh": auth["RefreshToken"]}
    ACCOUNTS.parent.mkdir(parents=True, exist_ok=True)
    with ACCOUNTS.open("a", encoding="utf-8") as fh:
        fh.write(f"# created {dt.datetime.now().isoformat()} in pool {pool} (synthetic live-test users)\n")
        for label, u in users.items():
            fh.write(f"user_{label}_email={u['email']}\nuser_{label}_password={u['password']}\n")
    record("AUTH-01", "Registration (Cognito SignUp)", "SignUp + AdminConfirmSignUp", "user created and confirmed", True, "2 users")
    record("AUTH-02", "Login (USER_PASSWORD_AUTH)", "InitiateAuth", "access + refresh tokens issued",
           all(u["access"] for u in users.values()), "tokens issued (not logged)")
    try:
        idp.initiate_auth(ClientId=client_id, AuthFlow="USER_PASSWORD_AUTH",
                          AuthParameters={"USERNAME": users["a"]["email"], "PASSWORD": "wrong-password-1"})
        record("AUTH-03", "Wrong password rejected", "InitiateAuth (bad password)", "NotAuthorizedException", False, "accepted!")
    except idp.exceptions.NotAuthorizedException:
        record("AUTH-03", "Wrong password rejected", "InitiateAuth (bad password)", "NotAuthorizedException", True, "NotAuthorizedException")
    ref = idp.initiate_auth(ClientId=client_id, AuthFlow="REFRESH_TOKEN_AUTH", AuthParameters={"REFRESH_TOKEN": users["a"]["refresh"]})
    record("AUTH-04", "Token refresh", "InitiateAuth REFRESH_TOKEN_AUTH", "new access token",
           "AccessToken" in ref["AuthenticationResult"], "new access token issued")

    A, B = Api(api_url, users["a"]["access"]), Api(api_url, users["b"]["access"])
    r = A("GET", "/me")
    me = r.json()
    record("AUTH-05", "Authenticated request; identity from token", "GET /me", "200, Cognito auth mode, id = token sub",
           r.status_code == 200 and me.get("auth_mode") == "cognito" and len(me["user"]["id"]) == 36,
           f"{r.status_code} auth_mode={me.get('auth_mode')}")
    record("AUTH-06", "No UUID display name (fix D1)", "GET /me user.name", "empty (frontend uses ID-token name)",
           me["user"]["name"] in ("", None), repr(me["user"]["name"]))
    r = A("PUT", "/preferences", json={"display_name": "Live Test A", "currency": "INR", "timezone": "Asia/Kolkata"})
    record("PRF-01", "Profile/preferences update", "PUT /preferences", "200, persisted",
           r.status_code == 200 and A("GET", "/me").json()["preferences"]["display_name"] == "Live Test A", f"{r.status_code}")
    r = A("POST", "/expenses", json={"amount_minor": 100, "date": today, "category": "food", "description": "x", "user_id": "someone-else"})
    record("SEC-10", "Client-supplied user_id rejected", "POST /expenses with user_id", "422", r.status_code == 422, f"{r.status_code}")

    # ---------------------------------------------------------------- expenses
    seed = [(45050, "food", "Team lunch", "Cafe Coffee Day", "upi"), (120000, "groceries", "Weekly groceries", "BigBasket", "debit_card"),
            (35000, "transportation", "Metro card top-up", "Chennai Metro", "wallet"), (89900, "shopping", "Running shoes", "Decathlon", "credit_card"),
            (49900, "subscriptions", "Music subscription", "Spotify", "upi"), (25000, "entertainment", "Movie night", "PVR", "upi")]
    created = []
    for amt, cat, desc, merch, pm in seed:
        r = A("POST", "/expenses", json={"amount_minor": amt, "date": today, "category": cat, "description": desc, "merchant": merch, "payment_method": pm})
        if r.status_code == 201:
            created.append(r.json()["expense"])
    record("EXP-01", "Expense creation", f"POST /expenses ×{len(seed)}", "201 each, persisted in DynamoDB",
           len(created) == len(seed), f"{len(created)}/{len(seed)} created")
    eid = created[0]["id"]
    r = A("GET", f"/expenses/{eid}")
    record("EXP-02", "Expense retrieval", "GET /expenses/{id}", "200, same amount", r.status_code == 200 and r.json()["amount_minor"] == 45050, f"{r.status_code}")
    r = A("PUT", f"/expenses/{eid}", json={"amount_minor": 52000, "date": today, "category": "food", "description": "Team lunch (edited)",
                                          "merchant": "Cafe Coffee Day", "payment_method": "upi"})
    record("EXP-03", "Expense update", "PUT /expenses/{id}", "200, new amount persisted",
           r.status_code == 200 and A("GET", f"/expenses/{eid}").json()["amount_minor"] == 52000, f"{r.status_code}")
    r = A("GET", "/expenses", params={"search": "groceries"})
    record("EXP-04", "Search", "GET /expenses?search=groceries", "1 match", r.status_code == 200 and r.json()["total_count"] == 1, f"total_count={r.json().get('total_count')}")
    r = A("GET", "/expenses", params={"category": "food", "sort": "amount", "order": "desc"})
    record("EXP-05", "Filter + sort", "GET /expenses?category=food&sort=amount", "only food rows",
           r.status_code == 200 and all(e["category"] == "food" for e in r.json()["items"]) and r.json()["total_count"] >= 1, f"total_count={r.json().get('total_count')}")
    tmp = A("POST", "/expenses", json={"amount_minor": 1000, "date": today, "category": "other", "description": "Delete me", "payment_method": "cash"}).json()["expense"]
    r = A("DELETE", f"/expenses/{tmp['id']}")
    record("EXP-06", "Expense deletion", "DELETE /expenses/{id}", "204 then 404", r.status_code == 204 and A("GET", f"/expenses/{tmp['id']}").status_code == 404, f"{r.status_code}")
    r = A("POST", "/expenses", json={"amount_minor": -5, "date": "2099-01-01", "category": "nope", "description": ""})
    body = r.json()
    record("EXP-07", "Input validation", "POST /expenses (invalid body)", "422 with error envelope + field details",
           r.status_code == 422 and body.get("error", {}).get("code") == "validation_error" and body["error"].get("details"),
           f"{r.status_code} {body.get('error', {}).get('code')} fields={len(body.get('error', {}).get('details') or [])}")
    r = A("GET", "/expenses/00000000000000000000000000000000")
    record("EXP-08", "Unknown id", "GET /expenses/{unknown}", "404 not_found", r.status_code == 404, f"{r.status_code}")

    # ---------------------------------------------------------------- budgets
    r1 = A("POST", "/budgets", json={"category": None, "amount_minor": 1500000})
    r2 = A("POST", "/budgets", json={"category": "shopping", "amount_minor": 100000})
    record("BUD-01", "Budget creation (overall + category)", "POST /budgets ×2", "201 each", r1.status_code == 201 and r2.status_code == 201, f"{r1.status_code}/{r2.status_code}")
    r = A("GET", "/budgets")
    b = r.json()
    shop = next((c for c in b["categories"] if c["category"] == "shopping"), {})
    record("BUD-02", "Budget utilization & threshold status", "GET /budgets", "shopping 89.9% → warning",
           r.status_code == 200 and shop.get("utilization_pct") == 89.9 and shop.get("status") == "warning",
           f"util={shop.get('utilization_pct')} status={shop.get('status')}")
    r = A("PUT", f"/budgets/{shop['budget_id']}", json={"amount_minor": 80000})
    shop2 = next(c for c in A("GET", "/budgets").json()["categories"] if c["category"] == "shopping")
    record("BUD-03", "Budget update", "PUT /budgets/{id}", "200, exceeded at ₹800", r.status_code == 200 and shop2["status"] == "exceeded", f"{r.status_code} status={shop2['status']}")
    r = A("POST", "/budgets", json={"category": "shopping", "amount_minor": 5000})
    record("BUD-04", "Duplicate budget rejected", "POST /budgets (existing category)", "409", r.status_code == 409, f"{r.status_code}")

    # ---------------------------------------------------------------- analytics / intelligence
    r = A("GET", "/dashboard")
    d = r.json()
    record("ANA-01", "Dashboard", "GET /dashboard", "200, totals match seeded data",
           r.status_code == 200 and d["summary"]["total_minor"] == 52000 + 120000 + 35000 + 89900 + 49900 + 25000, f"total_minor={d['summary']['total_minor']}")
    r = A("GET", "/analytics", params={"start": today[:8] + "01", "end": today})
    record("ANA-02", "Spending analytics", "GET /analytics", "200, 6 categories", r.status_code == 200 and len(r.json()["categories"]) == 6, f"{r.status_code} categories={len(r.json().get('categories', []))}")
    r = A("GET", "/insights")
    record("ANA-03", "Financial Intelligence Engine", "GET /insights", "200, ≥1 insight with evidence",
           r.status_code == 200 and len(r.json()["insights"]) >= 1 and "evidence" in r.json()["insights"][0], f"{r.status_code} insights={len(r.json().get('insights', []))}")
    r = A("GET", "/anomalies", params={"status": "all"})
    record("ANA-04", "Anomaly detection endpoint", "GET /anomalies?status=all", "200 with counts", r.status_code == 200 and "counts" in r.json(), f"{r.status_code} counts={r.json().get('counts')}")
    r = A("POST", "/anomalies/scan")
    record("ANA-05", "Anomaly re-scan", "POST /anomalies/scan", "200 {scanned}", r.status_code == 200 and "scanned" in r.json(), r.text[:80])
    r = A("POST", "/assistant/query", json={"question": "How much did I spend this month?"})
    record("AST-01", "Finance Assistant", "POST /assistant/query", "200, total_spent intent with ₹ answer",
           r.status_code == 200 and r.json()["intent"] == "total_spent" and "₹" in r.json()["answer"], r.json().get("answer", "")[:90])

    # ---------------------------------------------------------------- goals + simulator
    r = A("POST", "/goals", json={"name": "Emergency fund", "target_minor": 5000000, "saved_minor": 500000,
                                  "target_date": (dt.date.today() + dt.timedelta(days=365)).isoformat()})
    gid = r.json()["id"] if r.status_code == 201 else None
    record("GOL-01", "Savings goal creation", "POST /goals", "201", r.status_code == 201, f"{r.status_code}")
    r = A("POST", f"/goals/{gid}/contributions", json={"amount_minor": 250000})
    g = next(x for x in A("GET", "/goals").json()["items"] if x["id"] == gid)
    record("GOL-02", "Contribution tracking", "POST /goals/{id}/contributions", "saved 7,50,000 paise; progress 15%",
           r.status_code == 201 and g["saved_minor"] == 750000 and g["progress_pct"] == 15.0, f"{r.status_code} saved={g['saved_minor']} pct={g['progress_pct']}")
    r = A("POST", "/simulations", json={"baseline": "current_month_projection", "goal_id": gid,
                                         "scenarios": [{"name": "Cut shopping 50%", "adjustments": [{"category": "shopping", "mode": "percent", "value": 50}]}]})
    record("SIM-01", "What-If simulator", "POST /simulations", "200, positive monthly savings",
           r.status_code == 200 and r.json()["scenarios"][0]["monthly_savings_minor"] > 0, f"{r.status_code} savings={r.json()['scenarios'][0].get('monthly_savings_minor') if r.status_code == 200 else r.text[:80]}")

    # ---------------------------------------------------------------- receipts (private S3 + container OCR)
    data = RECEIPT.read_bytes()
    r = A("GET", "/receipts/status")
    record("RCT-01", "OCR available in deployed container", "GET /receipts/status", "ocr_available true, presigned mode",
           r.status_code == 200 and r.json()["ocr_available"] and r.json()["upload_mode"] == "presigned", r.text[:120])
    r = A("POST", "/receipts/upload-url", json={"content_type": "image/png", "size_bytes": len(data)})
    up = r.json()
    rid = up.get("receipt_id")
    record("RCT-02", "Presigned upload issued", "POST /receipts/upload-url", "201 with POST fields (URL not logged)",
           r.status_code == 201 and "fields" in up.get("upload", {}), f"{r.status_code}")
    origin = web_url
    pre = httpx.options(up["upload"]["url"], headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    record("RCT-03", "S3 CORS allows the web origin", "OPTIONS presigned URL (Origin=WebUrl)", "200 + allow-origin",
           pre.status_code == 200 and pre.headers.get("access-control-allow-origin") == origin, f"{pre.status_code}")
    s3r = httpx.post(up["upload"]["url"], data=up["upload"]["fields"], files={"file": ("receipt.png", data, "image/png")}, timeout=60)
    record("RCT-04", "Direct browser-style upload to private bucket", "POST presigned form", "204", s3r.status_code == 204, f"{s3r.status_code}")
    try:
        big = httpx.post(up["upload"]["url"], data=up["upload"]["fields"], files={"file": ("x.png", b"0" * (6 * 1024 * 1024), "image/png")}, timeout=120)
        big_ok, big_detail = big.status_code == 400 and "EntityTooLarge" in big.text, f"{big.status_code} {'EntityTooLarge' if 'EntityTooLarge' in big.text else ''}"
    except httpx.HTTPError as exc:  # S3 may reset the connection once the policy limit is exceeded
        big_ok, big_detail = True, f"connection closed by S3 before the body finished ({type(exc).__name__})"
    record("RCT-05", "Upload size limit enforced by S3 policy", "POST 6 MB via presigned form", "rejected (400 EntityTooLarge or reset)", big_ok, big_detail)
    t0 = time.time()
    r = A("POST", f"/receipts/{rid}/process")
    elapsed = time.time() - t0
    ex = r.json().get("extracted", {}) if r.status_code == 200 else {}
    record("RCT-06", "OCR processing (Tesseract in Lambda container)", "POST /receipts/{id}/process", "200, total 610.05 extracted",
           r.status_code == 200 and ex.get("total_minor") == 61005, f"{r.status_code} total_minor={ex.get('total_minor')} merchant={ex.get('merchant', {}).get('value')} ocr={ex.get('ocr_confidence')}% in {elapsed:.1f}s")
    r = A("GET", f"/receipts/{rid}/image")
    url = r.json().get("url", "")
    img = httpx.get(url) if url else None
    record("RCT-07", "Receipt retrieval via short-lived presigned GET", "GET /receipts/{id}/image then fetch", "200 image/png",
           bool(img and img.status_code == 200 and img.headers.get("content-type") == "image/png"), f"{img.status_code if img else 'no url'}")
    bucket = outputs["ReceiptBucketName"]
    raw = httpx.get(f"https://{bucket}.s3.{REGION}.amazonaws.com/{url.split('amazonaws.com/')[1].split('?')[0]}" if url else "https://example.invalid")
    record("RCT-08", "Receipt bucket is private", "unsigned GET of the object", "403", raw.status_code == 403, f"{raw.status_code}")
    r = A("POST", f"/receipts/{rid}/confirm", json={"amount_minor": 61005, "date": today, "category": "groceries",
                                                    "description": "Purchase at FRESH MART SUPERMARKET", "merchant": "FRESH MART SUPERMARKET", "payment_method": "upi"})
    record("RCT-09", "Review & confirm creates linked expense", "POST /receipts/{id}/confirm", "201, expense.receipt_id set",
           r.status_code == 201 and r.json()["expense"]["receipt_id"] == rid, f"{r.status_code}")
    r = A("POST", "/receipts/upload-url", json={"content_type": "application/pdf", "size_bytes": 1000})
    record("RCT-10", "Unsupported file type rejected", "POST /receipts/upload-url (pdf)", "422", r.status_code == 422, f"{r.status_code}")

    # ---------------------------------------------------------------- cross-user isolation
    checks = [B("GET", f"/expenses/{eid}").status_code, B("PUT", f"/expenses/{eid}", json={"amount_minor": 1, "date": today, "category": "food", "description": "hijack", "payment_method": "upi"}).status_code,
              B("DELETE", f"/expenses/{eid}").status_code, B("GET", f"/receipts/{rid}").status_code, B("GET", f"/receipts/{rid}/image").status_code,
              B("POST", f"/goals/{gid}/contributions", json={"amount_minor": 1}).status_code]
    record("ISO-01", "User B cannot read/modify user A's expense, receipt or goal", "6 cross-user requests", "404 for every request",
           all(c == 404 for c in checks), f"{checks}")
    lb = B("GET", "/expenses").json()
    record("ISO-02", "User B's lists are empty", "GET /expenses as B", "total_count 0", lb["total_count"] == 0, f"total_count={lb['total_count']}")
    record("ISO-03", "A's data intact after B's attempts", "GET /expenses/{id} as A", "amount unchanged",
           A("GET", f"/expenses/{eid}").json()["amount_minor"] == 52000, "unchanged")

    # ---------------------------------------------------------------- CORS + logout
    if same_origin:
        record("COR-01", "Site and API share one origin (no CORS needed)", "compare WebUrl and ApiUrl", "identical origins",
               web_url.rstrip("/") == api_url.rstrip("/"), web_url.split("//")[1].split(".")[0] + ".execute-api…")
    else:
        ok = httpx.options(api_url + "/api/v1/expenses", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                                   "Access-Control-Request-Headers": "authorization,content-type"})
        record("COR-01", "API CORS preflight from CloudFront origin", "OPTIONS /expenses", "204 + allow-origin = WebUrl",
               ok.status_code in (200, 204) and ok.headers.get("access-control-allow-origin") == origin, f"{ok.status_code} {ok.headers.get('access-control-allow-origin')}")
    evil = httpx.options(api_url + "/api/v1/expenses", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    record("COR-02", "Foreign origin not allowed", "OPTIONS with Origin evil.example", "no allow-origin header",
           evil.headers.get("access-control-allow-origin") is None, f"{evil.status_code} {evil.headers.get('access-control-allow-origin')}")
    r0 = B("GET", "/me")
    idp.global_sign_out(AccessToken=users["b"]["access"])
    time.sleep(17)  # > TOKEN_CHECK_CACHE_SECONDS (15 s): the backend re-asks Cognito whether the token is still valid
    r = B("GET", "/me")
    code = (r.json().get("error") or {}).get("code") if r.status_code == 401 else None
    record("AUTH-07", "Sign-out (GlobalSignOut) revokes the access token", "GET /me before and ~17 s after GlobalSignOut",
           "200 before; 401 token_revoked after", r0.status_code == 200 and r.status_code == 401 and code == "token_revoked",
           f"before={r0.status_code} after={r.status_code} code={code}")

    # ---------------------------------------------------------------- cleanup of user B
    B2 = Api(api_url, idp.initiate_auth(ClientId=client_id, AuthFlow="USER_PASSWORD_AUTH",
                                        AuthParameters={"USERNAME": users["b"]["email"], "PASSWORD": users["b"]["password"]})["AuthenticationResult"]["AccessToken"])
    r = B2("POST", "/account/delete-data", json={"confirm": "DELETE"})
    idp.admin_delete_user(UserPoolId=pool, Username=users["b"]["email"])
    record("CLN-01", "Isolation user B cleaned up", "POST /account/delete-data + AdminDeleteUser", "200, user removed", r.status_code == 200, f"{r.status_code}")
    if args.delete_all:
        A("POST", "/account/delete-data", json={"confirm": "DELETE"})
        idp.admin_delete_user(UserPoolId=pool, Username=users["a"]["email"])

    passed = sum(r["status"] == "PASS" for r in results)
    limitations = sum(r["status"] == "LIMITATION" for r in results)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps({"ran_at": dt.datetime.now().isoformat(), "stack": args.stack, "region": REGION,
                                   "passed": passed, "limitations": limitations, "total": len(results), "results": results}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n{passed}/{len(results)} passed -> {RESULTS}")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
