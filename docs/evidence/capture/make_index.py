"""Regenerate docs/evidence/SCREENSHOT_INDEX.md from the files actually present in docs/evidence/.

Every entry is a real file on disk. Descriptions come from the table below; files without a description
are still listed (marked "(no description)") so nothing is hidden or invented.
Usage: python docs/evidence/capture/make_index.py
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

EV = Path(__file__).resolve().parent.parent

PHASES = {
    "01_workspace_audit": ("Phase 1–2 audit/cleanup", "Implementation readiness audit"),
    "02_local_application": ("Phase 3 local application", "Implementation / results (local)"),
    "03_frontend_design": ("Phase 5 design", "UI design"),
    "04_animations": ("Phase 5 animations", "UI animation implementation"),
    "05_aws_toolchain": ("Phase 6–7 toolchain + identity", "Deployment environment"),
    "06_aws_console": ("Phase 10 AWS resources", "AWS deployment"),
    "07_aws_deployment": ("Phase 9–10 deployment", "AWS deployment"),
    "08_live_application": ("Phase 10–11 live application", "Results (live on AWS)"),
    "09_testing": ("Phase 3/11 testing", "Testing"),
    "10_monitoring": ("Phase 11 monitoring", "Monitoring"),
}

# filename -> (what it demonstrates, kind, redactions)
DESC: dict[str, tuple[str, str, str]] = {}


def d(name: str, what: str, kind: str = "Application screenshot (headless Chrome, synthetic data)", red: str = "none") -> None:
    DESC[name] = (what, kind, red)


TERM = "Terminal capture (real command output saved as text)"
AWSV = "AWS resource view: rendered from live AWS API responses (read-only CLI calls), not a Console screenshot"
for n, w in {
    "local_landing": "Public landing page", "local_registration": "Registration form", "local_login": "Sign-in form",
    "local_dashboard": "Dashboard: KPIs, category donut, budgets, trend, recent activity, insights, needs attention (full page)",
    "local_budget_management": "Budgets: overall + category budgets, utilization, thresholds, history",
    "local_expense_management": "Transactions table with search, sort, pagination and summary strip",
    "local_expense_detail_dialog": "Expense detail dialog", "local_expense_filtering": "Filter panel (category filter applied)",
    "local_expense_creation": "Add-expense form filled in", "local_financial_analytics": "Analytics: daily/monthly charts, categories, merchants",
    "local_financial_intelligence": "Financial insights (Intelligence Engine) with evidence", "local_anomaly_detection": "Anomaly detection review list",
    "local_receipt_scanner": "Receipt scanner upload step", "local_receipt_ocr_review": "Receipt OCR result and review/correction form",
    "local_whatif_simulator": "What-If simulator scenarios and comparison", "local_finance_assistant": "Finance assistant answer",
    "local_savings_goals": "Savings goals with progress and contributions", "local_profile": "Profile", "local_settings": "Settings (full page)",
}.items():
    d(n + ".png", w)
for n, w in {
    "design_dashboard_dark": "Dashboard, dark theme (default)", "design_dashboard_light": "Dashboard, light theme",
    "design_transactions_light": "Transactions, light theme", "design_mobile_dashboard": "Dashboard at 390px (mobile)",
    "design_mobile_navigation": "Mobile navigation drawer open",
}.items():
    d(n + ".png", w)
for n, w in {
    "anim_form_validation_message": "Sign-in validation messages sliding in (empty submit)",
    "anim_dashboard_entrance_midframe": "Dashboard entrance mid-frame: KPI figures counting up, donut drawing in",
    "anim_page_transition_midframe": "Page transition mid-frame: blocks rising in with stagger after client-side navigation",
    "anim_budget_progress_settled": "Budget progress bars after their grow-in animation",
    "anim_sidebar_active_hover_focus": "Sidebar: emerald active indicator, hover state and keyboard focus ring",
    "anim_modal_opening_midframe": "Dialog entrance mid-frame (fade + rise + scale)",
    "anim_expense_form_validation": "Expense form validation messages",
    "anim_receipt_processing_state": "Receipt processing state: step list, scan line, indeterminate bar, live timer",
    "anim_assistant_typing": "Assistant message entrance and 'Calculating…' dots",
    "anim_savings_progress_settled": "Savings-goal progress bars after grow-in",
    "anim_theme_switch_midframe": "Theme switch mid cross-fade (dark → light)",
    "anim_mobile_drawer_opening_midframe": "Mobile drawer sliding in",
}.items():
    d(n + ".png", w, "Application screenshot, captured mid-animation (headless Chrome)")
for n, w in {
    "live_landing": "Live landing page served by API Gateway + WebFunction (CloudFront pending AWS verification)", "live_registration": "Live registration page (Cognito sign-up)",
    "live_login": "Live sign-in page", "live_dashboard": "Live dashboard after Amazon Cognito sign-in (data from DynamoDB)",
    "live_expense_management": "Live transactions list", "live_expense_creation_form": "Expense being created in the live app",
    "live_expense_workflow": "New expense listed after saving through API Gateway → Lambda → DynamoDB",
    "live_budget_management": "Live budgets with utilization/threshold status", "live_analytics": "Live analytics",
    "live_financial_insights": "Live financial insights", "live_anomaly_detection": "Live anomaly detection page",
    "live_receipt_processing": "Live receipt processing (browser → presigned POST → private S3 → OCR Lambda)",
    "live_receipt_review": "Live OCR result and review form from the container Lambda",
    "live_whatif_simulator": "Live What-If simulator", "live_finance_assistant": "Live finance assistant answer",
    "live_savings_goals": "Live savings goal with contribution", "live_profile": "Live profile (Amazon Cognito account)",
    "live_settings": "Live settings", "live_dashboard_light": "Live dashboard, light theme",
    "live_mobile_dashboard": "Live dashboard at 390px", "live_mobile_navigation": "Live mobile navigation drawer",
    "live_landing_footer_credit": "Landing footer with 'Created by Aakar Gupta' and the header 'i' (About) button",
    "live_about_author_dark": "About the author dialog (dark theme)", "live_about_author_light": "About the author dialog (light theme)",
    "live_about_author_mobile": "About the author dialog at 390px",
}.items():
    d(n + ".png", w, "Live application screenshot (deployed execute-api URL, synthetic test user)", "URL bar not shown; no tokens or signed URLs visible")


for n, w in {
    "aws_cloudformation_stack": "CloudFormation stack status, outputs and all resources", "aws_lambda_functions": "9 Lambda functions (8 zip python3.13 + 1 container) and shared env",
    "aws_api_gateway": "HTTP API, Cognito JWT authorizer and every route with its authorization type", "aws_cognito_user_pool": "Cognito user pool (Lite tier) and public app client",
    "aws_dynamodb_table": "DynamoDB single table + GSI1, on-demand, SSE", "aws_s3_receipts_bucket": "Private receipts bucket: Block Public Access, SSE, CORS, TLS-only policy",
    "aws_ecr_repository": "ECR images for the OCR container function", "aws_cloudwatch_monitoring": "CloudWatch 5xx alarm and log groups (14-day retention)",
}.items():
    d(n + ".png", w, AWSV, "account ID masked")
for n, w in {
    "initial_repository_inventory.txt": "Repository inventory before cleanup (git status incl. ignored paths)",
    "aws_toolchain_and_identity.txt": "AWS CLI / SAM / Docker versions, identity (masked) and Free-plan credit state",
    "sam_build_output.txt": "Final `sam build` output", "receipts_container_verification.txt": "OCR image: linux/amd64, Tesseract 5.5.0, handler import, OCR on the sample receipt",
    "zip_package_import_check.txt": "Zip package imports + Mangum round-trip in a Linux cp313 container",
    "sam_deploy_attempt1_changeset.txt": "Attempt 1 changeset (62 adds) - CloudFront later refused", "sam_deploy_attempt2_cloudfront_blocked.txt": "Attempt 2 - CloudFront account-verification error and rollback",
    "sam_deploy_changeset.txt": "Successful deployment changeset (63 adds, FrontendHosting=apigateway)", "sam_deploy_update1_changeset.txt": "Update 1 - packaging fix (code-only modifies)",
    "sam_deploy_update2_changeset.txt": "Update 2 - regional S3 endpoint fix (code-only modifies)", "stack_outputs_and_resources.txt": "Stack outputs and resource list after deployment",
    "baseline_backend_pytest.txt": "Baseline backend tests (114 passed)", "baseline_frontend_and_lint.txt": "Baseline frontend tests, typecheck, build, cfn-lint",
    "infra_validation.txt": "sam validate --lint and cfn-lint", "final_local_regression.txt": "Final local regression (latest code)",
    "live_api_results.json": "Live API/Cognito/S3/OCR results (latest run)", "sam_deploy_update3_changeset.txt": "Update 3 - About dialog + token revocation check (code-only modifies)", "live_api_test_console.txt": "Console output of the live API test run",
    "live_browser_results.json": "Live browser checks (latest run)", "local_capture_run.json": "Local capture run: shots, 0 console errors, 0 failed requests",
    "cloudwatch_monitoring_evidence.txt": "CloudWatch log groups, alarm state, API/Lambda metrics, log excerpts (incl. the pre-fix import error)",
}.items():
    d(n, w, "Test evidence (JSON)" if n.endswith(".json") else TERM, "account ID masked; no tokens/URLs with signatures")


def main() -> None:
    rows = []
    for folder in sorted(p for p in EV.iterdir() if p.is_dir() and p.name[:2].isdigit()):
        for f in sorted(folder.iterdir()):
            if f.suffix.lower() not in {".png", ".jpg", ".txt", ".json"} or (folder.name == "06_aws_console" and f.suffix == ".json"):
                continue
            what, kind, red = DESC.get(f.name, ("(no description)", TERM if f.suffix == ".txt" else
                                               "Test evidence (JSON)" if f.suffix == ".json" else "", "account ID masked" if f.suffix in {".txt", ".json"} else "none"))
            phase, section = PHASES.get(folder.name, ("", ""))
            ts = dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            rows.append(f"| `{folder.name}/{f.name}` | {ts} | {phase} | {what} | {kind} | {section} | {red} |")
    for sub, kind, section in (("manual/aws-console", "Genuine AWS Management Console screenshot (captured manually by the owner)", "AWS deployment"),
                               ("manual/application", "Genuine application screenshot (captured manually by the owner, real browser)", "Results (live on AWS)")):
        folder = EV / sub
        for f in sorted(folder.glob("*.png")) if folder.exists() else []:
            ts = dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            rows.append(f"| `{sub}/{f.name}` | {ts} | Manual capture by the owner | full-screen capture | {kind} | {section} | **NOT masked** (git-ignored original; masked report copies in docs/report_assets/aws_console/) |")
    md = ["# Evidence & Screenshot Index", "",
          "Types: **Application screenshot** = genuine capture of the running app (local dev or live AWS). **AWS resource view** = page",
          "rendered from live read-only AWS API responses, labelled on the image, *not* a Console screenshot. **Genuine AWS Console",
          "screenshot** = captured by the owner in the AWS Console (`manual/aws-console/`). **Terminal capture** / **Test evidence** = real",
          "command or test output. Diagrams and conceptual illustrations live in `docs/report_assets/` (see REPORT_ASSET_INDEX.md), not here.", "",
          "Generated by `docs/evidence/capture/make_index.py` from the files actually present. Every image was captured from the",
          "running system (local dev server, or the deployed AWS stack). Every text file is real command or test output. Nothing is mocked up.",
          "", "| File | Captured (IST) | Phase | What it demonstrates | Type | Report section | Redactions |",
          "|---|---|---|---|---|---|---|", *rows, "",
          "Capture scripts: `docs/evidence/capture/local.mjs` (local), `live.mjs` (deployed site), `aws_views.py` (AWS resource views).",
          "Genuine AWS Console screenshots (`manual/aws-console/`) are the owner's unmasked originals and are git-ignored; masked copies used in the report are in `docs/report_assets/aws_console/` (see docs/REPORT_ASSET_INDEX.md)."]
    (EV / "SCREENSHOT_INDEX.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(rows)} entries")


if __name__ == "__main__":
    main()
