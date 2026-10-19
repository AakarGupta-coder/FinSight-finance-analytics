# FinSight — Final Validation Summary (2026-10-16)

Every result below was obtained on 2026-10-16. Detailed checks: [REPORT_VALIDATION.md](REPORT_VALIDATION.md) (report) and
[PRESENTATION_VALIDATION.md](PRESENTATION_VALIDATION.md) (presentation).

## Application and deployment

| Check | Result |
|---|---|
| Backend `pytest` (after the final cleanup) | **131 passed** |
| AWS-path subset (DynamoDB/S3 with moto, Lambda handlers, security, Cognito tokens, web handler) | **32 passed** |
| Frontend Vitest | **20 passed** (4 files) |
| `npm run typecheck` / `npm run build` | pass / pass |
| `cfn-lint infra/template.yaml` | exit 0 |
| Live smoke test of <https://zkht2b4ib3.execute-api.ap-south-1.amazonaws.com> | `/` 200 (FinSight HTML), `/app/budgets` 200 (SPA fallback), `/api/v1/health` 200 `{"status":"ok","database":"ok","environment":"production","data_backend":"dynamodb"}`, `/api/v1/config` 200, `/api/v1/expenses` without a token 401 |
| Stack (read-only CLI) | `UPDATE_COMPLETE`, `FrontendHosting=apigateway`; CloudFront **not** deployed |
| Live API suite / live browser suite (latest full runs, not repeated: no deployed code changed since) | **64/64 PASS** / **27/27**, 0 console errors, 0 failed requests ([AWS_LIVE_TEST_RESULTS.md](AWS_LIVE_TEST_RESULTS.md)) |

## Deliverables

| Deliverable | Result |
|---|---|
| `docs/PROJECT_REPORT_FINAL.docx` / `.pdf` | 92 pages, 58 figures, 27 tables, 25 references. `validate.py`: 0 missing sections, 0 uncited references, 0 unreferenced figures or tables, 101 contents entries with 0 mismatches, 0 secrets, passwords or unmasked IDs. All pages visually inspected |
| `docs/PROJECT_PRESENTATION_FINAL.pptx` / `.pdf` | 11 editable slides. Schema validation passed; opens and exports in PowerPoint; all slides visually inspected; no placeholder text or IDs |
| `docs/AWS_VIVA_GUIDE.md` / `.pdf` | 8 syllabus modules + 150 questions with answers; 26-page PDF |
| `README.md`, `docs/PROJECT_DOCUMENTATION.md`, `docs/HANDOVER.md` | consolidated |

## Documentation integrity

| Check | Result |
|---|---|
| Relative links, anchors and image paths in all Markdown files (README, `docs/*.md`, evidence index) | **all resolve** (158 links checked, 0 problems) |
| Mermaid diagrams (README and PROJECT_DOCUMENTATION) | 4 of 4 render with Mermaid 10.9.1 (headless Chrome), 0 syntax errors |
| README screenshots | 10 genuine live screenshots from `docs/evidence/08_live_application/`, all present |
| References to removed Markdown files | none, except in historical evidence files and in the audit and cleanup records that list them |
| Secrets in Markdown | 0 AWS keys, JWTs, private keys, password assignments, test-account passwords or unmasked 12-digit account IDs |
| Unmasked Console originals | git-ignored (`docs/evidence/manual/aws-console/Screenshot*.png`); masked copies used everywhere else |
| Git status | no commits; 405 files would be added by `git add -A`, none of them local data, `.env`, build output, `node_modules` or the unmasked originals |

## Not verified

- CloudFront delivery: not deployed.
- Browsers other than Chromium, and assistive technologies.
- Load and performance, and OCR accuracy on real receipts.
- How the PPTX renders on machines without Arial Black or Calibri.
