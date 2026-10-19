# FinSight Report — Asset Index

All visual assets used in `docs/PROJECT_REPORT_FINAL.docx` and `docs/PROJECT_REPORT_FINAL.pdf` are stored under `docs/report_assets/`.
Figure numbers match the report (Word SEQ fields, updated 2026-10-16).

## Asset types — read this first

| Type | Meaning |
|---|---|
| **Genuine application screenshot** | Captured with headless Chrome from FinSight running locally (Vite + FastAPI + SQLite + Tesseract 5.4) on 2026-10-16. The account `demo.user@finsight.test` is fictional and holds only the app's built-in **synthetic demo data**, which the UI labels “Demo”. |
| **Architecture / design diagram** | Deterministic SVG generated from the repository (routes, models, `infra/template.yaml`). A PNG is rendered from it for the DOCX. |
| **AWS resource view (rendered from live AWS API responses)** | Image rendered from the JSON responses of read-only AWS CLI calls on the deployed stack (`docs/evidence/06_aws_console/`, 2026-10-16 14:26 IST). Real data from the live account, **not an AWS Management Console screenshot**; each image carries a banner naming its API sources. Account ID masked as `9672****3724`. The CloudFormation view is cropped to its first 25 of 63 resources; the others have empty background trimmed. |
| **AWS Management Console screenshot (owner capture, masked copy)** | Taken by the owner in the AWS Console on 2026-10-16 (19:18–19:35 IST); originals in `docs/evidence/manual/aws-console/` are **not masked** and are not used directly. The report copies in `report_assets/aws_console/` (made by `generators/prep_console.py`) crop away the browser address bar and the Windows taskbar, cover the console account menu, and black out every account ID in ARNs and the bucket name; an OCR pass found no readable account ID, and each copy was checked by eye. |
| **Live application screenshot (deployed on AWS)** | Captured with headless Chrome from the deployed site (`https://zkht2b4ib3.execute-api.ap-south-1.amazonaws.com`) on 2026-10-16 with a synthetic Cognito test user (`docs/evidence/08_live_application/`). URL bar not shown; no tokens or signed URLs visible. |
| **Generated chart (example data)** | matplotlib chart computed through the local API from the synthetic demo data. Each chart is footnoted as an example, not real user data or a measurement. |
| **Generated chart (verified test counts)** | Counts from `pytest --collect-only` and a passing `pytest` run. |

## Figures in the report

| Fig. | Title | File(s) | Type | Source | Report section |
|---|---|---|---|---|---|
| 1 | High-level system architecture of FinSight | `report_assets/diagrams/fig_system_architecture.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 1.8 System Architecture |
| 2 | Sign-in and registration pages (dark theme) | `report_assets/screens/03_login.png`<br>`report_assets/screens/02_register.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.1 Authentication and User Management |
| 3 | Profile page (cropped to the content area) | `report_assets/screens/21c_profile_content.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.1 Authentication and User Management |
| 4 | Settings page: preferences, appearance, categories, demo data and data deletion (cropped) | `report_assets/screens/22c_settings_content.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.1 Authentication and User Management |
| 5 | Transactions page with summary cards, search and sortable table | `report_assets/screens/06_transactions.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.2 Expense Management |
| 6 | Add-expense form (cropped to the content area) | `report_assets/screens/07c_add_expense_form.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.2 Expense Management |
| 7 | Edit-expense form with the Delete option (cropped to the content area) | `report_assets/screens/08c_edit_expense_form.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.2 Expense Management |
| 8 | Expense detail dialog with Delete and Edit actions | `report_assets/screens/10_expense_detail.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.2 Expense Management |
| 9 | Expense filtering by text, category and payment method (14 matching transactions) | `report_assets/screens/09_filters.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.3 Category and Payment-Method Management |
| 10 | Budgets page: overall budget, alerts, category budgets and history | `report_assets/screens/11_budgets.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.4 Budget Management and Alerts |
| 11 | Dashboard in the dark theme (synthetic demo data, labelled “Demo”) | `report_assets/screens/04_dashboard_dark.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.5 Financial Dashboard |
| 12 | Dashboard in the light theme | `report_assets/screens/05_dashboard_light.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.5 Financial Dashboard |
| 13 | Analytics page (three-month range) | `report_assets/screens/13_analytics.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.6 Spending Analytics |
| 14 | Financial insights with an expanded “Why am I seeing this?” evidence panel | `report_assets/screens/14_insights.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.7 Personal Finance Intelligence Engine |
| 15 | Anomaly alerts with reasons, comparison values and review actions | `report_assets/screens/15_anomalies.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.8 Financial Anomaly Detection |
| 16 | Receipt scanner after genuine Tesseract OCR of a generated sample receipt: extracted fields with confidence and the review form | `report_assets/screens/17_receipt_ocr_review.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.9 Smart Receipt Scanner |
| 17 | What-If simulator comparing two scenarios (results marked “Hypothetical”) | `report_assets/screens/18_simulator.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.10 What-If Financial Simulator |
| 18 | Finance assistant answering two questions with tabular evidence | `report_assets/screens/19_assistant.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.11 Conversational Finance Assistant |
| 19 | Savings goals with progress, required monthly saving and contribution history | `report_assets/screens/20_goals.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.12 Savings Goals |
| 20 | Receipt upload panel (local storage mode) | `report_assets/screens/16_receipts_upload.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 4.13 Receipt Storage |
| 21 | Authentication and authorization sequence (Cognito mode, as deployed) | `report_assets/diagrams/fig_auth_sequence.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 4.17 AWS Authentication and Authorization |
| 22 | Module interaction diagram | `report_assets/diagrams/fig_module_interaction.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 4.19 Module Interaction and Data Flow |
| 23 | Level-1 data flow diagram | `report_assets/diagrams/fig_dfd.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 4.19 Module Interaction and Data Flow |
| 24 | Entity relationship diagram of the logical data model | `report_assets/diagrams/fig_erd.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 4.20 Data Model and Entity Relationship Diagram |
| 25 | Primary user workflow | `report_assets/diagrams/fig_user_workflow.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 5.1 Primary User Workflow |
| 26 | Public landing page | `report_assets/screens/01_landing.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 5.2 Public Landing Page |
| 27 | Mobile layout at 390 px: dashboard (left) and navigation drawer (right) | `report_assets/screens/23_mobile_dashboard.png`<br>`report_assets/screens/24_mobile_navigation.png` | Genuine application screenshot | Locally running FinSight (Vite + FastAPI + SQLite + Tesseract), fictional demo account with the app's labelled synthetic demo data | 5.3 Responsive Design |
| 28 | Example: category-wise spending for the current month (synthetic demo data) | `report_assets/charts/chart_category_breakdown.png` | Generated chart (example data) | matplotlib, computed from FinSight's synthetic demo data through the local API | 7.2 Spending Aggregation and Period Comparison |
| 29 | Example: monthly spending against the overall budget (synthetic demo data) | `report_assets/charts/chart_monthly_spending.png` | Generated chart (example data) | matplotlib, computed from FinSight's synthetic demo data through the local API | 7.2 Spending Aggregation and Period Comparison |
| 30 | Example: budget utilization by budget (synthetic demo data) | `report_assets/charts/chart_budget_utilization.png` | Generated chart (example data) | matplotlib, computed from FinSight's synthetic demo data through the local API | 7.3 Budget Utilization, Thresholds and Projection |
| 31 | Anomaly detection flow for a new or edited expense | `report_assets/diagrams/fig_anomaly_flow.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 7.6 Anomaly Detection |
| 32 | Example: modified z-scores of Shopping transactions (synthetic demo data) | `report_assets/charts/chart_anomaly_zscores.png` | Generated chart (example data) | matplotlib, computed from FinSight's synthetic demo data through the local API | 7.6 Anomaly Detection |
| 33 | Smart receipt scanner pipeline | `report_assets/diagrams/fig_ocr_pipeline.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 7.7 OCR Extraction and Receipt Parsing |
| 34 | Example: hypothetical monthly savings of three What-If scenarios (synthetic demo data) | `report_assets/charts/chart_whatif_scenarios.png` | Generated chart (example data) | matplotlib, computed from FinSight's synthetic demo data through the local API | 7.8 What-If Simulation |
| 35 | Example: savings goal progress (synthetic demo data) | `report_assets/charts/chart_goal_progress.png` | Generated chart (example data) | matplotlib, computed from FinSight's synthetic demo data through the local API | 7.10 Savings Goal Metrics |
| 36 | Backend automated tests per module (all 131 passed) | `report_assets/charts/chart_tests_per_module.png` | Generated chart (verified test counts) | pytest --collect-only and a full pytest run on the repository (2026-10-16) | 8.2 Automated Test Results |
| 37 | Live dashboard on AWS after Cognito sign-in (synthetic test user; data from DynamoDB) | `report_assets/live/live_dashboard.png` | Live application screenshot (deployed on AWS) | docs/evidence/08_live_application (headless Chrome on the live URL, synthetic test user, 2026-10-16) | 8.4 Live Testing on AWS |
| 38 | Live receipt scanner: image uploaded to the private S3 bucket and read by the Tesseract container function, with fields awaiting review | `report_assets/live/live_receipt_review.png` | Live application screenshot (deployed on AWS) | docs/evidence/08_live_application (headless Chrome on the live URL, synthetic test user, 2026-10-16) | 8.4 Live Testing on AWS |
| 39 | Live application at 390 px: dashboard (left) and navigation drawer (right) | `report_assets/live/live_mobile_dashboard.png`<br>`report_assets/live/live_mobile_navigation.png` | Live application screenshot (deployed on AWS) | docs/evidence/08_live_application (headless Chrome on the live URL, synthetic test user, 2026-10-16) | 8.4 Live Testing on AWS |
| 40 | About the author dialog on the live landing page, opened from the information button (dark theme) | `report_assets/live/live_about_author_dark.png` | Live application screenshot (deployed on AWS) | docs/evidence/08_live_application (headless Chrome on the live URL, synthetic test user, 2026-10-16) | 8.4 Live Testing on AWS |
| 41 | Live landing page footer with the “Created by Aakar Gupta” credit, which opens the same dialog | `report_assets/live/live_landing_footer_credit.png` | Live application screenshot (deployed on AWS) | docs/evidence/08_live_application (headless Chrome on the live URL, synthetic test user, 2026-10-16) | 8.4 Live Testing on AWS |
| 42 | Deployed AWS architecture of FinSight (FrontendHosting=apigateway) | `report_assets/diagrams/fig_aws_architecture.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 9.1 Deployed Architecture |
| 43 | CloudFormation events: FrontendDistribution CREATE_FAILED, rollback and deletion of the failed attempt (AWS Console; account ID masked) | `report_assets/aws_console/13-cloudfront-limitation.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.2 Frontend Hosting Decision |
| 44 | AWS SAM deployment workflow as executed | `report_assets/diagrams/fig_deploy_workflow.png` | Architecture / design diagram | Generated SVG (deterministic, from repository code and infra/template.yaml) | 9.4 Deployment Workflow |
| 45 | CloudFormation: the three FinSight stacks and the finance-intelligence-prod overview (UPDATE_COMPLETE) (AWS Console; account ID masked) | `report_assets/aws_console/01-cloudformation-stack.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 46 | CloudFormation outputs: WebUrl and ApiUrl on one origin, FrontendHosting=apigateway, table, bucket and Cognito identifiers (AWS Console; account ID masked) | `report_assets/aws_console/02-cloudformation-outputs.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 47 | API Gateway: the CognitoJwt authorizer attached to the API routes (JWT Auth) (AWS Console; account ID masked) | `report_assets/aws_console/03-api-gateway.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 48 | Lambda: the nine FinSight functions (eight zip packages on Python 3.13 and the OCR container image) (AWS Console; account ID masked) | `report_assets/aws_console/04-lambda-functions.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 49 | DynamoDB: table finance-intelligence-prod, on-demand capacity, PK/SK keys, point-in-time recovery off (AWS Console; account ID masked) | `report_assets/aws_console/05-dynamodb.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 50 | Cognito: user pool finance-intelligence-prod on the Lite feature plan (AWS Console; account ID masked) | `report_assets/aws_console/06-cognito.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 51 | S3: receipts bucket permissions with Block all public access turned on (AWS Console; account ID masked) | `report_assets/aws_console/07-s3-receipt-storage.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 52 | ECR: the three OCR container image versions; the newest is used by the receipts function (AWS Console; account ID masked) | `report_assets/aws_console/08-ecr-ocr.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 53 | CloudWatch Logs: receipts-function log events with method, path, status and duration only (AWS Console; account ID masked) | `report_assets/aws_console/09-cloudwatch-logs.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 54 | CloudWatch: ApiServerErrorsAlarm (5xx ≥ 5 in 5 minutes) in state OK (AWS Console; account ID masked) | `report_assets/aws_console/10-cloudwatch-alarms.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 55 | IAM: one execution role per FinSight function, created by the stack (AWS Console; account ID masked) | `report_assets/aws_console/11-iam-roles.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.5 Deployed Resources in the AWS Management Console |
| 56 | Deployed Lambda functions (eight API functions and WebFunction) and their shared non-secret environment (rendered from live AWS API responses — not a Console screenshot) | `report_assets/aws_evidence/aws_lambda_functions.png` | AWS resource view (rendered from live AWS API responses; not a Console screenshot) | docs/evidence/06_aws_console (read-only AWS CLI calls on the deployed stack, 2026-10-16 14:26 IST; account ID masked) | 9.6 Resource Views Rendered from AWS API Responses |
| 57 | API Gateway HTTP API: Cognito JWT authorizer and the 25 routes with their authorization type (rendered from live AWS API responses — not a Console screenshot) | `report_assets/aws_evidence/aws_api_gateway.png` | AWS resource view (rendered from live AWS API responses; not a Console screenshot) | docs/evidence/06_aws_console (read-only AWS CLI calls on the deployed stack, 2026-10-16 14:26 IST; account ID masked) | 9.6 Resource Views Rendered from AWS API Responses |
| 58 | Billing and Cost Management: credits summary on 16 October 2026 (AWS Console; account ID masked) | `report_assets/aws_console/12-aws-billing.png` | AWS Management Console screenshot (owner capture, masked copy) | docs/evidence/manual/aws-console (owner, 16 Oct 2026 19:18–19:35 IST); browser bar, account menu and taskbar cropped or covered, account ID blacked out (prep_console.py) | 9.8 Cost Analysis |

## Tables in the report

| Table | Caption |
|---|---|
| 1 | Technology stack and rationale |
| 2 | Functional requirements and implementation status |
| 3 | Non-functional requirements |
| 4 | Literature review summary |
| 5 | Module specification — Authentication and User Management |
| 6 | Module specification — Expense Management |
| 7 | Module specification — Category and Payment-Method Management |
| 8 | Module specification — Budget Management and Alerts |
| 9 | Module specification — Financial Dashboard |
| 10 | Module specification — Spending Analytics |
| 11 | Module specification — Personal Finance Intelligence Engine |
| 12 | Module specification — Financial Anomaly Detection |
| 13 | Module specification — Smart Receipt Scanner |
| 14 | Module specification — What-If Financial Simulator |
| 15 | Module specification — Conversational Finance Assistant |
| 16 | Module specification — Savings Goals |
| 17 | API summary (paths relative to /api/v1) |
| 18 | SQLite schema |
| 19 | User workflow steps and corresponding screens |
| 20 | Requirements traceability matrix |
| 21 | Local execution compared with the AWS deployment |
| 22 | Automated and scripted test results |
| 23 | Representative test cases |
| 24 | Live AWS test results by area (64 passed, 0 failed) |
| 25 | Problems found during deployment and live testing |
| 26 | AWS resource mapping and deployment status |
| 27 | Security controls and their verification status |

## All files in `docs/report_assets/`

The `.svg` and `.html` files are the editable sources of the PNG files with the same name. Files not used in the report are kept for completeness.

| File | Used as | Notes |
|---|---|---|
| `report_assets/figure_table_manifest.json` | manifest | Figure and table numbers, captions, types and sources |
| `report_assets/aws_console/01-cloudformation-stack.png` | Figure 45 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/02-cloudformation-outputs.png` | Figure 46 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/03-api-gateway.png` | Figure 47 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/04-lambda-functions.png` | Figure 48 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/05-dynamodb.png` | Figure 49 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/06-cognito.png` | Figure 50 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/07-s3-receipt-storage.png` | Figure 51 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/08-ecr-ocr.png` | Figure 52 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/09-cloudwatch-logs.png` | Figure 53 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/10-cloudwatch-alarms.png` | Figure 54 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/11-iam-roles.png` | Figure 55 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/12-aws-billing.png` | Figure 58 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_console/13-cloudfront-limitation.png` | Figure 43 | AWS Management Console screenshot (owner capture, masked copy) |
| `report_assets/aws_evidence/aws_api_gateway.png` | Figure 57 | AWS resource view (rendered from live AWS API responses; not a Console screenshot) |
| `report_assets/aws_evidence/aws_lambda_functions.png` | Figure 56 | AWS resource view (rendered from live AWS API responses; not a Console screenshot) |
| `report_assets/branding/vit_chennai_logo.png` | title page | Official VIT Chennai logo from https://chennai.vit.ac.in (white web version recoloured navy on white for print) |
| `report_assets/charts/chart_anomaly_zscores.png` | Figure 32 | Generated chart (example data) |
| `report_assets/charts/chart_budget_utilization.png` | Figure 30 | Generated chart (example data) |
| `report_assets/charts/chart_category_breakdown.png` | Figure 28 | Generated chart (example data) |
| `report_assets/charts/chart_goal_progress.png` | Figure 35 | Generated chart (example data) |
| `report_assets/charts/chart_monthly_spending.png` | Figure 29 | Generated chart (example data) |
| `report_assets/charts/chart_tests_per_module.png` | Figure 36 | Generated chart (verified test counts) |
| `report_assets/charts/chart_whatif_scenarios.png` | Figure 34 | Generated chart (example data) |
| `report_assets/diagrams/fig_anomaly_flow.png` | Figure 31 | Architecture / design diagram |
| `report_assets/diagrams/fig_anomaly_flow.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/diagrams/fig_auth_sequence.png` | Figure 21 | Architecture / design diagram |
| `report_assets/diagrams/fig_auth_sequence.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/diagrams/fig_aws_architecture.png` | Figure 42 | Architecture / design diagram |
| `report_assets/diagrams/fig_aws_architecture.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/diagrams/fig_deploy_workflow.png` | Figure 44 | Architecture / design diagram |
| `report_assets/diagrams/fig_deploy_workflow.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/diagrams/fig_dfd.png` | Figure 23 | Architecture / design diagram |
| `report_assets/diagrams/fig_dfd.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/diagrams/fig_erd.png` | Figure 24 | Architecture / design diagram |
| `report_assets/diagrams/fig_erd.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/diagrams/fig_module_interaction.png` | Figure 22 | Architecture / design diagram |
| `report_assets/diagrams/fig_module_interaction.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/diagrams/fig_ocr_pipeline.png` | Figure 33 | Architecture / design diagram |
| `report_assets/diagrams/fig_ocr_pipeline.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/diagrams/fig_system_architecture.png` | Figure 1 | Architecture / design diagram |
| `report_assets/diagrams/fig_system_architecture.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/diagrams/fig_user_workflow.png` | Figure 25 | Architecture / design diagram |
| `report_assets/diagrams/fig_user_workflow.svg` | vector source | SVG original of the PNG with the same name |
| `report_assets/generators/build_report.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/capture.mjs` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/chart_tests.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/charts.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/diagrams.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/edit_front.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/make_index.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/md_to_pdf.mjs` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/prep_console.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/prep_evidence.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/render.mjs` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/rep_part1.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/rep_part2.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/replib.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/sample_receipt_generated.png` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/validate.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/generators/word_finalize.py` | generator | Script or input used to produce the assets or the report (paths are machine-specific) |
| `report_assets/live/live_about_author_dark.png` | Figure 40 | Live application screenshot (deployed on AWS) |
| `report_assets/live/live_dashboard.png` | Figure 37 | Live application screenshot (deployed on AWS) |
| `report_assets/live/live_landing_footer_credit.png` | Figure 41 | Live application screenshot (deployed on AWS) |
| `report_assets/live/live_mobile_dashboard.png` | Figure 39 | Live application screenshot (deployed on AWS) |
| `report_assets/live/live_mobile_navigation.png` | Figure 39 | Live application screenshot (deployed on AWS) |
| `report_assets/live/live_receipt_review.png` | Figure 38 | Live application screenshot (deployed on AWS) |
| `report_assets/presentation/apply_theme.js` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/build_presentation.js` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/export_presentation.py` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/AlertTriangle.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Code2.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Database.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Eye.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/FlaskConical.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Gauge.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Globe.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/HardDrive.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/HelpCircle.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/KeyRound.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Layers.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Lock.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/PiggyBank.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Receipt.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/ScanLine.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Server.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/ShieldAlert.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Sparkles.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/TrendingUp.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Users.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/Wallet.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/presentation/icons/brandmark.png` | presentation asset (not in report) | Used by the slide deck docs/PROJECT_PRESENTATION_FINAL.pptx |
| `report_assets/screens/01_landing.png` | Figure 26 | Genuine application screenshot |
| `report_assets/screens/02_register.png` | Figure 2 | Genuine application screenshot |
| `report_assets/screens/03_login.png` | Figure 2 | Genuine application screenshot |
| `report_assets/screens/04_dashboard_dark.png` | Figure 11 | Genuine application screenshot |
| `report_assets/screens/04b_dashboard_dark_viewport.png` | not used in report | Genuine screenshot captured but not inserted (superseded by a cropped or alternative view) |
| `report_assets/screens/05_dashboard_light.png` | Figure 12 | Genuine application screenshot |
| `report_assets/screens/06_transactions.png` | Figure 5 | Genuine application screenshot |
| `report_assets/screens/07_add_expense.png` | not used in report | Genuine screenshot captured but not inserted (superseded by a cropped or alternative view) |
| `report_assets/screens/07c_add_expense_form.png` | Figure 6 | Genuine application screenshot |
| `report_assets/screens/08_edit_expense.png` | not used in report | Genuine screenshot captured but not inserted (superseded by a cropped or alternative view) |
| `report_assets/screens/08c_edit_expense_form.png` | Figure 7 | Genuine application screenshot |
| `report_assets/screens/09_filters.png` | Figure 9 | Genuine application screenshot |
| `report_assets/screens/10_expense_detail.png` | Figure 8 | Genuine application screenshot |
| `report_assets/screens/11_budgets.png` | Figure 10 | Genuine application screenshot |
| `report_assets/screens/12_budget_edit_dialog.png` | not used in report | Genuine screenshot captured but not inserted (superseded by a cropped or alternative view) |
| `report_assets/screens/13_analytics.png` | Figure 13 | Genuine application screenshot |
| `report_assets/screens/14_insights.png` | Figure 14 | Genuine application screenshot |
| `report_assets/screens/15_anomalies.png` | Figure 15 | Genuine application screenshot |
| `report_assets/screens/16_receipts_upload.png` | Figure 20 | Genuine application screenshot |
| `report_assets/screens/17_receipt_ocr_review.png` | Figure 16 | Genuine application screenshot |
| `report_assets/screens/18_simulator.png` | Figure 17 | Genuine application screenshot |
| `report_assets/screens/19_assistant.png` | Figure 18 | Genuine application screenshot |
| `report_assets/screens/20_goals.png` | Figure 19 | Genuine application screenshot |
| `report_assets/screens/21_profile.png` | not used in report | Genuine screenshot captured but not inserted (superseded by a cropped or alternative view) |
| `report_assets/screens/21c_profile_content.png` | Figure 3 | Genuine application screenshot |
| `report_assets/screens/22_settings.png` | not used in report | Genuine screenshot captured but not inserted (superseded by a cropped or alternative view) |
| `report_assets/screens/22c_settings_content.png` | Figure 4 | Genuine application screenshot |
| `report_assets/screens/23_mobile_dashboard.png` | Figure 27 | Genuine application screenshot |
| `report_assets/screens/24_mobile_navigation.png` | Figure 27 | Genuine application screenshot |
