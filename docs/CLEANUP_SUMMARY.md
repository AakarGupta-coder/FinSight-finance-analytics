# FinSight — Repository Cleanup Summary

Date: 2026-10-16  
Audit & Verification: Completed

---

## 1. Final Directory Structure

Documentation hierarchy organized into clean, discoverable functional subdirectories:

```text
docs/
├── README.md                      # Preserved at repository root (primary entry point)
├── CLEANUP_SUMMARY.md             # This concise cleanup and inventory summary
├── handover/
│   └── HANDOVER.md                # Primary operational handover and current state
├── reports/
│   ├── PROJECT_REPORT_FINAL.docx  # Canonical editable final report (92 pages)
│   ├── REPORT_ASSET_INDEX.md      # Index of visual assets and report figures
│   ├── report_assets/             # Visible source assets (screens, diagrams, charts, console)
│   │   ├── aws_console/           # Masked AWS Console captures
│   │   ├── aws_evidence/          # Masked AWS API evidence views
│   │   ├── branding/              # Institutional logos
│   │   ├── charts/                # Generated analytical charts
│   │   ├── diagrams/              # Architectural SVGs & PNGs
│   │   ├── live/                  # Headless captures of live AWS deployment
│   │   ├── presentation/          # Deck assets
│   │   ├── screens/               # Headless application screens
│   │   └── figure_table_manifest.json
│   └── markdown/                  # Consolidated technical documentation & test reports
│       ├── AWS_LIVE_TEST_RESULTS.md
│       ├── FINAL_DELIVERABLE_AUDIT.md
│       ├── FINAL_VALIDATION.md
│       ├── PRESENTATION_VALIDATION.md
│       ├── PROJECT_DOCUMENTATION.md
│       ├── REPORT_VALIDATION.md
│       └── WORKSPACE_CLEANUP_REPORT.md
├── presentations/
│   ├── PROJECT_PRESENTATION_FINAL.pptx # Canonical editable final presentation (11 slides)
│   └── assets/                         # Presentation icon assets
│       └── icons/
├── viva/
│   └── AWS_VIVA_GUIDE.md          # 8 syllabus modules + 150 viva Q&As
├── pdfs/
│   ├── PROJECT_REPORT_FINAL.pdf        # Canonical 92-page academic report PDF
│   ├── PROJECT_PRESENTATION_FINAL.pdf  # Canonical 11-slide presentation PDF
│   └── AWS_VIVA_GUIDE.pdf              # Canonical 26-page viva preparation PDF
└── evidence/
    ├── 01_workspace_audit/
    ├── 02_local_application/
    ├── 03_frontend_design/
    ├── 04_animations/
    ├── 05_aws_toolchain/
    ├── 06_aws_console/
    ├── 07_aws_deployment/
    ├── 08_live_application/
    ├── 09_testing/
    ├── 10_monitoring/
    ├── capture/                   # Verification & screenshot capture harnesses
    ├── manual/                    # Unmasked original console screenshots (git-ignored)
    └── SCREENSHOT_INDEX.md
```

---

## 2. Document Locations & Deliverables

All canonical deliverables are organized into dedicated directories:

| Deliverable | Format | Canonical Path | Status |
|---|---|---|---|
| Project Report Source | DOCX | `docs/reports/PROJECT_REPORT_FINAL.docx` | Verified (81 XML parts, 92 pages) |
| Project Report PDF | PDF | `docs/pdfs/PROJECT_REPORT_FINAL.pdf` | Verified (92 pages, valid bookmarks) |
| Presentation Source | PPTX | `docs/presentations/PROJECT_PRESENTATION_FINAL.pptx` | Verified (102 XML parts, 11 slides) |
| Presentation PDF | PDF | `docs/pdfs/PROJECT_PRESENTATION_FINAL.pdf` | Verified (11 pages) |
| Viva Preparation Guide | Markdown | `docs/viva/AWS_VIVA_GUIDE.md` | Verified (8 modules, 150 Q&As) |
| Viva Preparation PDF | PDF | `docs/pdfs/AWS_VIVA_GUIDE.pdf` | Verified (26 pages) |
| Handover | Markdown | `docs/handover/HANDOVER.md` | Verified (current state, run steps) |
| Technical Documentation | Markdown | `docs/reports/markdown/PROJECT_DOCUMENTATION.md` | Complete consolidated reference |

---

## 3. report_assets Investigation & Status

- **Visibility & Location:** Located at `docs/reports/report_assets/`.
- **Attributes:** Windows file attributes verified: standard directory `d----` (no Hidden or System attributes set).
- **Git Tracking:** Not ignored by `.gitignore`. Verified visible to git status.
- **Subdirectories:** Contains all required figures, diagrams, charts, and masked screenshots:
  - `aws_console/` (13 masked console captures)
  - `aws_evidence/` (2 masked architecture views)
  - `branding/` (institutional logo)
  - `charts/` (7 verified analytical charts)
  - `diagrams/` (9 pairs of SVG/PNG architecture flow diagrams)
  - `live/` (6 verified live deployment screenshots)
  - `screens/` (26 verified application screenshots)
- **Integrity:** All 58 figures referenced in `docs/reports/REPORT_ASSET_INDEX.md` and `PROJECT_REPORT_FINAL.docx` remain intact.

---

## 4. Generator Scripts & Redundant Files Removed

Previous consolidation passes safely eliminated one-off generator clutter, superseded drafts, and obsolete illustration files without impacting project reproducibility:

- **Obsolete Generator Scripts Removed:**
  - `generators/prep_evidence.py` (one-off illustration converter superseded by live evidence)
  - `generators/aws_ill.py` (pre-deployment mock-up generator with "ILLUSTRATION ONLY" banners)
  - `docs/report_assets/presentation/raster_icons.mjs` (unrunnable script whose input `icons.json` was deleted)
- **Redundant Assets & Superseded Drafts Removed:**
  - `docs/report_assets/aws_illustrations/` (10 obsolete HTML + 10 mock PNGs)
  - `docs/report_assets/aws_evidence/` (6 redundant unmasked views duplicated by console captures)
  - 9 unused icon variants from presentation asset drafts
  - 26 fragmented Markdown drafts and competing handovers (`docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DATABASE_DESIGN.md`, `docs/SECURITY.md`, `docs/AWS_COST_REVIEW.md`, `docs/AWS_DEPLOYMENT.md`, `docs/TESTING.md`, `docs/FINAL_HANDOVER.md`, `docs/PROJECT_REPORT.md`, `docs/AWS_VIVA_CHEAT_SHEET.md`, etc.), all consolidated into `PROJECT_DOCUMENTATION.md`, `HANDOVER.md`, and `AWS_VIVA_GUIDE.md`.

---

## 5. Important Files Deliberately Preserved

- **Repeatable Capture Tooling:** `docs/evidence/capture/` (`harness.mjs`, `local.mjs`, `live.mjs`, `aws_views.py`, `make_index.py`, `make_live_results.py`) retained for reproducible test evidence capture and screenshot indexing.
- **Frontend Asset Generators:** `frontend/scripts/generate_icons.py` retained for favicon/app icon generation.
- **Infrastructure Automation:** `infra/prepare_build.py`, `infra/deploy_frontend.py`, `infra/live_test.py`, and `infra/web/handler.py`.
- **Full Test & Capture Evidence:** All genuine captures in `docs/evidence/` (local, live, animation frames, monitoring, and audit logs) preserved.
- **Unmasked Console Originals:** `docs/evidence/manual/aws-console/Screenshot*.png` preserved locally for historical verification (safely excluded from git tracking via `.gitignore`).

---

## 6. References & Link Verification

- Repository entry point `README.md` verified pointing to all canonical documentation and evidence paths.
- Relative links across `docs/reports/markdown/*.md`, `docs/handover/HANDOVER.md`, `docs/viva/AWS_VIVA_GUIDE.md`, and `docs/evidence/SCREENSHOT_INDEX.md` verified valid.
- Zero stale references to deleted drafts or missing files.

---

## 7. Final Validation Results

- **Backend Pytest Suite:** 131 passed out of 131 tests (`pytest -q`).
- **Frontend Vitest Suite:** 20 passed out of 20 unit/component tests (`vitest run`).
- **Frontend Typecheck:** TypeScript compiler check passed (`tsc -b`).
- **Frontend Production Build:** Vite build succeeded (bundle verified, temporary build cache cleaned).
- **Deliverables Check:**
  - DOCX opened and validated (81 parts, valid OpenXML structure).
  - PPTX opened and validated (102 parts, valid OpenXML structure).
  - All PDFs opened and verified (26 pages Viva, 11 pages Presentation, 92 pages Report).
