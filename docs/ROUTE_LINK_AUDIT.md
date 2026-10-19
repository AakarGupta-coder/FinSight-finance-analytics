# FinSight — Complete Route, Link & Navigation Audit

Date: 2026-10-16  
Status: Passed (All identified broken references fixed & verified)

---

## 1. Application Routes Audit

Every frontend route defined in `frontend/src/App.tsx` and referenced across sidebar navigation, quick search, page headers, action links, and cards was inspected:

| Route Path | Page Component | Guard / Access | Navigation Source(s) | Status |
|---|---|---|---|---|
| `/` | `LandingPage` | Public | Home / logo, logout redirect, direct URL | Valid |
| `/login` | `LoginPage` | `GuestOnly` | Header buttons, redirect on unauthenticated private access | Valid |
| `/register` | `RegisterPage` | `GuestOnly` | Header buttons, landing CTA, auth footer switch | Valid |
| `/app` | `DashboardPage` | `RequireAuth` | Sidebar "Dashboard", logo, auth redirect | Valid |
| `/app/transactions` | `TransactionsPage` | `RequireAuth` | Sidebar "Transactions", dashboard card links, receipt upload finish | Valid |
| `/app/transactions/new` | `ExpenseEditorPage` | `RequireAuth` | Dashboard "+ Add expense", Transactions "+ Add expense" | Valid |
| `/app/transactions/:id/edit` | `ExpenseEditorPage` | `RequireAuth` | Transactions row edit, expense detail dialog edit, anomaly review edit | Valid |
| `/app/budgets` | `BudgetsPage` | `RequireAuth` | Sidebar "Budgets", dashboard card links | Valid |
| `/app/analytics` | `AnalyticsPage` | `RequireAuth` | Sidebar "Analytics", dashboard card links | Valid |
| `/app/insights` | `InsightsPage` | `RequireAuth` | Sidebar "Financial insights", dashboard card links | Valid |
| `/app/anomalies` | `AnomaliesPage` | `RequireAuth` | Sidebar "Anomaly detection", header bell indicator, dashboard card link | Valid |
| `/app/receipts` | `ReceiptsPage` | `RequireAuth` | Sidebar "Receipt scanner", expense editor alternate CTA | Valid |
| `/app/simulator` | `SimulatorPage` | `RequireAuth` | Sidebar "What-If simulator", assistant recommendation link | Valid |
| `/app/goals` | `GoalsPage` | `RequireAuth` | Sidebar "Savings goals", dashboard card links | Valid |
| `/app/assistant` | `AssistantPage` | `RequireAuth` | Sidebar "Finance assistant" | Valid |
| `/app/profile` | `ProfilePage` | `RequireAuth` | Sidebar "Profile", top-right user avatar menu | Valid |
| `/app/settings` | `SettingsPage` | `RequireAuth` | Sidebar "Settings", budget threshold links, demo data CTA | Valid |
| `/transactions` | `RedirectIntoApp` | Public redirect | Dynamic insight action link fallback → `/app/transactions` | Valid |
| `/budgets` | `RedirectIntoApp` | Public redirect | Dynamic insight action link fallback → `/app/budgets` | Valid |
| `/goals` | `RedirectIntoApp` | Public redirect | Dynamic insight action link fallback → `/app/goals` | Valid |
| `/simulator` | `RedirectIntoApp` | Public redirect | Dynamic insight action link fallback → `/app/simulator` | Valid |
| `*` / `/app/*` | `NotFoundPage` | Public / InApp | Handles arbitrary unknown paths, preserves brand shell | Valid |

---

## 2. Internal Documentation & Relative Link Fixes

Automated AST scan checked all Markdown files across the project. 47 broken links caused by the reorganization of `docs/` were detected and corrected:

### A. Root `README.md`
- Fixed diagram link: `docs/report_assets/diagrams/fig_aws_architecture.svg` → `docs/reports/report_assets/diagrams/fig_aws_architecture.svg`
- Fixed technical doc links (sections 5, 6, 11, 13, 14, 16, 17, 18): `docs/PROJECT_DOCUMENTATION.md` → `docs/reports/markdown/PROJECT_DOCUMENTATION.md`
- Fixed live test results links: `docs/AWS_LIVE_TEST_RESULTS.md` → `docs/reports/markdown/AWS_LIVE_TEST_RESULTS.md`
- Fixed documentation index table:
  - `docs/HANDOVER.md` → `docs/handover/HANDOVER.md`
  - `docs/AWS_VIVA_GUIDE.md` → `docs/viva/AWS_VIVA_GUIDE.md` (and PDF to `docs/pdfs/AWS_VIVA_GUIDE.pdf`)
  - `docs/PROJECT_REPORT_FINAL.pdf` → `docs/pdfs/PROJECT_REPORT_FINAL.pdf` (and DOCX to `docs/reports/PROJECT_REPORT_FINAL.docx`)
  - `docs/PROJECT_PRESENTATION_FINAL.pdf` → `docs/pdfs/PROJECT_PRESENTATION_FINAL.pdf` (and PPTX to `docs/presentations/PROJECT_PRESENTATION_FINAL.pptx`)
  - `docs/REPORT_ASSET_INDEX.md` → `docs/reports/REPORT_ASSET_INDEX.md`
  - `docs/FINAL_VALIDATION.md` → `docs/reports/markdown/FINAL_VALIDATION.md`
  - `docs/WORKSPACE_CLEANUP_REPORT.md` → `docs/reports/markdown/WORKSPACE_CLEANUP_REPORT.md`

### B. `docs/handover/HANDOVER.md`
- Updated relative cross-links to point to `../reports/markdown/PROJECT_DOCUMENTATION.md` (sections 6, 14, 19, Appendix B).
- Updated relative links to `../reports/markdown/AWS_LIVE_TEST_RESULTS.md`, `../evidence/SCREENSHOT_INDEX.md`, `../reports/REPORT_ASSET_INDEX.md`, `../viva/AWS_VIVA_GUIDE.md`, and `../pdfs/AWS_VIVA_GUIDE.pdf`.
- Updated validation links to `../reports/markdown/FINAL_VALIDATION.md`, `REPORT_VALIDATION.md`, `PRESENTATION_VALIDATION.md`, `FINAL_DELIVERABLE_AUDIT.md`, and `WORKSPACE_CLEANUP_REPORT.md`.

### C. `docs/reports/markdown/FINAL_DELIVERABLE_AUDIT.md`
- Corrected relative paths to root `README.md` (`../../../README.md`), `HANDOVER.md` (`../../handover/HANDOVER.md`), and `AWS_VIVA_GUIDE.md` (`../../viva/AWS_VIVA_GUIDE.md`).

### D. `docs/reports/markdown/PROJECT_DOCUMENTATION.md`
- Corrected header relative link to root `README.md` (`../../../README.md`) and `HANDOVER.md` (`../../handover/HANDOVER.md`).
- Corrected local setup link in §7 to `../../../README.md#local-setup`.
- Corrected asset map links in §21 to `../../evidence/SCREENSHOT_INDEX.md` and `../REPORT_ASSET_INDEX.md`.

### E. `docs/viva/AWS_VIVA_GUIDE.md`
- Updated technical reference links to `../reports/markdown/PROJECT_DOCUMENTATION.md`.

**Re-validation:** After fixes, total broken links across all markdown files: **0**.

---

## 3. Backend API Routes & Frontend Call Alignment

Verified complete contract symmetry between frontend calls and backend handlers:

| Route Group | Endpoint | Methods | Frontend Caller | Backend Route Definition |
|---|---|---|---|---|
| **Auth** | `/auth/register` | POST | `RegisterPage` | `backend/app/api/routes/auth.py` |
| | `/auth/login` | POST | `LoginPage` | `backend/app/api/routes/auth.py` |
| | `/auth/change-password` | POST | `ProfilePage` | `backend/app/api/routes/auth.py` |
| **Account** | `/me` | GET | `AppDataProvider` | `backend/app/api/routes/account.py` |
| | `/reference` | GET | `AppDataProvider` | `backend/app/api/routes/account.py` |
| | `/preferences` | PUT | `SettingsPage`, `ProfilePage` | `backend/app/api/routes/account.py` |
| | `/categories` | POST, DELETE | `SettingsPage` | `backend/app/api/routes/account.py` |
| | `/demo-data` | POST, DELETE | `DashboardPage`, `SettingsPage` | `backend/app/api/routes/account.py` |
| | `/account/delete-data`| POST | `SettingsPage` | `backend/app/api/routes/account.py` |
| **Expenses** | `/expenses` | GET, POST | `TransactionsPage`, `DashboardPage`, `ExpenseEditorPage` | `backend/app/api/routes/expenses.py` |
| | `/expenses/{id}` | GET, PUT, DELETE | `ExpenseEditorPage`, `TransactionsPage` | `backend/app/api/routes/expenses.py` |
| **Budgets** | `/budgets` | GET, POST | `BudgetsPage`, `DashboardPage` | `backend/app/api/routes/budgets.py` |
| | `/budgets/{id}` | PUT, DELETE | `BudgetsPage` | `backend/app/api/routes/budgets.py` |
| | `/budgets/history` | GET | `BudgetsPage`, `DashboardPage` | `backend/app/api/routes/budgets.py` |
| **Analytics** | `/dashboard` | GET | `DashboardPage` | `backend/app/api/routes/analytics.py` |
| | `/analytics` | GET | `AnalyticsPage` | `backend/app/api/routes/analytics.py` |
| | `/insights` | GET | `InsightsPage`, `DashboardPage` | `backend/app/api/routes/analytics.py` |
| **Anomalies** | `/anomalies` | GET, POST | `AnomaliesPage`, `AppShell` header | `backend/app/api/routes/anomalies.py` |
| | `/anomalies/{id}/review` | POST | `AnomaliesPage` | `backend/app/api/routes/anomalies.py` |
| **Receipts** | `/receipts` | GET, POST | `ReceiptsPage` | `backend/app/api/routes/receipts.py` |
| | `/receipts/status` | GET | `ReceiptsPage` | `backend/app/api/routes/receipts.py` |
| | `/receipts/upload-url` | POST | `ReceiptsPage` (presigned S3 mode) | `backend/app/api/routes/receipts.py` |
| | `/receipts/{id}` | GET, DELETE | `ReceiptsPage` | `backend/app/api/routes/receipts.py` |
| | `/receipts/{id}/image` | GET | `TransactionsPage` (receipt view) | `backend/app/api/routes/receipts.py` |
| | `/receipts/{id}/confirm` | POST | `ReceiptsPage` | `backend/app/api/routes/receipts.py` |
| **Planning** | `/goals` | GET, POST | `GoalsPage`, `DashboardPage`, `SimulatorPage` | `backend/app/api/routes/planning.py` |
| | `/goals/{id}` | PUT, DELETE | `GoalsPage` | `backend/app/api/routes/planning.py` |
| | `/goals/{id}/contributions` | POST | `GoalsPage` | `backend/app/api/routes/planning.py` |
| | `/simulations` | POST | `SimulatorPage` | `backend/app/api/routes/planning.py` |
| **Assistant**| `/assistant/query` | POST | `AssistantPage` | `backend/app/api/routes/account.py` |

---

## 4. AWS & Deployment URL Verification

- **Actual Stack Configuration:** Verified in `infra/samconfig.toml` (`FrontendHosting=apigateway`, region `ap-south-1`, stack `finance-intelligence-prod`).
- **Live Endpoint:** `https://zkht2b4ib3.execute-api.ap-south-1.amazonaws.com` (API Gateway HTTP API serving both the SPA via `WebFunction` and `/api/v1` routes).
- **Same-Origin Design:** `frontend/src/lib/api.ts` uses empty `VITE_API_BASE_URL` in production builds (`prepare_build.py`), eliminating cross-origin API calls and avoiding stale domain dependencies.
- **No Hardcoded Development URLs:** Confirmed 0 hardcoded `localhost` or dev endpoints in `frontend/src/`.
- **CloudFront Verification:** The template contains CloudFront configuration for future activation, but correctly defaults to `FrontendHosting=apigateway` pending account verification.

---

## 5. Automated Validation Results

- **Backend Pytest Suite:** 131/131 passed (`pytest -q`).
- **Frontend Vitest Suite:** 20/20 passed (`vitest run`).
- **Frontend Typecheck:** `tsc -b` passed with 0 errors.
- **Frontend Production Build:** Vite build succeeded (temporary `dist/` cleaned).
- **Link & Asset Verification:** 0 broken markdown links, 0 broken image sources.
