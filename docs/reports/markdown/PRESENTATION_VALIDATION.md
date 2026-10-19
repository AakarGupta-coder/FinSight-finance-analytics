# FinSight Presentation — Validation

Final state, 2026-10-16. Files: `docs/PROJECT_PRESENTATION_FINAL.pptx` (about 1.8 MB) and `docs/PROJECT_PRESENTATION_FINAL.pdf`
(about 1.5 MB, exported by Microsoft PowerPoint). Source: `docs/report_assets/presentation/build_presentation.js`
(pptxgenjs), exported with `export_presentation.py`.

## 1. Structure (11 slides, 16:9 widescreen)

| # | Slide | Main visual |
|---|---|---|
| 1 | FinSight — title, full title, author, institution, live URL | live dashboard screenshot bleeding off the edge, overlapping title panel |
| 2 | Problem and motivation | four icon rows; live landing page bleeding off the right edge; overlapping motivation card |
| 3 | Objectives and key features | 4 × 2 feature grid with icons |
| 4 | Application overview | live light-theme dashboard with the mobile navigation overlaid |
| 5 | Actual system architecture | native, editable diagram of the deployed stack; CloudFront shown dashed as *planned, not deployed* |
| 6 | Core modules and workflow | six-step journey, three backend layers, module pills |
| 7 | Analytics and intelligence | live insights screenshot; insight, anomaly and projection rules |
| 8 | Receipt OCR workflow | five numbered steps; live receipt review; three result figures from live test RCT-06 |
| 9 | AWS deployment and security | deployment facts, four security controls, two masked AWS Console screenshots |
| 10 | Testing, evaluation and cost | four headline results, native bar chart of live checks by area, cost card |
| 11 | Conclusion and future work | contributions, limitations, future work, live URL |

There is no empty Q&A or thank-you slide; the last slide carries the conclusions, limitations and future work.

## 2. Design (Margie's Travel reference)

- **Reference used:** the Microsoft *Travel presentation* template (Margie's Travel), found at
  `%APPDATA%\Microsoft\Templates\Travel presentation.potx` and rendered slide by slide for study.
- **Principles applied:**
  - a thin left brand rail with vertical lettering and a logo mark;
  - heavy uppercase titles with letter-spaced subtitles;
  - screenshots that bleed off a slide edge, with a content card overlapping them;
  - square “+” markers for comparison blocks;
  - consistent margins and a dark/light rhythm.
- **Not copied:** none of its travel photographs, text, branding, contact details or colour palette (checked: no
  “Margie”/“travel” text in the deck).
- **FinSight identity:**
  - near-black `101114` and charcoal `16191F`, emerald `10B981` / `047857` / `34D399`, white and light grey `F3F5F4`;
  - icons in charcoal circles as the repeated motif;
  - Arial Black titles and Calibri body text.

## 3. Checks

| Check | Result |
|---|---|
| Slide count | **11** |
| `validate.py` (pptx skill: schema, relationships, content types, charts) | **All validations passed** |
| Opens in Microsoft PowerPoint; PDF export | yes (PowerPoint COM); 11-page PDF |
| Editable | native text boxes, shapes, a native chart and a native diagram (296 shapes, 32 pictures); slide layouts with title/subtitle placeholders; theme colours written into the theme; speaker notes on all 11 slides; sections Introduction / Problem and objectives / Design and implementation / Cloud deployment / Results |
| Text size | body and list text 14–19 pt (mostly 15–16 pt); headline figures 26–54 pt; only labels, subtitles, sub-labels and captions are 10.5–13 pt |
| Overflow, clipping, overlaps | every slide rendered by PowerPoint at 1600 × 900 and inspected. Fixed during QA: a negative-width connector (made the file unopenable), a title running into an image, a subtitle under a screenshot, an overlapping planned-CloudFront box, a wrapping tagline |
| Placeholder text (lorem, TODO, “click to”) | none |
| Account IDs / secrets | no 12-digit IDs in slide text; the Console images are the masked copies |
| Accuracy | deployed services only; CloudFront marked planned; results 64/64, 27/27, 131, 20 and the cost figures match `AWS_LIVE_TEST_RESULTS.md` and the billing evidence |

## 4. Known limitations

- Screenshots are raster images, so very small UI text in them cannot be edited (by design: they are evidence).
- Arial Black and Calibri ship with Microsoft Office. On systems without them PowerPoint substitutes fonts and line breaks may shift.
