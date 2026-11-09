# Repository editorial pass

Task: `editorial-polish-20261109`. Owner/integrator: Alejandro Castellanos,
assisted by Codex. Base: `3d25f44482280766fdff305d470773dc30023f93`.
Branch: `docs/editorial-polish-20261109`; isolated worktree of the same task name.

## Outcome and scope

Make maintained documentation consistent with the completed OpenRouter pilot and
latest publication. Preserve the cinematic README, exact manuscript title and
author order, research denominators, unfavorable outcomes and security boundaries.
Give readers one documentation map, portable examples and explicit distinctions
between current instructions, dated evidence and unresolved acceptance.

Owned paths: `README.md`, `CONTRIBUTING.md`, `data/README.md`, `fleet/README.md`,
the maintained top-level Markdown guides in `docs/`, `docs/adr/README.md`,
`docs/report/latest.md`, `docs/report/latest.html`, `docs/report/latest.pdf`,
`docs/report/latest.provenance.json`, `docs/submission/latest/`,
`docs/submission/latest-submission.zip`, and this plan.
Historical content in `BUILD_STATUS.md` is append-only. The old scripted report
and scenario task record may receive a context banner; their bodies stay intact.
Accepted ADRs, prior plans/reviews, experiment records, datasets, `REPORT.*`,
runtime code, tests, infrastructure and runtime pins are outside scope.

## Work and verification

1. Audit maintained guides against committed experiment/publication evidence;
   replace stale status claims, normalize terminology and repair navigation.
2. Copyedit the latest report without changing findings. Regenerate its HTML,
   PDF and explicit-allowlist ZIP; preserve prior publication identity in
   provenance. Inspect every PDF page and verify hashes, page limits and abstract.
3. Check local links/anchors, preservation hashes and whitespace. Exercise
   the offline demo and fleet commands; run the full Python and Node suites.
   Documentation-only edits do not need tests that mirror prose.
4. Obtain one fresh independent whole-branch review, resolve findings, run the
   existing hosted runtime matrix on the final tree, then integrate green work.
   Keep exact source identities, commands, failures and limitations in receipts.

## Rulings and boundaries

- The native worktree tool cannot choose an output path. Use Git to keep this
  worktree inside the project, as required by workstation path policy.
- Use the sibling artifact directory and admitted 2 GiB budget for retained
  logs and rendering. Do not place durable evidence under temporary directories.
- A dated public source is not a fresh price/account/service check. This pass
  changes no budgets, credentials, cloud resources, experiments or event entry.
- Use existing publication tooling and installed runtimes; no dependency or
  runtime upgrade is needed for editorial work.

## Execution ledger

- Worktree created at the base above; initial storage preflight allowed the
  declared workload. Initial audit found stale pre-calibration status in the
  gates, roadmap, architecture, worker and provider guides.
- Implementation and acceptance receipts follow in `BUILD_STATUS.md`; the
  final commit and hosted CI identity are recorded after execution.

- Tasks 1–3 complete: maintained guides reconciled; report and package regenerated;
  all pages inspected; 309 Python and five viewer tests passed. Local link audit,
  demo metrics, planner, package checks and preservation checks passed.
- Ruling: retain the execution ledger and renders in the admitted sibling artifact
  packet rather than deleting skill scratch — owner preservation policy applies;
  the cost is retained storage within the declared budget.
- Ruling: continue the already authorized green-merge workflow without another
  approval menu — prior owner authorization persists; exact-head review and CI
  remain required. No paid execution or event submission is included.
- Independent review of `2a3b32aff0235038fc40a115774d3248ad146eac` found no
  blocking issue. Its one minor receipt-fixture wording finding is corrected.
  The user's full editorial-polish request includes this small clarification;
  no prose-matching unit test or second review is needed. Final-tree CI and
  integration remain tracked in PR #14 and the retained task packet.
