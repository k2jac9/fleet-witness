# ADR-0010: Trusted live-model gateway and bounded pilot

- Status: Accepted design; implementation and live validation pending
- Date: 2026-11-08
- Supersedes: none
- Extends: ADR-0001 through ADR-0005, ADR-0007 and ADR-0008

## Context

The owner wants controlled real-model experiments and has authorized bounded
cloud expenditure. The deployed workers currently run deterministic offline
tasks. They have neither provider credentials nor a provider connection. The
existing gateway accepts only an inert fake and synthetic accounting units.
The [proposal](../proposals/live-model-adapter.md) defines an initial paired
supervisor study and its unresolved provider and security prerequisites.

Current accepted decisions do not grant a model authority to release, change
policy, make arbitrary network calls, or publish. They also do not authorize
worker-connected gateways or a public attack sensor. A separate design is
needed for a controlled change without weakening those boundaries.

## Decision

The owner selected the controlled pilot and, on 2026-11-08, explicitly asked
to proceed with the reviewed gateway, spend controls, security checks and
calibration. This accepts the design direction; it does not waive the checks
below or establish facts that have not been verified. Once the applicable
pre-calibration gates are met, a trusted host-side
gateway may submit explicitly authorized supervisor requests. It is separate
from the isolated workers and the controller; no provider credential, network
access or general host command facility is given to a worker. The gateway
returns data only. The controller alone evaluates current authorization and
commits any local effect and its audit event atomically.

The trusted runner builds each request using the proposal's exact model-visible
allowlist. It excludes issuer keys, privileged truth, expected answers,
orchestration labels and evaluator results. Paired conditions receive
byte-identical signed evidence and the same facts, use separate mutable trial
state and separate provider conversations; only the presentation instruction
changes. Closed-schema recommendations with a bounded reason are parsed as
untrusted data. Unknown keys, invalid JSON, unexpected output items or tool
calls, and size violations are invalid outcomes, not correct denials.

The provider adapter accepts only reviewed model IDs and a fixed TLS endpoint,
enforces reviewed input byte/token and output token limits before dispatch,
and bounds response bytes and parse depth.
It cannot choose URLs from the model or input, invoke tools, run code, follow
unreviewed redirects, or implicitly retry. For the proposed Adaption adapter,
direct model IDs only are permitted, with `tools=[]`, `tool_choice="none"`,
`agentic_memory=false`, and `store=false`; these settings do not establish
provider-wide zero retention. No live data is sent until provider handling,
model access, limits and billing are independently verified.

The operator establishes a private persistent shared ledger, separately from
worker outputs. Each ledger transition and its audit event commit atomically.
Shared reservations fail closed: the gateway reserves a conservative bound
before each call and records dispatch before network I/O. The pilot has one
in-flight request, one attempt per request and a 30-second client deadline.
The ledger uses verified fixed-point provider units, includes all billed input,
output and reasoning, and treats a timeout, crash, missing usage, excess usage
or ambiguous provider response as unresolved. Unresolved reservations remain
held and halt further dispatch until reconciled; they are never retried
automatically. A known charge exceeding its reservation is recorded as the
larger liability even if available funds become negative; the overrun is never
silently reduced. A model request must fit the authorized envelope, count and
runtime limits after all settled and held charges are accounted for. No
conversion between provider credits and money is assumed.

The runner retains provenance, failure counts and accounting separately from
the model-visible input. A new versioned replay must distinguish live and
scripted data and maintain the existing viewer's inert rendering and strict
asset boundaries. Version 1 scripted replays and their consumers remain
supported. The predeclared paired study, sampling, analysis, failures and
limitations are as specified in the proposal; calibration is separate and
cannot be counted as confirmatory data.

## Alternatives

- Distribute credentials to workers: rejected because it expands authority and
  makes enforcement of a single spend envelope unreliable.
- Continue fake-only operation: retains the existing boundary but cannot
  produce empirical model results; it remains the default until authorized
  live activation passes its gates.
- Public attack observation first: needs a separate, scoped research and
  isolation design and cannot establish this paired supervisor comparison.

## Consequences and migration

Accepting this record would extend rather than silently change the earlier
ADRs. It introduces a trusted external-data and credential boundary, provider
availability and cost risk, a durable ledger and a replay migration. Offline
tests remain free, dependency-free by default and unable to activate a real
provider. Existing scripted mode, transactional effects, worker isolation and
viewer checks must continue to pass. The pilot does not create an autonomous
coding fleet or identify external actors; any such capability needs a separate
reviewed scope. A container is not a separate-kernel isolation guarantee.

Acceptance alone, the GCP budget and OAuth setup do not activate provider calls.
The earlier accepted contracts continue to apply. Every paid run,
including calibration, requires deliberate live-mode selection and a valid
operator authorization record specifying the provider, verified budget,
request count and duration. Owner delegation of development is not evidence
that a model, rate table, credit conversion or provider retention policy has
been verified. The previously selected inert offline foundation remains
permitted under its existing boundary.

## Validation required before any paid calibration

1. Independent review of this decision and its implementation, including
   credential placement, request allowlists, output parsing and failure states.
2. Failing behavioral tests followed by passing tests for concurrency,
   crash-after-dispatch, exhaustion, invalid or missing usage, overspend,
   malformed outputs, data leakage, paired facts and preserved controller
   authority; full Python and viewer suites and compatibility checks.
3. Exact account-accessible model IDs, endpoint, applicable price version,
   billable usage units and conversion, all output and reasoning bounds, and
   an operator-recorded request, duration and monetary envelope. Unknowns
   stop dispatch; reconcile usage against the actual provider account.
4. Reviewed terms for synthetic input and output handling, credential access,
   redaction, retention and deletion. No credential in worker, image, prompt,
   source, replay or logs. Verify TLS/egress and worker denial independently.
5. Complete applicable host and cloud acceptance, recovery, and cost controls;
   preserve tested rollback assets and explicitly record unexecuted checks.
6. Specify and authorize a bounded calibration, including its own request,
   duration and spend limits and failure stop criteria.

## Validation required before the confirmatory study

Complete the separately labeled calibration and reconcile its usage. Freeze
the main study's models, prompts, schedule, analysis and budget after
calibration and before confirmatory collection. Report incomplete or unstarted
calls and preserve unresolved reservations and evidence.

## References

- [Bounded live-model experiments and gateway proposal](../proposals/live-model-adapter.md)
- [Adaption Responses API](https://docs.adaptionlabs.ai/api/python/resources/responses/methods/create)
- [Security policy](../SECURITY_POLICY.md)
