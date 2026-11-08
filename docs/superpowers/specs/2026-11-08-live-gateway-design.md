# Bounded trusted-host live gateway

Task `live-gateway`: the primary owner agent works in the isolated
`fleet/controlled-pilot` worktree. Owned implementation paths are
`fleet_witness/live_gateway.py`, `tests/test_live_gateway.py`, this design and
its implementation plan; integration documentation includes ADR-0010,
`docs/adr/README.md`, `docs/ADAPTION.md`, `docs/CONTROLLED_PILOT.md`, and
`docs/BUILD_STATUS.md`. Independent review is required before live activation.
The existing fake-only gateway and offline baseline remain unchanged.

## Scope and authority

The user selected a controlled pilot and asked on 2026-11-08 to implement the
reviewed gateway, spending controls, security checks and bounded calibration.
This authorizes the design direction and use of the existing protected Adaption
key. For the first calibration the operator chooses a ceiling of one Adaption
credit for one request, one in-flight request, 30 seconds, and no retries.
The owner separately stated a $100 GCP ceiling and reported 1,500 available
Adaption credits. The owner reported 1 credit = $1, without specifying a
currency. This is
not an independently retrieved balance or a statement that cloud and provider
credits share a ledger. No GCP VM is started by this task.

Live default remains off. Synthetic input only, chosen by trusted code; no
worker connects to a provider, receives credentials, launches this gateway or
supplies arbitrary commands or URLs. A supervisor can propose only approve or
deny. The existing trusted controller is the only component with authority to
commit a local effect and audit; this gateway cannot access the controller or
perform effects. A later main paired study and public attack-observation scope
remain separate and must not be claimed from calibration.

## Budget and provenance

For the accessible `gemma-4-31b-it` hosted ID, the 2026-11-08 public model table
lists 0.09 input and 0.34 output credits per million tokens and a 256,000 token
combined context. The captured public page and its SHA-256 are recorded with the
evidence packet; the offline fixture tests use a placeholder hash and do not
bind that snapshot to a live run. Current account-specific billing and
provider-side ceilings are not yet independently verified. Use uncached input
price as a conservative basis.

A private SQLite ledger uses integer microcredits, a frozen authorization record
and BEGIN IMMEDIATE transactions. The offline fixture checks expiry before
reservation and dispatch and enforces one attempted request, one in-flight
request and a 1,000,000 microcredit reservation. It stores a 30-second setting
but does not implement a whole-call deadline or any network call. Production
must enforce that deadline and reserve before network I/O. Reserving the entire
one-credit envelope dominates the
published per-token table for a single 256,000-token context at its higher
published rate (0.08704 credit), assuming no undisclosed charges and that the
published context includes all billed tokens. Those assumptions are not
provider guarantees. ADR-0010 blocks even the first paid calibration until the
applicable charge basis, reasoning-token bounds and worst-case reservation are
verified. Local reservations cannot enforce a provider-side spending ceiling.
Provider billing reconciliation is separately required before a larger cohort.
No automatic retry is permitted.

The authorization must bind a unique authorization ID, verified provider
account/organization, exact source identity, expiration, and a canonical
ledger identity. A single-use registry must prevent authorization reuse through
another ledger path or after settlement; per-database limits alone are
insufficient. The current experimental ledger is an offline test foundation and
does not yet implement that global activation boundary.

Requests and accounting transitions plus audit events commit atomically. A
crash after marking dispatch, timeout, nonterminal status, missing usage,
unknown charge basis, token counts beyond the published context or unexpected
cost hold the reservation and stop new dispatch. Results and reported usage
are untrusted; validate bounded response bytes, status, IDs, output types,
closed recommendation schema and integer usage. Preserve the full liability
when reported usage exceeds the reservation. Do not infer zero cost from a
client-side failure. No signed issuer key, scenario truth, API key or private
metadata is sent to the provider or logged. Receipts distinguish live from
fake and are saved privately with request identity and status; the historical
scripted replay format is unchanged.

## Transport and secret boundary

The only live destination is the fixed Adaption HTTPS Responses endpoint. Disable
proxy inheritance, redirects and implicit retries, use explicit tools=[],
tool_choice=none, store=false, agentic_memory=false, bounded output and a
30-second whole-call timeout. Reject unknown endpoints, stack IDs, tool calls,
nonterminal responses, malformed JSON and invalid or oversized output. The
credential is read at runtime from the verified owner-private regular file;
never print it or put it into Git, Nix, worker data, command-line arguments or
logs. The executable and TLS backend must be pinned; disable curl configuration,
proxy variables and inherited TLS/key-log settings, and deliver the key on a
private channel outside argument lists. TLS trust must block the compromised
eMudhra public keys even through alternate cross-signed chains, not merely
remove one root. Verify exact trust material and transport behavior before
sending credentials; no claim of provider-wide zero retention follows from
store=false. Until these properties and billing bounds are proven, no live
transport is enabled.

## Evidence and activation

Before dispatch, independently review design, diff, pinned trust/rates,
credential/egress boundaries and initial authorization; run red/green security
behavior tests, full Python and viewer tests, migration and crash cases, and
record unexecuted cloud acceptance. A source-bound live run has explicit
operator activation and ledger identities. Capture status, provider response ID,
reported usage, elapsed time and sanitized result. Do not release unresolved
reservations or expand the study until provider billing is reconciled. The
operator must not claim an authorized live result until one is actually returned.
