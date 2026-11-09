# Controlled OpenRouter calibration implementation plan

> **For agentic workers:** Use superpowers:executing-plans for implementation and an independent whole-branch review. The owner already authorized implementation, green integration, and bounded calibration; no repeat approval is required.

**Goal:** Execute one auditable, synthetic supervisor calibration using the existing sponsored OpenRouter key after applicable qualification succeeds.

**Architecture:** Extend the existing controlled runner and transactional ledger. Introduce an additive `controlled-openrouter-v1` authorization schema, preserving `swarm-paid-v1` consumers. A strict OpenRouter profile fixes routing and response interpretation; a separate transport profile fixes runtime, TLS roots and private credential loading. Remote model output has no controller or tool authority.

**Tech stack:** Python standard library, SQLite, existing Python and Node CI lanes. Host execution must bind exact runtime identities; compatibility checks do not claim host promotion.

**Spec:** ADR-0010, `docs/proposals/live-model-adapter.md`, and the owner's approval of the four-step OpenRouter implementation/calibration scope. This is the provider-specific implementation of that scope; accepted ADRs remain unchanged.

## Global constraints

- One request, one in flight, no implicit retries, at most 256 output tokens and 30 seconds. Calibration monetary envelope at most $15, OpenRouter provider envelope at most $50. GCP $100 and Adaption credits remain separate.
- Fixed endpoint `https://openrouter.ai/api/v1/chat/completions`. Direct reviewed model ID and one reviewed provider route, no automatic fallback. Disable tools, streaming, storage and model-selected network actions.
- Synthetic facts only, exact existing visible-field allowlist. Closed proposal: `recommendation` approve/deny and bounded nonempty `reason`. Bad proposals are invalid outcomes, not denial labels.
- Reserve the entire calibration envelope in the existing canonical ledger before dispatch. Unknown charges, malformed envelopes, crashes and timeouts hold funds and stop subsequent requests. Never reset holds or mutate persisted caps to retry.
- Owner-provided organizer email establishes a sponsored $50 allocation; key-level API evidence establishes a $50 unused allowance. The unrelated management account's $0 is not evidence about sponsor funding. No management key is required or used.
- Preserve every historical receipt, old worktree and accepted ADR. No cloud deployment, external messaging, public sensor or network scanning in this work order.

## Design decisions

Use an additive controlled profile rather than weakening the generic permissive completion parser or creating a second ledger. Keep `swarm-paid-v1` behavior for its existing consumers; the new controlled OpenRouter entrypoint requires its new schema. New profile fields are operator assertions bound into the existing source digest and immutable authorization envelope, not signatures or proof of a trustworthy host.

The `openrouter` profile contains `provider_slug`, `provider_name`, `response_model`, `reasoning_effort`, `output_token_parameter` and `transport`. The transport profile contains `key_file`, `ca_file`, `ca_sha256`, `root_sha256`, `python_executable`, `python_sha256`, and `openssl_version`. Exact field sets and safe values are validated before credential access or ledger creation. TLS uses only the approved root certificates from the hashed bundle, hostname verification and no environment proxy, key-log, redirect or retry discovery. Public peer-chain qualification remains separate observed evidence.

Requests require the selected provider, `allow_fallbacks=false`, `require_parameters=true`, `data_collection=deny`, `zdr=true`, `store=false`, no tools, and a strict JSON schema. The candidate uses explicit low reasoning with excluded reasoning text and a combined output/reasoning token bound. A ZDR routing flag alone is not proof of every provider's retention policy; review current endpoint metadata, safety-retention caveats, OpenRouter metadata and upstream terms before qualification.

Strict responses require the selected model/provider, a bounded generation ID, exactly one assistant text choice, recognized finish reason, no executable/tool content and valid itemized usage. A real reported total cost is required for this path; conservative token accounting must never understate a larger reported liability. Reconcile the generation receipt and original key usage after the one paid call before any further run.

## Design review corrections

Independent review corrected the initial disabled-reasoning design: current
GPT-6.1 Sol requires reasoning. The implemented profile additionally contains
`reasoning_effort` and `output_token_parameter`. Candidate: Azure US route,
explicit `low` reasoning, excluded reasoning text, and a combined
`max_completion_tokens` bound. Omit temperature. The first-party OpenAI route
is excluded by current ZDR routing policy. Pin `only` and `order` to the same
route and service tier to `default`. Use a conservative cache-write input rate.
Retain provider-reported charge separately from conservative ledger accounting.
Recover known charge and generation ID even from invalid envelopes/HTTP errors.

The literal owned-path scope additionally includes `tests/test_swarm_provider.py`
only to replace an uninitialized legacy truncation fixture with a real client
and ledger, preserving the no-retry assertion. This correction was recorded in
the task progress ledger before editing that file.

## Owned paths

Primary integrator owns `fleet_witness/swarm/openrouter_controlled.py`, `fleet_witness/swarm/secure_transport.py`, `fleet_witness/swarm/authorization.py`, `fleet_witness/swarm/providers.py`, `fleet_witness/controlled_calibration.py`, `tests/test_openrouter_controlled.py`, `tests/test_secure_transport.py`, `docs/CONTROLLED_PILOT.md`, `docs/GATES.md`, `docs/BUILD_STATUS.md`, and this plan. Durable task evidence and independent review live in `/home/neo/Projects/fleet-witness-artifacts/openrouter-calibration-20261109/`. Any needed scope extension is recorded before editing additional paths.

## Review focus

- A malicious caller changes routing or transport after construction: revalidate the detached authorization and effective request at dispatch.
- A response names another model/provider or includes a tool: retain the liability and halt; no proposal or effect.
- A private key path becomes a symlink, hardlink or public file: refuse before dispatch and keep secrets out of errors.
- Environment variables try to inject TLS trust, proxying or key logging: explicit context and connection settings ignore them; test against actual local TLS where possible.
- A crash or timeout follows dispatch: retain the full reservation, prohibit another request, and reconcile externally.

## Task 1: Secure controlled transport

Interfaces: `validate_profile(profile)` validates exact nonsecret transport fields; `prepare(profile)` verifies runtime and CA identities and returns an explicit SSL context; `read_key(profile)` reads only an owner-private singly-linked regular key in a canonical private directory.

- [ ] Write failing behavior tests for safe loading, permissions/symlinks/hardlinks, runtime/CA/root mismatch, environment TLS/key-log injection and alternate-root rejection.
- [ ] Run RED and retain the failure receipt.
- [ ] Implement the boundary without adding runtime dependencies. Extend `_post(..., ssl_context=None)` to permit the verified context without changing legacy callers.
- [ ] Run focused tests GREEN and the full standard-library suite; retain runtime/command identities.

## Task 2: Strict OpenRouter contract and authorization

Interfaces: `validate_profile(record)` checks the new controlled profile; `request_fields(profile)` provides protected routing/schema fields; `validate_envelope(data, record)` validates identity, closed message shape and authoritative cost before accepting a proposal.

- [ ] Write RED tests for valid paired facts, route/parameter preservation, identity mismatch, tool refusal, missing/invalid cost, unexpected output, budget holds and invalid proposal accounting.
- [ ] Extend authorization with additive `controlled-openrouter-v1`; enforce provider OpenRouter, purpose calibration, one request, max $15/$50, token/time limits and complete profile. Existing generic schemas remain unchanged.
- [ ] Add strict `ModelClient.recommend` handling through the existing ledger; require and use protected key loading and explicit TLS only for this new profile. Reserve the full request envelope.
- [ ] Run focused and complete Python/viewer suites; preserve all failed receipts.

## Task 3: Controlled runner and recovery

- [ ] Write RED tests showing the existing runner accepts the qualified new OpenRouter schema, selects its actual provider, preserves private manifest/result files, and refuses repeated dispatch or unqualified profiles before key/network access.
- [ ] Generalize only the bounded runner's provider selection. Preserve Adaption regression behavior, deliberate live selection, source binding, canonical ledger and no controller effects.
- [ ] Run full Python/viewer checks, offline verification and source-bound runtime CI. Update current docs with observed checks and explicit unexecuted gates.

## Task 4: Provider/host qualification, review, calibration

- [ ] Retain current official endpoint/routing/cost/reasoning/privacy documentation and key catalog evidence. Select one direct model and one route. Verify conservative input/output bounds and all applicable charges.
- [ ] Verify the actual host runtime, TLS trust/hostname/alternate-root rejection, private credential placement, applicable worker exclusion and failure/recovery behavior. Scope cloud and worker claims to what was actually exercised.
- [ ] Independent reviewer reads the exact branch diff and qualification packet; resolve critical/important findings and rerun affected checks. Integrate only the exact green source already authorized by the owner.
- [ ] If qualification passes, create a private source-bound one-request operator record, then dispatch exactly one calibration within the approved envelope. If any prerequisite fails, retain the explicit hold and finish all independent engineering work.
- [ ] Reconcile returned cost, generation charge and original key usage. Record model input/output, proposal, errors, timing, accounting and provenance without secrets. Calibration is not a paired confirmatory study or evidence of wild-world fleets.
