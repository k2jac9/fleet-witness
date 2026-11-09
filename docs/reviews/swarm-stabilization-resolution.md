# Swarm stabilization: integrator resolution

Task: `swarm-stabilization-20261109`. Independent review:
[original review](swarm-stabilization-review.md), exact head
`8c0c790515db16f1af8468c4978070a505709b82`. The original verdict was **not ready**;
it is retained verbatim. The integrator fixed the four findings in
`519c3aacfc4cd32b10dafb598915ac11930da5f8` and verified them with retained failing
regressions followed by passing tests. This resolution is the integrator's
acceptance evidence, not a second independent review of that commit.

## Findings and verification

| Finding | Resolution | Observed verification |
| --- | --- | --- |
| R1, Important: model records multiply the shared request count | Bind count, expiry, source and purpose to an immutable run authority; count all run reservations transactionally | Second model after restart is denied at shared limit; replacement record cannot raise limit; both red then green |
| R2, Important: Git-free worker fixtures fail | Supply a synthetic commit only within offline test fixtures; preserve production rejection of absent/mismatched source | Initial source-only provider probe failed; fixed full Git-free launcher passed 233 Python tests, five viewer tests and scripted demo, `stage=complete`, exit 0 |
| R3, Important: swapped model datasets receive wrong labels | Validate exact recorded model, configuration and seed schedule before output; include actual model IDs and all eight dataset identities in output provenance | Wrong-model/configuration tests red then green; reviewer's swapped real-archive copy now rejected before output |
| R4, reviewer Minor, integrator Important: unsent reservations counted as requests | Retain each safe dispatch count; summarize dispatched requests separately from reservations | Pre-dispatch persistence failure reproducer red then green; zero transport/ledger/summary attempts, retained reservation and liability |

The fix-pass full standard-library suite passed 233 tests. Full offline
reproduction on the clean fixed commit preserved all 147 input files and passed
the depth-six checker in both configurations with all seven mutants caught.
Eighteen derived JSON files parse strictly. The original archive, accepted ADRs,
historical reviews and review input are unchanged. A bounded pattern scan of
44 changed files found no potential secret matches; that is not proof of absence
of every possible secret. See [final reproduction receipt](../report/REPRODUCTION-REVIEW-FIX-2026-11-09.json).

Two hosted Python lanes repeatedly failed while downloading exact runtime
artifacts with upstream HTTP 504, before tests. The narrow CI fix uses a fresh
request query and bounded retries, then the official GitHub release API through
`gh release download` for the same Python tag/file if necessary. The download
step alone receives the existing read-only workflow token. All pinned versions,
digests and required checks remain unchanged. A local API-route download of the
exact 3.13.17 archive passed the existing digest verifier. GitHub documents this
[release-asset API](https://docs.github.com/en/rest/releases/assets); no runtime
identity is selected by the fallback. Exact final-source hosted results remain a merge gate and are
recorded in the integration PR. No runtime was substituted or acceptance waived.

The Git-free launcher check is not a Nix derivation build, boot, cloud-isolation
check or live-provider qualification. Inherited unclosed-SQLite warnings remain
in full logs. No paid inference, credential access or cloud mutation occurred
in this stabilization.

## Integrator rulings

- **Existing authorization and preservation:** the owner approved this plan and
  integration; no repeated approval is needed. All branches, worktrees, original
  receipts and failed probes remain preserved. Cost if wrong: confusing a retained
  checkpoint with permission for a new live operation; live gates remain explicit.
- **Task ownership:** the parent also owned operator/private-receipt helpers,
  judge accounting and narrow integration-test updates, because every paid
  entrypoint needs the same controls. Cost if wrong: an omitted entrypoint could
  evade accounting; the tests exercise swarm, judge and review paths.
- **Sequential paid execution:** the accepted envelope permits one in-flight
  request. Paid runner work is sequential; fake work can remain concurrent.
  Cost: reduced throughput, without expanding paid authority.
- **R4 severity:** counting an unsent reservation as a request undermines the
  required failure-accounting evidence, so it was fixed as Important. Cost:
  additional regression/verification work rather than deferred incorrect counts.
- **CI downloads:** bounded retries and the verified same-asset official API
  fallback address download failures while mandatory hash verification stays intact. Cost if ineffective:
  CI fails visibly and integration remains blocked; no substitute artifact.

## Disposition of every declined-to-judge item

- **Live provider facts and qualification:** remain unverified acceptance gates.
  No operator record is issued here. Treating local fixtures as qualification
  would risk unauthorized or unreconciled spending and data disclosure.
- **Unavailable historical signatures/prompts/attempts/bills:** preserve the raw
  record and label reconstruction honestly. Missing records cannot be recovered
  by assertion; inferring them would overstate evidence and cost completeness.
- **Cloud/dashboard/host state:** not reverified or changed by this local task.
  Their dated receipts do not establish present health, expiry or isolation.
- **Hostile same-UID/compromised operator:** outside the declared trusted-host
  boundary. Worktrees and private file modes are not process isolation; treating
  them as such would expose credentials and permit accounting tampering.
- **Reconciliation/migration tooling:** still absent. Legacy JSON and unresolved
  holds stop live work. A fresh ledger must not be used to evade those liabilities.
- **Literature/novelty/authorship timing:** no new independent claim is made.
  Source verification and human publication acceptance remain open; ignoring
  them could misstate research provenance or submission readiness.
- **PDF visual review:** accept the publication worker's retained inspection of
  all 17 rendered pages and bound hashes. The code reviewer did not repeat it;
  a missed visual defect would affect presentation, not raw observations.
- **Inherited heuristic vote/sign parsers:** retained to preserve the historical
  experimental treatment. They are not the closed-schema supervisor interface
  required by ADR-0010. Before new paid qualification, explicitly scope and
  validate the intended treatment and parser; accepting them implicitly would
  conflate different studies and admission rules.

No review minor is silently deferred: R4 was escalated and fixed. The explicit
operational gates and historical-evidence limits above remain open.

Evidence packet:
`/home/neo/Projects/fleet-witness-artifacts/stabilization-20261109/`.
