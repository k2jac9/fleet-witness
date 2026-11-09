# Latest submission implementation plan

> **For agentic workers:** Use superpowers:executing-plans; root implements and an independent reviewer checks the complete branch.

**Goal:** Deliver latest.pdf, a reproducible submission package and a cinematic README.
**Architecture:** Add publication artifacts and a narrow allowlisted public-data exporter; retain the historical report and all runtime contracts.
**Tech stack:** Python standard library, existing Markdown renderer, installed Chromium and Poppler, original local SVG.
**Spec:** ../specs/2026-11-09-latest-submission-design.md

## Global constraints

- At most eight main report pages; abstract 150-250 words; required ethics appendix.
- Exact existing title; Alejandro Castellanos (Independent researcher), Ignatius Pio Binawan (University of Toronto).
- No rewrite of REPORT.*, historical evidence or accepted ADRs; no new paid call or external submission.
- Public export excludes credentials, account details, private paths, transport profiles and opaque response metadata.
- Preserve failed receipts and source-bound verification. Use unchanged 2 GiB storage admission.
- Existing baseline is the just-qualified ee7c17e tree: 304 Python tests, five viewer checks, all runtime lanes. Final checks run on this branch after publication changes.

## Owned files

README.md; docs/SUBMISSION.md; docs/AI_ASSISTANCE.md; docs/BUILD_STATUS.md;
docs/assets/fleet-witness-hero.svg; docs/assets/fleet-witness-mission.svg;
docs/assets/fleet-witness-results.svg; docs/report/latest.md;
docs/report/latest.html; docs/report/latest.pdf; docs/report/latest.references.json;
docs/report/latest.provenance.json; docs/report/latest-figures/paired-pilot.svg;
docs/submission/latest/**; docs/submission/latest-submission.zip;
data/paired-pilot-2026-11-09.json; scripts/export_public_pilot.py;
scripts/build_latest_submission.py; tests/test_public_pilot_export.py;
this plan and its spec. Task receipts only in the sibling latest-submission-20261109 artifact directory.

## Review focus

- A nested unexpected credential or transport field must not leak through the public exporter.
- Historical logical responses and new provider attempts must remain separate in every artifact.
- Paper main-page boundaries, abstract, figure labels and affiliation details must remain correct in the final PDF.
- Archive checksums, links and metadata must refer to the packaged files, with no symlinks or private material.
- GitHub's constrained rendering must keep core claims and launch instructions accessible without images.

### Task 1: Publication evidence and report

- [x] Verify primary reference metadata and narrow unsupported novelty claims.
- [x] Add failing export regressions for unknown nested sensitive fields and mismatched/incomplete evidence; implement explicit allowlists.
- [x] Write latest.md with separate historical and new-pilot evidence; preserve old report hashes.
- [x] Render and inspect all PDF pages after storage admission; enforce page and abstract limits.

### Task 2: README and submission package

- [x] Write original static SVG artwork and semantic README links, claims, setup and limitations.
- [x] Build the package from an explicit member list, with portable evidence, metadata and checksums.
- [x] Align current submission/author notes and add an observed build-status entry.
- [x] Inspect README preview at desktop and narrow widths; verify local links and SVG safety.

### Task 3: Verify and integrate

- [x] Run full Python/viewer suites and publication checks; retain commands/results and failures.
- [x] Independent whole-branch evidence/code/visual review; root fixes material findings with behavioral regressions where applicable.
- [ ] Run exact-source hosted CI, retain identities, merge green PR and fast-forward clean main.
- [ ] Deliver latest.pdf, ZIP and current README links with explicit remaining submission steps.

## Execution ledger

- Ruling: publish only trial scalars and aggregate outcomes; omit free-text prompts, reasons and provider envelopes. This reduces accidental private-data exposure; the public table supports recomputation, not full private trace replay.
- Ruling: reuse the existing Markdown renderer and installed Chromium rather than install a new PDF dependency. Preserve a standalone editable Markdown/HTML/figure set.
- Ruling: retain the existing title and author order; use the owner-confirmed Independent researcher affiliation. Historical manuscripts remain byte-identical.
- Ruling: link the historical reproduction receipt rather than package its workstation path. Keep the original receipt unchanged in the repository.
- Evidence: public-export module missing (RED), canonical receipt fixture corrected, export tests GREEN; package module missing (RED), symlink/traversal checks GREEN; existing historical receipt path disclosure (RED), linked receipt plus package input regression GREEN.
- Local verification: 308 Python tests; five viewer checks; all eight PDF pages visually reviewed; six main pages; 218-word abstract; 14 package members verified and extracted aggregate commands executed. Full receipts are in the sibling latest-submission-20261109 artifact directory.
- Pending: fresh whole-branch review and exact-source hosted CI/integration. No paid calls or external form submission belong to this publication task.

- Final: fixed recognized-field nested-object leak — `test_recognized_scalar_fields_cannot_carry_nested_private_values` RED (11 failures) to GREEN; strict scalar formats reject containers, booleans as counts, negatives and noninteger counts. Full suite 309/309, viewer 5/5. Real trial rows and summaries unchanged.
- Final: fixed both minor findings — GitHub emoji heading anchor; HMAC observability caveat restored in the report and public dataset. PDF/HTML/ZIP regenerated, all eight pages visually rechecked and package arithmetic/checksums passed.
- Final: Ruling: accept the review's declined areas as separate acceptance boundaries — paid execution/billing authentication, historical depth-six rerun, current cloud state, event-form acceptance, independent reproduction of cited research, hosted GitHub visual acceptance and new runtime upgrades are outside this publication task. Exact-source hosted CI remains required for the branch.
