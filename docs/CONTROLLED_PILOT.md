# Controlled pilot foundation

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
| Provider exception/timeout | Hold full reservation, record unresolved status, halt new dispatch |
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
before correction. The focused suite then passed fifteen tests, with seventy
Python tests and five viewer tests passing across the candidate. The
[build record](BUILD_STATUS.md) binds those observations to source and artifacts.

## Activation still required

The reviewed proposal's new ADR, exact provider transport and account model
access, verified rate/unit conversion, operator spend record, usage reconciliation,
private runtime credential injection, egress policy, raw evidence/provenance
capture, live replay schema, randomized study runner, and real calibration remain
unimplemented. Existing demo scenario names in IDs are unsuitable for blinded
live trials; the new runner must generate opaque shared trajectory IDs and keep
oracle labels outside visible inputs.

The $100 GCP authorization and owner-reported $1,500 Adaption balance remain
separate. Neither is a balance verified by this fake ledger. Reachable GCP
authorization/project and worker boot acceptance are also open. Public attack
observation follows the controlled pilot under a separately approved scope; the
current [security policy](SECURITY_POLICY.md) remains applicable.
