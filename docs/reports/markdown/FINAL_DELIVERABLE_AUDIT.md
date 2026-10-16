# FinSight — Final Deliverable Audit (2026-10-16)

This short audit was made before the final consolidation. It records what was authoritative, what was outdated and what was
done about it. The details of each change are in [WORKSPACE_CLEANUP_REPORT.md](WORKSPACE_CLEANUP_REPORT.md).

## Sources of truth (verified)

| Area | Source | Check |
|---|---|---|
| Deployment | live stack `finance-intelligence-prod` (read-only CLI) | `UPDATE_COMPLETE`, last update 2026-10-16 09:49 UTC, `FrontendHosting=apigateway`. Live URL: `/` 200, `/api/v1/health` ok (DynamoDB), private route 401 |
| CloudFront | stack outputs, template | **not deployed**; still blocked by account verification |
| Tests | runs on 2026-10-16 | backend 131, frontend 20, typecheck, build and cfn-lint pass; live 64/64 and 27/27 (`docs/evidence/09_testing/`) |
| Screenshots | `docs/evidence/` (genuine captures, indexed); owner's Console captures in `docs/evidence/manual/aws-console/` | the Console captures were **not masked** (account ID in the address bar, account menu and ARNs), so masked copies were made for the report and deck |
| Diagrams | `docs/report_assets/diagrams/` | the AWS architecture, deployment, auth-sequence, system and workflow diagrams already show the deployed design |

## Findings before consolidation

| Finding | Action |
|---|---|
| 26 Markdown files with three competing handovers (`HANDOVER`, `FINAL_HANDOVER`, `FINAL_IMPLEMENTATION_AUDIT`) and overlapping architecture, deployment, security, cost and testing documents | consolidated into README, `PROJECT_DOCUMENTATION.md`, `HANDOVER.md`, `AWS_VIVA_GUIDE.md` and the validation files |
| `ARCHITECTURE.md`, `PROJECT_REPORT.md`, `AWS_DEPLOYMENT.md` and the README still described S3 + CloudFront hosting or “not deployed” | corrected during the migration |
| Two separate viva documents (cheat sheet + 150 Q&As) | merged into one guide without losing content |
| Report at 100 pages with duplicate AWS evidence (rendered views and Console screenshots of the same resources) and diagrams queued to chapter ends | duplicates removed, diagrams inlined, spill pages fixed (92 pages) |
| 9-slide deck with 10–13 pt body text and no Margie's Travel layout | rebuilt: 11 slides on the Margie's Travel layout in FinSight colours |
| Superseded AWS illustrations and an unrunnable icon script still in `report_assets` | removed |
| Evidence index script would have labelled the unmasked Console originals as “masked by owner” | corrected; the originals are git-ignored |

## Deliverables (final)

[README.md](../../../README.md) · [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) · [HANDOVER.md](../../handover/HANDOVER.md) ·
[AWS_VIVA_GUIDE.md](../../viva/AWS_VIVA_GUIDE.md) · `PROJECT_REPORT_FINAL.docx/.pdf` · `PROJECT_PRESENTATION_FINAL.pptx/.pdf` ·
[FINAL_VALIDATION.md](FINAL_VALIDATION.md)
