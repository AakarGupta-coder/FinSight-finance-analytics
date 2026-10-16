"""Render read-only AWS API responses for the deployed stack into simple HTML resource views.

These are NOT AWS Management Console screenshots: each page carries a banner saying it was rendered from
live AWS API responses (time-stamped), so the report can show real resource state without Console access.
Account IDs are masked. Raw (masked) JSON is saved next to each page.
Usage: backend\\.venv\\Scripts\\python.exe docs/evidence/capture/aws_views.py   (then aws_views_shoot.mjs)
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import boto3

OUT = Path(__file__).resolve().parent.parent / "06_aws_console"
STACK, REGION = "finance-intelligence-prod", "ap-south-1"
ACCT = re.compile(r"$^")  # replaced at runtime with the caller's account id (see main)


def mask(obj):
    return json.loads(ACCT.sub(r"\1****\2", json.dumps(obj, default=str)))


def session() -> boto3.Session:
    aws = shutil.which("aws") or r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
    c = json.loads(subprocess.run([aws, "configure", "export-credentials", "--format", "process", "--profile", "finsight"],
                                  capture_output=True, text=True, check=True).stdout)
    return boto3.Session(aws_access_key_id=c["AccessKeyId"], aws_secret_access_key=c["SecretAccessKey"],
                         aws_session_token=c.get("SessionToken"), region_name=REGION)


def table(headers: list[str], rows: list[list]) -> str:
    th = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def page(name: str, title: str, source: str, sections: list[tuple[str, str]], raw) -> None:
    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    body = "".join(f"<h2>{html.escape(h)}</h2>{c}" for h, c in sections)
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title><style>
body{{font:14px/1.45 "Segoe UI",Arial,sans-serif;margin:0;background:#f2f3f3;color:#16191f}}
.banner{{background:#0f1b2a;color:#fff;padding:10px 24px;font-size:12.5px}} .banner b{{color:#ff9900}}
main{{padding:18px 24px}} h1{{font-size:22px;margin:4px 0 2px}} .sub{{color:#5f6b7a;font-size:12.5px;margin-bottom:14px}}
h2{{font-size:15px;margin:18px 0 8px}} table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #d5dbdb;font-size:12.5px}}
th{{background:#fafafa;text-align:left;padding:7px 10px;border-bottom:1px solid #d5dbdb;color:#414d5c}}
td{{padding:6px 10px;border-bottom:1px solid #eaeded;vertical-align:top;word-break:break-word}}
.ok{{color:#037f0c;font-weight:600}}</style></head><body>
<div class="banner"><b>Rendered from live AWS API responses</b> · {now} · account (masked) · {REGION} · source: {html.escape(source)} — not an AWS Management Console screenshot</div>
<main><h1>{html.escape(title)}</h1><div class="sub">Stack {STACK}</div>{body}</main></body></html>"""
    (OUT / f"{name}.html").write_text(ACCT.sub(r"\1****\2", doc), encoding="utf-8")
    (OUT / f"{name}.json").write_text(json.dumps(mask(raw), indent=1), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = session()
    global ACCT
    acct = s.client("sts").get_caller_identity()["Account"]
    ACCT = re.compile(rf"({acct[:4]}){acct[4:8]}({acct[8:]})")
    cfn, lam, apigw, idp, ddb, s3, ecr, cw, logs = (s.client(x) for x in
        ("cloudformation", "lambda", "apigatewayv2", "cognito-idp", "dynamodb", "s3", "ecr", "cloudwatch", "logs"))
    stack = cfn.describe_stacks(StackName=STACK)["Stacks"][0]
    res = cfn.list_stack_resources(StackName=STACK)["StackResourceSummaries"]
    phys = {r["LogicalResourceId"]: r["PhysicalResourceId"] for r in res}
    outs = {o["OutputKey"]: o["OutputValue"] for o in stack["Outputs"]}

    page("aws_cloudformation_stack", "CloudFormation stack", "cloudformation:DescribeStacks, ListStackResources", [
        ("Status", table(["Stack", "Status", "Created", "Last updated"], [[STACK, stack["StackStatus"], stack["CreationTime"], stack.get("LastUpdatedTime", "")]])),
        ("Outputs", table(["Key", "Value"], [[k, v] for k, v in outs.items()])),
        (f"Resources ({len(res)})", table(["Logical ID", "Type", "Status"], [[r["LogicalResourceId"], r["ResourceType"], r["ResourceStatus"]] for r in sorted(res, key=lambda r: r["ResourceType"])])),
    ], {"stack": stack, "resources": res})

    fns = [lam.get_function_configuration(FunctionName=phys[k]) for k in phys if k.endswith("Function")]
    page("aws_lambda_functions", "Lambda functions", "lambda:GetFunctionConfiguration", [
        (f"Functions ({len(fns)})", table(["Name", "Package", "Runtime / image", "Arch", "Memory MB", "Timeout s", "State", "Last modified"],
            [[f["FunctionName"], f.get("PackageType"), f.get("Runtime", "container image"), ",".join(f.get("Architectures", [])), f["MemorySize"], f["Timeout"], f.get("State"), f["LastModified"]] for f in fns])),
        ("Environment (shared settings, non-secret)", table(["Variable", "Value"], sorted(
            [[k, v] for k, v in fns[0].get("Environment", {}).get("Variables", {}).items()]))),
    ], fns)

    api_id = phys["HttpApi"]
    api = apigw.get_api(ApiId=api_id)
    routes = apigw.get_routes(ApiId=api_id)["Items"]
    auths = apigw.get_authorizers(ApiId=api_id)["Items"]
    page("aws_api_gateway", "API Gateway HTTP API", "apigatewayv2:GetApi, GetRoutes, GetAuthorizers", [
        ("API", table(["Name", "ApiId", "Protocol", "Endpoint", "CORS allow-origins"], [[api["Name"], api_id, api["ProtocolType"], api["ApiEndpoint"], ", ".join(api.get("CorsConfiguration", {}).get("AllowOrigins", []))]])),
        ("JWT authorizer", table(["Name", "Type", "Issuer", "Audience", "Identity source"], [[a["Name"], a["AuthorizerType"], a["JwtConfiguration"]["Issuer"], ", ".join(a["JwtConfiguration"]["Audience"]), ", ".join(a["IdentitySource"])] for a in auths])),
        (f"Routes ({len(routes)})", table(["Route", "Authorization"], sorted([[r["RouteKey"], r.get("AuthorizationType", "NONE")] for r in routes]))),
    ], {"api": api, "routes": routes, "authorizers": auths})

    pool = idp.describe_user_pool(UserPoolId=phys["UserPool"])["UserPool"]
    client = idp.describe_user_pool_client(UserPoolId=phys["UserPool"], ClientId=phys["UserPoolClient"])["UserPoolClient"]
    page("aws_cognito_user_pool", "Amazon Cognito user pool", "cognito-idp:DescribeUserPool, DescribeUserPoolClient", [
        ("User pool", table(["Name", "Id", "Tier", "Sign-in", "Auto-verified", "Est. users", "Password policy"], [[pool["Name"], pool["Id"], pool.get("UserPoolTier"), ", ".join(pool.get("UsernameAttributes", [])), ", ".join(pool.get("AutoVerifiedAttributes", [])), pool.get("EstimatedNumberOfUsers"), json.dumps(pool["Policies"]["PasswordPolicy"])]])),
        ("App client", table(["Name", "Client id", "Secret", "Auth flows", "Access/ID token", "Refresh token", "Revocation"], [[client["ClientName"], client["ClientId"], "none" if "ClientSecret" not in client else "yes", ", ".join(client["ExplicitAuthFlows"]), f"{client['AccessTokenValidity']}/{client['IdTokenValidity']} min", f"{client['RefreshTokenValidity']} days", client.get("EnableTokenRevocation")]])),
    ], {"pool": pool, "client": {k: v for k, v in client.items() if k != "ClientSecret"}})

    t = ddb.describe_table(TableName=phys["FinanceTable"])["Table"]
    page("aws_dynamodb_table", "DynamoDB table", "dynamodb:DescribeTable", [
        ("Table", table(["Name", "Status", "Billing", "Keys", "SSE", "Item count (≈6 h refresh)", "Size bytes"], [[t["TableName"], t["TableStatus"], t.get("BillingModeSummary", {}).get("BillingMode"), " / ".join(f"{k['AttributeName']} ({k['KeyType']})" for k in t["KeySchema"]), t.get("SSEDescription", {}).get("Status"), t["ItemCount"], t["TableSizeBytes"]]])),
        ("Global secondary indexes", table(["Index", "Keys", "Projection", "Status"], [[g["IndexName"], " / ".join(f"{k['AttributeName']} ({k['KeyType']})" for k in g["KeySchema"]), g["Projection"]["ProjectionType"], g["IndexStatus"]] for g in t.get("GlobalSecondaryIndexes", [])])),
    ], t)

    bucket = phys["ReceiptBucket"]
    pab = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    enc = s3.get_bucket_encryption(Bucket=bucket)["ServerSideEncryptionConfiguration"]
    cors = s3.get_bucket_cors(Bucket=bucket)["CORSRules"]
    pol = json.loads(s3.get_bucket_policy(Bucket=bucket)["Policy"])
    objs = s3.list_objects_v2(Bucket=bucket).get("KeyCount", 0)
    page("aws_s3_receipts_bucket", "S3 private receipts bucket", "s3:GetPublicAccessBlock, GetBucketEncryption, GetBucketCors, GetBucketPolicy, ListObjectsV2 (count only)", [
        ("Bucket", table(["Name", "Objects (synthetic test receipts)", "Encryption"], [[bucket, objs, enc["Rules"][0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"]]])),
        ("Block Public Access", table(list(pab.keys()), [list(pab.values())])),
        ("CORS", table(["Methods", "Origins", "Max age"], [[", ".join(r["AllowedMethods"]), ", ".join(r["AllowedOrigins"]), r.get("MaxAgeSeconds")] for r in cors])),
        ("Bucket policy statements", table(["Sid", "Effect", "Action", "Condition"], [[x.get("Sid"), x["Effect"], x["Action"], json.dumps(x.get("Condition"))] for x in pol["Statement"]])),
    ], {"public_access_block": pab, "encryption": enc, "cors": cors, "policy": pol, "object_count": objs})

    repos = [r for r in ecr.describe_repositories()["repositories"]]
    imgs = []
    for r in repos:
        for d in ecr.describe_images(repositoryName=r["repositoryName"])["imageDetails"]:
            imgs.append([r["repositoryName"], ",".join(d.get("imageTags", [])) or "(untagged)", round(d["imageSizeInBytes"] / 1e6, 1), d["imagePushedAt"], d.get("imageManifestMediaType", "")])
    page("aws_ecr_repository", "ECR repository (OCR container image)", "ecr:DescribeRepositories, DescribeImages", [
        ("Images", table(["Repository", "Tags", "Compressed MB", "Pushed", "Manifest type"], imgs)),
    ], {"repositories": repos, "images": imgs})

    alarms = cw.describe_alarms()["MetricAlarms"]
    groups = logs.describe_log_groups(logGroupNamePrefix=f"/aws/lambda/{STACK}")["logGroups"]
    page("aws_cloudwatch_monitoring", "CloudWatch alarms and log groups", "cloudwatch:DescribeAlarms, logs:DescribeLogGroups", [
        ("Alarms", table(["Name", "State", "Metric", "Threshold", "Period s"], [[a["AlarmName"], a["StateValue"], f"{a['Namespace']} {a['MetricName']}", f"{a['ComparisonOperator']} {a['Threshold']}", a["Period"]] for a in alarms])),
        (f"Log groups ({len(groups)})", table(["Log group", "Retention days", "Stored bytes"], [[g["logGroupName"], g.get("retentionInDays"), g.get("storedBytes")] for g in groups])),
    ], {"alarms": alarms, "log_groups": groups})
    print("rendered", len(list(OUT.glob("*.html"))), "views ->", OUT)


if __name__ == "__main__":
    main()
