# ADR-0007: Isolated worlds for paired trials

- Status: Accepted for the initial prototype
- Date: 2026-11-08
- Clarifies: ADR-0003 and ADR-0004

## Context

Raw and scope-explicit evidence must reuse identical facts and signed receipts. Giving each presentation a different signed run identity changes its evidence. Sharing the same mutable release state lets the first condition contaminate the second.

## Decision

Treat each presentation as an isolated counterfactual trial in the same SQLite database. `trial_id` identifies the independent world and equals the replay episode ID. `run_id` identifies the shared underlying trajectory; `pair_id` links the two presentations. Scope mutable policy, decisions, attempts, effects, and audit queries to the trial. Effect uniqueness is `(trial_id, run_id, artifact_digest)`, meaning at most one release per run/artifact in each independent world.

The two worlds intentionally reuse the same signed trajectory receipt. Execution obtains its trial from the trusted stored decision, never from an untrusted caller override. Wrong-run evidence remains invalid. Trial identity is orchestration metadata, not an extra evidence fact given to one supervisor condition.

## Alternatives

Distinct signed run IDs weaken the exact pairing contract. One shared mutable world introduces order effects. Separate database files provide isolation but complicate exports and are unnecessary for this controlled simulator.

## Consequences

The single-database uniqueness language in ADR-0003 applies within a trial. This is logical experimental isolation, not hostile-process containment. The future live-model harness must preserve this distinction.

## Validation

Paired evidence facts and receipts compare equal. Both legitimate paired conditions can release independently. Duplicate execution inside either trial produces only one effect. Revoking authorization in one trial cannot mutate the other.
