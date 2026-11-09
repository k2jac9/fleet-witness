# Controlled exploratory paired pilot

The opt-in pilot collects **160 supervisor calls / 80 paired trajectories** from
one qualified OpenRouter model (`openai/gpt-6.1-sol`, Azure `azure/us`). Eight
families have ten pairs each; each pair receives identical facts and signed
receipts under `raw` and `scope_explicit` instructions, in separate conversations
and controller trial namespaces. Five pairs per family use each order first.
Workers and reviewers are synthetic fixtures. This is an explicitly preliminary
exploratory cohort; the proposed two-model study remains separate.

The [frozen design](superpowers/specs/2026-11-09-paired-pilot-design.md) specifies
families, order, stop rules and analysis. Signing keys and sealed evaluator truth
never enter supervisor input. The model cannot verify private HMACs: forged
receipt scores measure decisions against sealed policy truth, not cryptographic
verification skill. Releases are local SQLite rows, with atomic audit records.

## Qualification and invocation

No command below supplies spending authority. The trusted operator must retain
review, exact-source CI, current provider access/prices/handling, host/TLS
qualification and a successful, account-reconciled calibration. Calibration
acceptance depends on transport, schema, identity and accounting; its answer
need not match the expected recommendation. The original failed calibration and
its reconciliation remain historical evidence.

Create an owner-private `controlled-openrouter-pilot-v1` record through the
existing operator procedure. It uses purpose `exploratory`, accepted calibration,
exact design and calibration-packet hashes under `study`, 160 requests, 4096 input
bytes, 256 combined output tokens, 30 seconds per call and at most two hours.
The run cap is at most $15 and provider lifetime cap at most $50. Use the existing
canonical ledger, retaining all previous charges. It refuses the whole schedule
unless its conservative bound fits both remaining caps. At $2.75/M input and
$11/M output, this admission bound is $13.06624; actual charges are separately
retained. GCP and Adaption budgets are separate.

The private calibration acceptance packet has schema `calibration-acceptance-v1`,
`calibration_authorization`, the original `result_raw` JSON string,
`reconciliation`, `applies_to_source_sha256`, `reviewed_by`, and an `applicability`
statement explaining why the reviewed runner can use that calibration. The
reconciliation includes the result-byte hash, generation identity/charge/token
counts, key usage delta, explicit checks and acceptance. Profile and rate record
must match the calibration. SHA-256 of canonical JSON binds this packet into the
pilot authorization. It is a trusted operator attestation, not a signature or
independent proof of provider behavior.

Run the reviewed pinned Python executable on clean committed source:

```sh
python -m fleet_witness.controlled_pilot \
  --authorization /private/pilot-authorization.json \
  --calibration /private/calibration-acceptance.json \
  --output /private/new-pilot-directory --live
```

The entrypoint validates qualification before reading a credential. It freezes
the complete schedule and signed fixtures before dispatch. It atomically claims
the run once in the canonical ledger, binding the authorization, output path,
plan and every scheduled request hash. A process-local capability is required
for calls; its clear value is never persisted. Every reservation atomically links
the scheduled call to its ledger attempt. A successful call is checkpointed only
after its controller work. Calls have no retry or automatic replacement.

## Stopping, recovery and evidence

An invalid output, transport/accounting failure or local error stops the cohort.
A process interruption also leaves the cohort consumed. Existing output paths
and claimed runs cannot be reused. Unknown charges stay held. Do not reset the
ledger, raise caps, delete failed artifacts or create a new run to evade a stop.
A deliberate later experiment needs a separately reviewed operator record.

Recovery exports committed evidence only, to a fresh private directory:

```sh
python -m fleet_witness.controlled_pilot \
  --recover /private/interrupted-pilot/pilot.sqlite3 \
  --ledger /private/canonical/spend-ledger.sqlite3 \
  --output /private/recovery-report
```

Private artifacts include frozen plan, all scheduled inputs and sealed labels,
provider outcomes, failure states, controller snapshots/decisions/effects/events,
and `report.json` / escaped static `report.html`. The canonical ledger retains
request bytes, response bytes, hashes, per-call times, reserved/settled/held
amounts and schedule links, including across a crash before the runner saves its
outcome. Preserve both databases. Reports use `live-pilot-1.0`; the v1 scripted
viewer is unchanged and does not consume them. No public service is started.

The report shows scheduled, dispatched, completed, invalid, failed, interrupted
and unstarted calls; complete pairs; bad approvals/denials; denied execution,
committed effects and duplicate no-ops. Invalid calls never become denials.
Statistics and families use explicit denominators. The paired raw-minus-explicit
bad-approval contrast has a range-two Hoeffding 95% interval only for all 80
completed pairs with no stop, under an unverified independent-pair assumption.
Incomplete cohorts have descriptive results only, with no coverage claim.

Reconcile every dispatched generation against its retained response and the
original sponsored key usage delta. Preserve provider-reported charges separately
from conservative ledger accounting. `account_reconciliation: required` is an
honest collection-time status; retain the later account receipt separately.

No worker credentials, public network scans, public-web fleet attribution,
Adaption calls, GCP changes or hosted dashboard are added by this entrypoint.
