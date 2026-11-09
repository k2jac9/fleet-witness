# Observed paired-pilot evidence — November 9, 2026

The [completed experiment record](experiments/2026-11-09-openrouter-paired-pilot.md)
reports 160 calls / 80 pairs, controller effects, failures retained separately,
account reconciliation and limitations. Explicit presentation denied all cases;
zero invalid approvals alone is not a useful release-selection result. A trusted
verifier-result follow-up is proposed there, with no new interface or cohort
claimed. The runbook and historical qualification record follow.

---

# Azure opaque metadata compatibility — November 9, 2026

The first exploratory cohort at `92754a9` stopped after one response carried
`reasoning.encrypted` metadata despite `reasoning.exclude=true`. It recorded no
decision or effect and left 159 calls unstarted. The response/generation/key
charge agrees at $0.0016104, including 287 input and 89 combined output tokens
(28 reasoning). The original failure is retained; accounting reconciliation
cannot resume it or turn its unaccepted proposal into a scored decision.

[OpenRouter documentation](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)
defines the encrypted reasoning-details shape and Azure format. This adapter
accepts one bounded opaque object only for the qualified Azure route and model,
with exact keys/type/format, an rs_ identifier, zero integer index and up to
32 KiB of restricted-character data. It never decodes, interprets, replays or
puts those bytes into a proposal. Plaintext reasoning, summaries, unqualified
formats, unknown fields and invalid usage still fail. Raw bytes remain only in
private response evidence. The exclusion setting is a request, not proof that
no opaque metadata returned; no extra retention guarantee is asserted.

A separately reviewed operator reconciliation may link a failed receipt to
verified charge evidence through an atomic `operator_charge_reconciled` audit.
Recovery retains the original failed receipt and reports the reconciled settled
amount separately. Missing/mismatched audit links are refused. There is no
automatic hold release or retry. Prior run and source evidence remain unchanged.

---

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

---

The following foundation record is retained. Its historical activation gaps are
superseded only by the observed evidence and additive scope above.

# Controlled pilot foundation

## Controlled OpenRouter profile: 2026-11-09

The runner also accepts an additive `controlled-openrouter-v1` operator record.
It retains the existing record fields and adds `openrouter`: exact provider slug,
provider response name, expected response model, reasoning effort, token-limit
parameter and a pinned transport profile. Generic `swarm-paid-v1` OpenRouter
clients cannot enter the supervisor path; controlled profiles cannot enter
generic completion. Adaption and offline consumers remain supported.

This profile requires one calibration request, at most 256 combined output and
reasoning tokens, 30 seconds, a run cap up to $15 and provider cap up to $50.
Its fixed request pins the provider route and standard service tier, disables
fallbacks/tools/streaming/storage, requests data-collection denial and ZDR
routing, and requires strict JSON output. Unknown identities, tool content,
unqualified BYOK or invalid/missing reported cost retain the reservation.
An exhausted token budget with no visible text is an accounted invalid proposal.
OpenRouter's normalized `stop` may carry Azure's native `completed` status.
The documented `image_tokens` completion detail is accepted only when zero;
positive nontext usage and contradictory completion states remain invalid.
The request also caps provider input/output prices at the reviewed rates and
per-request fees at zero. The initial authorization identity is retained;
valid-looking configuration changes after client construction are refused before
key access, reservation or dispatch. Usage fields and prompt/completion details
have separate closed schemas. Contradictory upstream cost details halt the run
while preserving any larger known monetary liability. Encoded credential echoes
are redacted from HTTP-error receipts too; unsafe malformed echoes are replaced
by a digest-bearing marker.

Transport binds exact Python executable/hash, OpenSSL version, CA bundle/hash,
and root-certificate hashes. It verifies hostname and chain without loading
default/environment trust or TLS key logging. Credentials come from a canonical
owner-private directory and a 0600 singly-linked regular file; there is no
environment-key fallback. These controls assume a trusted host and do not
isolate hostile processes running as the owner.

The sponsored inference key has a verified $50 allowance and the owner supplied
the organizer's funding confirmation. No sponsor management key is required;
a separate personal workspace's balance is unrelated. Sponsor account-wide
funds and sponsor privacy opt-in settings are not directly observed.

Provider qualification considers the Azure US route for GPT-6.1 Sol with low
reasoning and `max_completion_tokens`. Current ZDR routing excludes first-party
OpenAI. Conservative cache-write pricing bounds input charges. ZDR filtering
does not establish universal zero retention: OpenRouter metadata/opt-in/legal
policies and Microsoft's safety-retention exceptions remain applicable. Inputs
are synthetic, without credentials, issuer keys, user data or evaluator answers.

Receipts distinguish `provider_reported_cost_usd` from the conservative ledger
amount: the larger of reported charge and token-rate bound. Recognizable
generation identity and charges survive invalid content or HTTP failures.
Check the original key's usage and generation receipt before another run;
no automatic retry or hold release occurs.

These are implemented boundaries, not a claim of completed live acceptance.
See BUILD_STATUS and the retained packet for exact executed checks. The local
calibration launches no worker, listener or controller effect; it does not
qualify future worker-connected or cloud deployment topologies.

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
