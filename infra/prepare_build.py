"""Stage the Lambda source so only application code is packaged.

Copies backend/app and backend/requirements.txt into infra/build/backend/. `sam build`
then installs the dependencies for the Lambda platform: aws-lambda-builders downloads
manylinux x86_64 wheels for python3.13 even on a Windows host (it needs a local python3.13
only for its runtime check), so host-specific binaries never reach the package. Note: SAM's
Python builder deliberately skips *.so files when copying source, so dependencies must come
from requirements.txt, never be vendored into this folder. boto3 is provided by the runtime.

This keeps the local virtualenv, tests and the local database (which may
contain personal data) out of the deployment package.

It also stages infra/build/web/ (the static-file Lambda for FrontendHosting=apigateway): the
handler from infra/web/ plus the SPA built with an empty VITE_API_BASE_URL, so the browser calls
the API on the same origin.

Usage:  python infra/prepare_build.py [--skip-frontend-build]   (then: cd infra && sam build)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "backend"
DEST = ROOT / "infra" / "build" / "backend"
WEB_DEST = ROOT / "infra" / "build" / "web"
FRONTEND = ROOT / "frontend"


def stage_web(skip_frontend_build: bool) -> None:
    if WEB_DEST.exists():
        shutil.rmtree(WEB_DEST)
    WEB_DEST.mkdir(parents=True)
    shutil.copy2(ROOT / "infra" / "web" / "handler.py", WEB_DEST / "handler.py")
    if not skip_frontend_build:
        # Same-origin build: API calls go to /api/v1 on the site's own origin.
        env = dict(os.environ, VITE_API_BASE_URL="")
        npm = shutil.which("npm") or "npm"
        subprocess.run([npm, "run", "build"], cwd=FRONTEND, env=env, check=True, shell=os.name == "nt")
    if not (FRONTEND / "dist" / "index.html").exists():
        sys.exit("frontend/dist/index.html missing - run without --skip-frontend-build")
    shutil.copytree(FRONTEND / "dist", WEB_DEST / "static")
    print(f"Staged web bundle: {sum(1 for p in (WEB_DEST / 'static').rglob('*') if p.is_file())} files in {WEB_DEST}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-frontend-build", action="store_true", help="reuse the existing frontend/dist")
    args = parser.parse_args()
    stage_web(args.skip_frontend_build)

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    shutil.copytree(SRC / "app", DEST / "app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(SRC / "requirements.txt", DEST / "requirements.txt")
    files = sum(1 for p in DEST.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in DEST.rglob("*") if p.is_file()) / 1e6
    print(f"Staged {files} files ({size:.1f} MB) in {DEST}")


if __name__ == "__main__":
    main()
