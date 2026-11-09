# Controlled pilot foundation

## Controlled calibration candidate: 2026-11-09

`ModelClient.recommend(facts, presentation)` connects the existing provider
boundary to the closed supervisor contract. It copies only the six approved
fact fields, keeps paired facts identical, and varies only the instruction.
Adaption responses must name the selected model and a bounded response ID and
contain one assistant text message. A proposal has exactly `recommendation`
(`approve` or `deny`) and a nonempty reason of at most 2,048 characters.
Unknown keys, malformed JSON and incomplete answers are invalid outcomes.
Validly reported usage for invalid proposals is still accounted; uncertain
provider envelopes retain holds. The proposal, contract, raw response and usage
are committed with the accounting receipt, not reconstructed as a denial.

The new trusted-host module `fleet_witness.controlled_calibration` prepares one
synthetic build-receipt request and retains private `manifest.json` before
dispatch, then separate `result.json` on completion or recorded provider failure.
It requires deliberate `--live`, one reviewed source-bound authorization, the
canonical `~/.fleet_witness/spend-ledger.sqlite3`, one request, at most $15 after
verified conversion, at most 256 output tokens and a 30-second maximum deadline.
It reserves the entire authorized calibration envelope. Reusing the same run
with a new output directory cannot send another request. Existing files, old
JSON ledgers and unresolved holds are not reset. A different run/authorization
must not be issued to evade reconciliation of the first.

On 2026-11-09 the owner increased the calibration ceiling from $1 to **up to
$15 when required**, and authorized merging green code and trying calibration.
The operator record can choose a smaller envelope; $15 is a ceiling, not a
target charge. Successful accounting settles reported actual usage, while an
uncertain attempt retains the full selected reservation. Existing authorizations
and ledger caps remain immutable. This budget update does not waive ADR-0010's
provider, account or host qualification requirements. Older one-credit plans
and fixture receipts remain historical evidence.

This is a transport/schema calibration, not the 320-request paired study. It
returns data only, never calls the controller, and records `controller_effect`
as null rather than an unobserved safety result. `controlled-calibration-v1`
is a private receipt format, not a viewer replay. Existing scripted/fake modes
remain unchanged. All new executed tests use synthetic keys and mocked HTTPS.

Help is inert:

```sh
python -m fleet_witness.controlled_calibration --help
```

**Live activation remains on hold.** No real authorization was issued or paid
request sent by this integration. The owner supplied current account text:
1,500 credits, 1 credit = $1, credits never expire. Public model prices and full
terms/privacy were retrieved. Complete reasoning/fee bounds, inference charge
reconciliation, applicable model handling, and actual host/TLS/worker acceptance
remain open. Qualification flags are operator assertions, not independent proof;
do not set them to true merely to run the command. See [GATES](GATES.md).

Before issuing a record, bind account identity, source, runtime and trust
material to the reviewed evidence, verify the host's credential and egress
boundary, and reconcile applicable prior usage. The current transport has
offline regressions; its default TLS context is not the qualified pinned trust
boundary required by the live-gateway design. No actual-key connection is made
until that separate requirement closes. The single calibration must be matched
to actual account billing before any confirmatory authorization is issued.

## Historical offline foundation

ADR-0010 was accepted, GCP boot and all four offline workers were exercised,
and the separate authenticated dashboard was deployed in the earlier work.
Those receipts do not verify today's service lifetime or new gateway host.
The following sections describe the original fake gateway. The later
`live_gateway` and `calibration_registry` modules are also explicitly offline
fixtures; their names do not establish a production provider integration.
See [current gates](GATES.md) and [build evidence](BUILD_STATUS.md) for the
current state. No live inference or calibration is claimed.

The owner selected both controlled experiments and later public attack
observation, beginning with the controlled pilot in the
[reviewed proposal](proposals/live-model-adapter.md). This task implements the
**offline foundation**. It provides no live provider transport, account access,
live replay format, automatic experiment runner, or network permission.

## Implemented interfaces

`fleet_witness.gateway` uses Python's standard library and SQLite:

- `provider_input(facts, presentation)` validates a closed fact schema and
  creates an independent bounded copy. Only the instruction and visible facts
  reach the provider. Request IDs remain outside that input. Nested extra fields,
  invalid policy types, oversized data, and invalid Unicode are refused.
- `BudgetLedger(path, limit_units)` persists an owner-private ledger with a
  fixed integer envelope. Its parent directory is a trusted operator location.
  Existing symlinks, hard links, shared permissions, and a different envelope
  are refused. The host owner can still alter the database; this is no sandbox
  against another process with that owner's filesystem authority.
- `reserve`, `dispatch`, `settle`, and `uncertain` record state and audit together
  in one transaction. Reservations share a single remaining envelope and only
  one request may be dispatched at a time. The provider runs outside the write
  transaction. Request IDs cannot be reused, including after settlement.
- `receipt(request_id)` returns the fake request's detached visible input,
  canonical input hash, token bound, bounded terminal raw text when available,
  and committed normalized result. Reservation records the input first; result,
  accounting transition and audit commit together. Interrupted requests can
  have no result, and pre-existing receipt-free requests remain receipt-free.
  The ledger is private operator data; this is not live-provider provenance.
  Text is persisted without automatic redaction, encryption or expiry, and the
  example below prints it. Keep inputs synthetic; apply the security policy
  before any future collection of real data.
- `ProviderReply(output_text, usage_units, status="completed", tool_calls=False)`
  is the fake adapter's result. Real-provider usage conversion is unimplemented.
- `FakeProvider(replies=None)` returns deterministic supplied results or raises
  supplied failures. The default contains one inert denial response costing one
  **synthetic unit**. These units have no dollar, credit, or token conversion.
- `Gateway(ledger, provider).run(request_id, facts, presentation, reserve_units,
  max_output_tokens=512)` validates before reserving, dispatches once, and returns
  an `offline-fake` result. Valid proposals contain only `approve`/`deny` and a
  bounded reason. Extra/duplicate keys, tool items, incomplete responses, bad
  Unicode, and malformed/oversized output are invalid outcomes, not model denials.

The gateway has no controller reference and cannot create a release. An approval
is inert data. Any later bridge must record the immutable decision through the
trusted controller and independently exercise its current authorization checks.
The existing `demo` and `serve` CLI paths remain unchanged.

## Accounting and recovery behavior

| Result | Ledger consequence |
| --- | --- |
| Valid or invalid output with verified synthetic usage within reservation | Settle actual units; release unused reservation; record outcome |
| Terminal provider failure/cancellation with verified final usage | Settle actual units under a distinct `provider_error` outcome; never invent a model recommendation |
| Nonterminal/unknown provider status, exception, or timeout | Hold full reservation, record unresolved status, halt new dispatch |
| Crash after dispatch | Keep dispatched status and full reservation; block another dispatch after restart |
| Missing, malformed, or excessive usage | Record accounting error and halt; retain the reservation or the larger known liability |
| Reused request identity | Refuse before another provider invocation |
| Audit insertion failure | Roll back the corresponding ledger state change |

No automatic retry, refund, reconciliation, or manual-reservation-clear command
is implemented. Preserve the ledger and diagnose its state. Reserved requests
interrupted before dispatch also remain held until a reviewed recovery mechanism
is added. A provider overrun can make available units negative; the ledger records
that liability and prevents further dispatch rather than concealing it.

## Reproduce an inert request

Run this from the candidate checkout. It creates a new private state directory
for this example and makes no network request:

```sh
python - <<'PY'
import os
from pathlib import Path
import tempfile
from fleet_witness.gateway import BudgetLedger, FakeProvider, Gateway

state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'fleet-witness'
state.mkdir(mode=0o700, parents=True, exist_ok=True)
run = Path(tempfile.mkdtemp(prefix='offline-pilot-', dir=state))
ledger = BudgetLedger(run / 'budget.sqlite3', 10)
facts = dict(run_id='opaque-example', artifact_digest='sha256:example',
             decision_time_policy=None, receipts=[], reviewer_verdict='deny',
             reviewer_statement='No release-safety attestation supplied.')
print(Gateway(ledger, FakeProvider()).run('offline-example', facts, 'raw', 2))
print(ledger.snapshot())
print(ledger.receipt('offline-example'))
PY
```

Expected: `mode=offline-fake`, status `completed`, recommendation `deny`, one
synthetic unit spent, zero held, and nine available. Dictionary formatting is
ordinary Python output. Retain state rather than reusing/deleting a past run.

Verification commands:

```sh
python -m unittest discover -s tests -p test_gateway.py -v
python -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
python scripts/fleet.py validate
git diff --check
```

The initial fifteen tests failed before implementation. Subsequent malformed
Unicode cases exposed two actual output-handling failures; both were reproduced
before correction. The focused suite then passed fifteen tests. Independent review found response
status-finality and failure-classification errors; new tests reproduced both
before correction. That historical foundation run passed seventeen focused
tests, seventy-two Python tests and five viewer tests. A later receipt change
passed thirty focused tests and eighty-five full Python tests; see the
[build record](BUILD_STATUS.md) for source and artifact evidence.

## Activation still required

ADR-0010 is an accepted design, with implementation and activation pending.
The exact provider transport, independently verified account-specific rates and
usage semantics, operator spend record, usage reconciliation,
private runtime credential injection, egress policy, live evidence/provenance
capture, live replay schema, randomized study runner, and real calibration remain
unimplemented. Existing demo scenario names in IDs are unsuitable for blinded
live trials; the new runner must generate opaque shared trajectory IDs and keep
oracle labels outside visible inputs.

The $100 GCP authorization and owner-reported $1,500 Adaption balance remain
separate. Neither is a balance verified by this fake ledger. The GCP project and first worker execution are established; remaining host,
recovery, runtime-migration and cost acceptance stay open. Public attack
observation follows the controlled pilot under a separately approved scope; the
current [security policy](SECURITY_POLICY.md) remains applicable.
