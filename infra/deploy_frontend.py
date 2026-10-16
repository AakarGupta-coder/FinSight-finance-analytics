"""Build the frontend against the deployed API and publish it to the stack's S3 + CloudFront.

Reads every deployment-specific value (API URL, bucket, distribution) from the
CloudFormation stack outputs, so nothing environment-specific is hard-coded.

Usage:  python infra/deploy_frontend.py [--profile finsight] [--stack finance-intelligence-prod] [--skip-build]
Requires: AWS CLI v2 (signed in), Node/npm.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"


def aws_exe() -> str:
    found = shutil.which("aws")
    if found:
        return found
    default = Path(r"C:\Program Files\Amazon\AWSCLIV2\aws.exe")
    if default.exists():
        return str(default)
    sys.exit("AWS CLI v2 not found on PATH")


def aws(args: list[str], profile: str | None, region: str) -> str:
    cmd = [aws_exe(), *args, "--region", region, "--output", "json"]
    if profile:
        cmd += ["--profile", profile]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"aws {' '.join(args[:2])} failed:\n{result.stderr.strip()}")
    return result.stdout


def stack_outputs(stack: str, profile: str | None, region: str) -> dict[str, str]:
    data = json.loads(aws(["cloudformation", "describe-stacks", "--stack-name", stack], profile, region))
    return {o["OutputKey"]: o["OutputValue"] for o in data["Stacks"][0].get("Outputs", [])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=os.environ.get("AWS_PROFILE"))
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--stack", default="finance-intelligence-prod")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    out = stack_outputs(args.stack, args.profile, args.region)
    api_url, bucket, dist_id = out["ApiUrl"], out["FrontendBucketName"], out["DistributionId"]
    print(f"API: {api_url}\nBucket: {bucket}\nDistribution: {dist_id}\nWeb: {out.get('WebUrl')}")

    if not args.skip_build:
        env = dict(os.environ, VITE_API_BASE_URL=api_url)
        npm = shutil.which("npm") or "npm"
        subprocess.run([npm, "run", "build"], cwd=FRONTEND, env=env, check=True, shell=os.name == "nt")
    if not (DIST / "index.html").exists():
        sys.exit("frontend/dist/index.html missing - build first")

    # Hashed assets never change: cache for a year. Everything else (index.html, icons, manifest)
    # must be revalidated so a redeploy is picked up immediately.
    aws(["s3", "sync", str(DIST / "assets"), f"s3://{bucket}/assets", "--delete",
         "--cache-control", "public,max-age=31536000,immutable"], args.profile, args.region)
    aws(["s3", "sync", str(DIST), f"s3://{bucket}", "--delete", "--exclude", "assets/*",
         "--cache-control", "no-cache"], args.profile, args.region)
    inv = json.loads(aws(["cloudfront", "create-invalidation", "--distribution-id", dist_id, "--paths", "/*"],
                         args.profile, args.region))
    print(f"Uploaded {sum(1 for p in DIST.rglob('*') if p.is_file())} files; invalidation {inv['Invalidation']['Id']} "
          f"{inv['Invalidation']['Status']}")


if __name__ == "__main__":
    main()
