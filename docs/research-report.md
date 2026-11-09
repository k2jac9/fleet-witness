# Fleet Witness: separating authentic evidence from action authority

> **Historical scripted-study draft, 8 November 2026.** The body below is preserved
> as written. Use the [latest report](report/latest.md) and [PDF](report/latest.pdf)
> for current authorship, live-model findings and submission material.

Human team: Alejandro Castellanos (`k2jac9`) and `IPBin`. IPBin's preferred
publication name, both affiliations, contributions and the final author list/order
are to be confirmed by the team before submission. Draft dated 2026-11-08; no
event submission has been made. This report describes a scripted mechanism study.

## Abstract

Multi-agent oversight must distinguish a credible-looking recommendation from
an authorized action. Fleet Witness is a runnable testbed that separates three
questions: whether evidence is authentic, whether it applies to the proposed
release, and whether current policy permits execution. A deterministic supervisor
receives paired presentations of identical evidence, while a trusted controller
checks receipt integrity and applicability and commits each authorized local
effect together with its audit event in one SQLite transaction. An independent
evaluator records decision-time correctness separately from execution-time
authorization and observed effects. Across 32 scripted runs containing 640
trials, the retained traces contain 224 incorrect recommendations, 480 execution
attempts, 288 authorization denials, and 128 authorized local effects. Verification
found no unsafe or duplicate effects in these traces. Repeated seeds change
synthetic identities rather than supervisor policy, so these counts are software
verification results, not independent model observations or estimates of real-world
safety. The implementation includes replay inspection, offline worker execution,
and an authenticated read-only hosted dashboard. Fake-provider accounting tests
exercise shared reservations and failure handling, but live-provider calibration
and a confirmatory model comparison have not run. The contribution is an
inspectable separation of evidence, recommendation, authorization, and effect,
with explicit boundaries for later empirical evaluation.

## Question and contribution

Can a release controller preserve its authorization boundary when a supervisor
approves authentic but insufficient evidence, evidence with the wrong scope,
or a request whose permission changes after approval? Fleet Witness provides
executable examples and failure-oriented tests for this question. It makes no
claim to invent transactional control, authenticated attestations, or the
separation of recommendation and authorization. Its practical contribution is
putting those distinctions into independently inspectable paired traces.

The study concerns a local release represented by a database row. It does not
perform a package publication, contact an external fleet, or observe a live
swarm. The worker, reviewer, and supervisor in these traces are deterministic
policies. The AI tools used to develop and review the project are a separate
system and are not experimental subjects.

## Method

The trusted controller creates synthetic signed receipts and retains issuer
keys outside supervisor-visible input. A receipt's integrity is separate from
its exact issuer, claim, scope, artifact, and run applicability. A genuine build
receipt cannot establish a release-safety claim. The controller rechecks current
policy inside the transaction that commits a release and corresponding audit
event. A uniqueness constraint limits each run/artifact to one release in its
isolated trial. These transactions use SQLite's documented atomic-commit
mechanism [1]; this project has not independently qualified hardware power-loss
behavior.

Each seed produces 20 trials. Paired `raw` and `scope_explicit` presentations
share equal visible facts and signed evidence but have separate mutable trial
state. Only presentation instructions differ. The evaluator records
`decision_valid_at_snapshot`, `execution_authorized_at_attempt`, and
`effect_occurred` separately. A valid recommendation followed by revocation
remains valid at its snapshot while execution is denied. An invalid approval
remains invalid when the controller prevents its effect. An authorized repeated
execution is a no-op, not an additional effect or authorization denial.

Scenarios include honest/adversarial worker and reviewer combinations, genuine
but insufficient receipts, forged receipts, wrong artifact/run applicability,
missing policy, revocation, and duplicate execution. Additional regression tests
cover issuer, claim and scope mismatch, irrelevant neighboring receipts and
paired-state independence. The scenario inventory is in `docs/scenarios.md`.

The 32-seed campaign is a bounded regression campaign. Its verifier recomputes
summary counts from episodes, checks paired visible facts and committed receipt
equality, and rejects unsafe or duplicate effects. The retained campaign was
reverified during this continuation; no fresh model calls were involved.

## Results and denominators

| Quantity | Observed count | Meaning |
| --- | ---: | --- |
| Scripted runs | 32 | Seeds 0 through 31 |
| Trials | 640 | 20 trials per seed |
| Incorrect recommendations | 224 / 640 | 35% of scripted recommendations; not a model error estimate |
| Execution attempts | 480 | Includes authorized duplicate no-ops |
| Authorization denials | 288 / 480 | 60% of recorded attempts |
| Committed local effects | 128 | All authorized under the tested conditions |
| Unsafe effects | 0 | None found by the campaign verifier |
| Duplicate effects | 0 | No trial committed a second release |

No confidence interval or significance claim is assigned to these repeated
scripted seeds. They vary identities while repeating the same policy mechanisms.
In particular, the paired presentation difference is illustrative; it cannot
establish that a prompt improves a real model. Observing zero unsafe effects
here does not bound the failure probability of other workloads or deployments.

At the CI change `7a3db75`, 149 Python tests passed locally and on seven exact
hosted Python lanes; five viewer tests passed on four exact Node lanes. Stable,
upcoming, previous-supported and additional consumer/baseline selections and
artifact digests are recorded in `ci/runtime-matrix.json`. Actual run:
https://github.com/k2jac9/fleet-witness/actions/runs/42515494887 . Later changes
must use their own source-bound test evidence.

Earlier cloud evidence records successful execution of all four offline NixOS
workers and bounded identity, network-denial, resource-limit and timeout probes.
Some pressure diagnostics intentionally failed and other acceptance cases remain
open. Those observations do not establish full isolation of hostile processes.
The cloud VM is stopped. A separate authenticated Cloud Run service serves only
synthetic static replay assets; deployment evidence and its expiry are in
`docs/BUILD_STATUS.md`.

## Reproduction and source identity

The scripted campaign implementation is already present at
`39ba6cc35987541d673c25402bb2bf34759cb0ad`; the dashboard verification record is
at `63431b112c9150e178a58ee31833ea6111e6a5d4`. From a reviewed checkout:

```sh
python3 -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
python3 scripts/fleet.py validate
python3 -m fleet_witness.campaign --output /absolute/new/evidence-directory
```

Choose an absent output directory and retain the result. Scenario outcomes are
reproducible, but fresh signatures and timestamps prevent byte-identical replays.
Signing keys are intentionally not persisted; saved databases are historical
inspection artifacts, not resumable sessions. The retained original campaign
lives in the owner's project artifact directory, separate from the public Git
repository. Source-bound receipts remain there; private ledgers, credentials,
browser profiles and raw TLS session transcripts are not publication assets.

## Next empirical study

The reviewed proposal specifies a possible two-model, eight-family comparison
with 10 repetitions and two presentations: 320 requests across 160 pairs.
That is a proposed study, not an executed result. Calibration must first verify
provider access, billable units, reasoning bounds, worst-case costs, failure
accounting, TLS/egress, retention and the production authorization boundary.
Model, prompt, order, analysis and budget identities must be frozen after
calibration and before confirmatory collection. Failed, incomplete and unstarted
calls remain in their respective denominators. No such cohort has started.

## Prior work and provenance

SQLite supplies the transactional database implementation [1]. Python, Node,
NixOS, Caddy and Google Cloud supply general-purpose runtime and hosting
infrastructure. The repository's ADRs distinguish these dependencies from the
project's own evidence/controller mechanism. The project was initialized during
the sprint on 2026-11-08; earlier conceptual planning is disclosed in
`docs/AI_ASSISTANCE.md`. No source from that earlier planning repository or the
VPS reference project was copied into the implemented runtime. This report does
not claim an exhaustive literature review or novelty over all agent-oversight
systems. That review remains work before a broader research publication.

## Limitations and Dual-Use / Ethical Considerations

The evaluator uses synthetic truth and HMAC keys trusted within one process;
there is no independent notarization or public-key trust system. The controller
and evaluator could share mistakes, and tested failure cases do not exhaust the
input space. SQLite transaction tests do not demonstrate power-loss recovery on
every storage stack. Containers share a kernel. The hosted dashboard is static
and does not demonstrate autonomous coding or live-model oversight.

A shared accounting database cannot constrain an owner-level attacker or an
undocumented provider charge. Timeouts can leave billable work unresolved.
Provider terms and account-specific accounting remain gating facts, not flags
that an implementation may invent. Existing cloud storage can accrue charges
while compute is stopped. Costs, retention, runtime adoption, recovery and
remaining host acceptance must be resolved before wider activation.

The testbed can help operators identify authorization confusion, but trace and
orchestration tooling could also make coordinated agent operations easier.
Examples therefore stay synthetic and owner-controlled. No third-party target
was scanned, no actor was attributed, and no public attack sensor was deployed.
A later observation system needs its own authorized targets, privacy/retention
rules, abuse containment and review.

AI development tools assisted architecture, implementation, tests, documentation
and independent code review. They are not additional human entrants. The human
team remains responsible for claims, contribution attribution, affiliations and
the final submission.
This Markdown draft still needs the official report template, PDF/layout checks
and team review; it is not a submitted or accepted paper [2].

## References

1. SQLite, *Atomic Commit In SQLite*. https://sqlite.org/atomiccommit.html
2. Apart Research, *Swarm Alignment Hackathon: Guidelines*, checked 2026-11-08.
   https://apartresearch.com/sprints/swarm-alignment-2026#guidelines
