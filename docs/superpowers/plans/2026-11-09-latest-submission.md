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

- [ ] Verify primary reference metadata and narrow unsupported novelty claims.
- [ ] Add failing export regressions for unknown nested sensitive fields and mismatched/incomplete evidence; implement explicit allowlists.
- [ ] Write latest.md with separate historical and new-pilot evidence; preserve old report hashes.
- [ ] Render and inspect all PDF pages after storage admission; enforce page and abstract limits.

### Task 2: README and submission package

- [ ] Write original static SVG artwork and semantic README links, claims, setup and limitations.
- [ ] Build the package from an explicit member list, with portable evidence, metadata and checksums.
- [ ] Align current submission/author notes and add an observed build-status entry.
- [ ] Inspect README preview at desktop and narrow widths; verify local links and SVG safety.

### Task 3: Verify and integrate

- [ ] Run full Python/viewer suites and publication checks; retain commands/results and failures.
- [ ] Independent whole-branch evidence/code/visual review; root fixes material findings with behavioral regressions where applicable.
- [ ] Run exact-source hosted CI, retain identities, merge green PR and fast-forward clean main.
- [ ] Deliver latest.pdf, ZIP and current README links with explicit remaining submission steps.
