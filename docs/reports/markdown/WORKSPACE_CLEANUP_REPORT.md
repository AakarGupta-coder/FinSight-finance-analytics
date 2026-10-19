# FinSight — Workspace Cleanup Report

Final consolidation, 2026-10-16. The repository has no commits yet (every file is untracked), so nothing could be recovered
from Git. Every removed file was therefore read first, its unique content was migrated, references to it were updated, and a
copy was kept outside the repository (session scratchpad) during the work. No AWS resource was changed or deleted.
Earlier cleanup (Session 11) removed only git-ignored, regenerable caches (`frontend/dist/`, `tsconfig.tsbuildinfo`,
`.pytest_cache/`, `__pycache__/`, `infra/build/`); its pre-cleanup inventory is
`docs/evidence/01_workspace_audit/initial_repository_inventory.txt`.

## 1. Markdown consolidation (files removed after migration)

| Removed | Content now in |
|---|---|
| `docs/ARCHITECTURE.md`, `docs/ACTUAL_AWS_ARCHITECTURE.md` | `PROJECT_DOCUMENTATION.md` §5–6 (the stale “S3 + CloudFront hosting” statements corrected) |
| `docs/API.md` | §10 (verbatim) |
| `docs/DATABASE_DESIGN.md` | §11 (verbatim) |
| `docs/SECURITY.md`, `docs/SECURITY_REVIEW.md` | §16 (threat model updated for WebFunction headers and token revocation; review verbatim) |
| `docs/AWS_COST_REVIEW.md` | §17 (verbatim, plus the Billing console figures) |
| `docs/AWS_DEPLOYMENT.md`, `docs/AWS_DEPLOYMENT_PLAN.md`, `docs/AWS_IMPLEMENTATION_LOG.md` | §6.6, §8.1, §14 (current procedure, verification, budget alert, permissions, rollback, cleanup, full deployment log, toolchain and the original plan) |
| `docs/TESTING.md` | §13 (commands, latest results, test map updated to 131 tests, frontend tests, live tests, manual checks, not tested) |
| `docs/UI_ANIMATION_IMPLEMENTATION.md` | §5.6 (verbatim) |
| `docs/IMPLEMENTATION_READINESS_AUDIT.md` | Appendix B.1 (defects D1–D4) and B.3 |
| `docs/FINAL_IMPLEMENTATION_AUDIT.md` | §3.1 (verified feature matrix) and §19; superseded by `FINAL_DELIVERABLE_AUDIT.md` |
| `docs/FINAL_HANDOVER.md` | `HANDOVER.md` (current state, remaining actions, Git) |
| `docs/PROJECT_REPORT.md` (outdated Markdown draft that said “not deployed”) | §3.3 (algorithm descriptions); the report itself is the DOCX/PDF |
| `docs/MANUAL_SCREENSHOT_CHECKLIST.md` (task completed — the owner captured the Console) | recapture note in `HANDOVER.md` §7 |
| `docs/AWS_VIVA_CHEAT_SHEET.md` / `.pdf`, `docs/FINSIGHT_AWS_VIVA_GUIDE.md` / `.pdf` | `AWS_VIVA_GUIDE.md` / `.pdf` (Part I: all 8 modules; Part II: all 150 Q&As) |
| `docs/HANDOVER.md` §D–§K (history and design) | `PROJECT_DOCUMENTATION.md` Appendix A (design system) and Appendix B (history, Session 8 tests and file list, Session 9 audit) |

Updated references to the removed files:

- `README.md`;
- `frontend/src/components/AboutAuthor.tsx` (comment);
- `backend/app/repositories/dynamodb_repo.py` (docstring);
- `infra/samconfig.toml` and `infra/template.yaml` (comment and description — the deployed stack description changes only at the next deploy);
- `docs/evidence/capture/make_index.py`;
- the report generators;
- `AWS_VIVA_GUIDE.md`.

Historical evidence files (inventory text, rendered JSON) were left untouched.

## 2. Assets and scripts removed

| Removed | Why |
|---|---|
| `docs/report_assets/aws_illustrations/` (10 HTML + 10 PNG) and `generators/aws_ill.py` | pre-deployment mock-ups with “ILLUSTRATION ONLY” banners; replaced by real evidence and no longer used anywhere |
| `docs/report_assets/aws_evidence/` — 6 of 8 derived views (CloudFormation, DynamoDB, S3, Cognito, CloudWatch, ECR) | duplicated by the masked Console screenshots in the report; the originals stay in `docs/evidence/06_aws_console/` |
| `docs/report_assets/presentation/raster_icons.mjs` | could not run (its input `icons.json` no longer existed); the rendered icons are kept |
| 9 unused icons in `docs/report_assets/presentation/icons/` | not referenced by the new deck |

## 3. Added or replaced

- **New documents:**
  - `docs/PROJECT_DOCUMENTATION.md`;
  - `docs/AWS_VIVA_GUIDE.md` / `.pdf`;
  - `docs/FINAL_DELIVERABLE_AUDIT.md`, `docs/FINAL_VALIDATION.md`, `docs/PRESENTATION_VALIDATION.md`.
- **Rewritten:**
  - `README.md`;
  - `docs/HANDOVER.md`, `docs/REPORT_VALIDATION.md`;
  - the 11-slide deck and its builder `build_presentation.js`.
- **New scripts:**
  - `export_presentation.py` (PowerPoint export);
  - `generators/prep_console.py` (masked Console copies; the unmasked originals are git-ignored);
  - `apply_theme.js` (copied from the pptx tooling so the deck builds without it).

## 4. Deliberately kept

- All application source, tests, configuration and infrastructure, including:
  - `infra/deploy_frontend.py`: needed when CloudFront is enabled;
  - `infra/budgets/`.
- All evidence in `docs/evidence/`. Screenshots are kept even when they are not embedded in the README.
- `docs/AWS_LIVE_TEST_RESULTS.md`: generated per-check results that the report and README cite.
- `docs/evidence/SCREENSHOT_INDEX.md` and `docs/REPORT_ASSET_INDEX.md`: generated indexes, each with a distinct scope (evidence versus report figures).
- The six uncropped report screenshots (`04b`, `07`, `08`, `12`, `21`, `22` in `report_assets/screens/`): genuine captures and the crop sources of the figures actually used.
- The Margie's Travel template, which lives outside the repository (`%APPDATA%\Microsoft\Templates\Travel presentation.potx`) and was not modified.
- `backend/data/` (git-ignored): local database and the local/QA/live test-account credential files.

## 5. Effect on the application

No application code changed behaviour. Only one comment and one docstring changed (§1), plus two new optional entries in
`.env.example` (`COGNITO_REVOCATION_CHECK`, `TOKEN_CHECK_CACHE_SECONDS`, documenting existing settings). Backend (131),
frontend (20), typecheck, build and cfn-lint were re-run after the cleanup and pass ([FINAL_VALIDATION.md](FINAL_VALIDATION.md)).

The audit does not claim that every possible unnecessary file is gone. It covers the documentation, report assets,
presentation assets and scripts reviewed here.
