# Offline fake gateway receipts

The fake-only gateway currently settles usage in SQLite and returns a proposal
in memory. If the caller crashes immediately after settlement, the request ID
cannot be retried but the result is lost. Persist enough synthetic request and
response evidence to inspect that result after reopening the ledger.

This is an offline foundation change. The owner task `offline-receipts` owns
`fleet_witness/gateway.py`, `tests/test_gateway.py`, `docs/CONTROLLED_PILOT.md`,
this design, and its plan;
the existing `fleet/controlled-pilot` branch is an isolated linked worktree.
No provider transport, credentials, controller authority, worker connection,
new replay mode, or paid call is introduced. Ledger contents remain private
trusted-host data, not a mechanism for isolating hostile host processes.

The gateway stores a deep-copied validated visible payload and token setting
atomically with the reservation, before dispatch. For recognized terminal fake
replies it stores response text when it is valid UTF-8 and at most `MAX_BYTES`;
malformed Unicode or oversized text is represented as unavailable. Exceptions
and nonterminal or unknown provider statuses do not retain raw text; a terminal
reply with unresolved usage can retain bounded text. It stores the normalized
result with settlement or unresolved status and the same transaction's audit
event. Arbitrary exception messages and unbounded provider objects are not
persisted. A read-only lookup returns copies after reopening; missing or legacy
receipts return `None`. Existing ledgers and unresolved reservations survive
an additive schema migration without fabricating historical receipts.

The persisted result matches the committed accounting outcome and returned
result: missing or excessive usage yields `accounting_error` without a
recommendation, even if output parsed successfully. Validate result identity,
mode, shape and bounds before writing. A request with an input receipt cannot
transition to an outcome without a matching result; legacy receipt-free
requests retain their old API behavior. A reserved or dispatched receipt has
no result, and terminal receipts cannot be overwritten. Unavailable raw text
is `None`, distinct from valid empty text; unsupported objects are not
stringified into receipts.

A crash after dispatch retains its hold; a crash after committed settlement
leaves the result inspectable. If receipt or audit insertion fails, the entire
state transition rolls back, leaving the prior hold intact. Duplicate IDs,
fake-only behavior and current budget checks remain in force. The data is
synthetic; persistence is not evidence that a live provider, pricing, retention,
blinding or paid-run authorization is ready.
