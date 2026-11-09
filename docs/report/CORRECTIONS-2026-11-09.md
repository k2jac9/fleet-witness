# Report correction and provenance: 2026-11-09

Task 3 publication portion of the approved swarm stabilization plan. This is an
offline correction of retained evidence, not a new live-model experiment, a
submission or human peer acceptance. It supersedes the current presentation
artifacts; it does not rewrite historical observations, reviews or accepted ADRs.

## Preserved originals

The original report, figures, scripts and archive are recoverable from commit
`6061cb20f39ac19fcc95b09303e02ebcd43a9887`. Their SHA-256 identities were verified
against that Git revision before correction. The exact original and corrected
identities are in [ARTIFACT_PROVENANCE-2026-11-09.json](ARTIFACT_PROVENANCE-2026-11-09.json).
The original archive remains byte-for-byte unchanged:

`c55e8acf07ed8dd3c11bc3dc8f70269adebaac6bfa14727642cca7314d1f821a`

`docs/report/reviews/**` and `docs/report/review-data.md` are preserved verbatim.
The latter is a historical review input, not a current statistical specification.
Its pooled binomial confidence intervals do not account for paired committee
seating. Its gpt-oss honest-auditor token denominator of 746 should be 745
answered responses; the main safety denominator of 746 is correct.

## Corrected content

- Repaired literal encoding corruption, including the capture equation, ranges
  and multiplication signs, in Markdown and regenerated HTML/PDF.
- Replaced the causal Figure 2 title with "Colluding agents produced longer
  outputs"; the longer, conflicting colluder prompt remains a stated confound.
- Used conventional medians, averaging the middle two values for even sample
  sizes. DeepSeek audit medians change from 111/241 to 110.5/240.5 (honest/colluding).
  The gpt-oss colluder-auditor median changes from 329 to 327.5; its honest median
  remains 174. Raw recomputation confirms answered-only audit counts of 746/262
  and 745/262, respectively. GPT vote counts are 5,398/1,798 answered responses.
- Distinguished 32,830 completed main logical records from 32,832 scheduled
  response slots and from unknown provider-attempt totals. The eight regimes
  reuse those records. Nominal 7-versus-50 standalone request counts are not
  measured token, dollar or latency savings; only hidden-board audits could
  omit voting while preserving their information set.
- Added the retained recorded costs: main $2.182374; all archived runs $5.828262
  over 84,813 completed logical records; reviews/speed test bring the known
  recorded sum to $10.858262. These are not reconciled provider bills. Missing
  attempts, failed-record costs, unretained pilots and development assistance
  remain explicit limitations.
- Distinguished the historical gated-majority counterfactual, computed from
  `majority_approve and kind != "forged"`, from the corrected baseline that
  executes the institution kernel using fresh synthetic receipts and keys plus
  retained votes. Historical keys and receipt identities were not retained;
  this cannot authenticate historical signatures. The reconstructed control
  agrees with the original counts: 0/120 targets, 0/48 forged releases, 96/96
  valid releases for each model.
- Clarified zero-collusion near-miss percentages, the separate 30% exceptions,
  offline splicing for mixed-model committees, small herding exposure counts,
  absent historical source/runtime/request provenance and incomplete retry
  metadata. The report retains the existing bounded-verification, paired-design,
  synthetic-task, semantic-error and detector-generalization limitations.
- Recorded AI review status accurately. Round 2's four weak accepts are model
  outputs; review manifests do not bind manuscript or data hashes. They do not
  constitute human peer acceptance or certify this corrected revision. Literature
  and novelty comparisons still require source verification before submission.

## Reproduction and verification

The publication branch starts at
`8f0f627619ce819524f6644a197ccb43cd291b9f`; the containing commit identifies its
final source. Per-file hashes bind the rendered inputs without claiming that
historical provider requests used this source. Python 3.15.0, Node 26.11.1,
Chrome 155.0.8059.39 and Poppler 26.06.0 were the local tools used. This is not a
runtime upgrade qualification or evidence that a full runtime matrix ran.

The retained task packet is
`/home/neo/Projects/fleet-witness-artifacts/stabilization-20261109/report/`.
It includes preflight/admission records for a 1 GiB growth budget, original
hashes, a failed initial extraction (Windows directory markers), corrected
extraction and hashes, median red/green logs, raw recomputed medians, complete
test logs, rendering commands, all PDF page images and artifact checks.

Executed publication checks:

- `python -m unittest discover -s tests -p test_report_figures.py -v`: the old
  even-sample calculation failed (329 instead of 327.5), then passed after the
  fix. The same real fixture covers odd samples and unanswered/non-target
  exclusions.
- `python -m unittest discover -s tests -v`: 169 tests passed on this publication
  branch, including the new regression.
- `node --test tests/viewer.test.mjs`: 5 tests passed.
- `git diff --check`: passed.
- Recomputed both SVGs from extracted main sweeps and regenerated both PNGs.
  Generated HTML equals the committed Markdown renderer's output. Chrome used
  a fresh isolated profile, disabled background networking, a blackhole proxy
  and disabled DNS resolution, loading only local report/figure files.
- Rendered the 17-page PDF with Poppler. Inspected all pages in contact sheets
  and the equation, main table, verification table and token figure at larger
  size. No clipped text, broken glyphs or overlapping elements were observed.
  Extracted text includes the corrected statistics and accounting boundaries.

The reproduction worker separately executed all main/near-miss analysis with
`--skip-checker`, retained input hashes and an `inputs_unchanged: true` result
at `../reproduction/derived/` relative to the task packet. Its baselines and
provenance hashes are recorded in the JSON companion. Those worker receipts
bind the worker's then-current file hashes and base commit, not an integrated
final commit. Final candidate reproduction and independent review belong to
the parent integration record in `docs/BUILD_STATUS.md`.

The portable reproduction interface after integration is:

```sh
python scripts/extract_run_archive.py --archive data/fleet-witness-runs-2026-11-08.zip --destination FRESH_INPUT
python scripts/reproduce_tables.py --input-root FRESH_INPUT/runs --output-root FRESH_DERIVED --skip-checker
python scripts/make_figures.py docs/report/figures FRESH_INPUT/runs/sweep-deepseek2k=DeepSeek FRESH_INPUT/runs/sweep-gptoss=gpt-oss
python scripts/report_to_pdf.py docs/report/REPORT.md
```

Use fresh, admitted artifact directories for the placeholders. Omitting
`--skip-checker` executes the bounded checker separately. This publication task
read the historical depth-six checker evidence and did not rerun that expensive
check. It made no model calls, credential reads, external requests, cloud changes,
pushes or merges. Historical raw archive/reviews remain unchanged. Current
`independence.json` and final integration evidence are parent-owned outputs.
