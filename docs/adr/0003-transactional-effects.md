# ADR-0003: Transactional effects and audit

- Status: Accepted for the initial prototype
- Date: 2026-11-08

## Context

Authorization can change after a supervisor decision. An audit trail written separately from an effect can describe a state that never committed.

## Decision

Use SQLite as the authoritative state. Inside one short `BEGIN IMMEDIATE` transaction, read current policy, validate the stored decision and its evidence, create at most one release, and append the outcome event. Enforce uniqueness at the database level. Record denials as attempts, never as effects. Decisions, attempts, and effects have separate identifiers. Export only committed state; do not dual-write the database and JSONL as independent authorities.

## Alternatives

Check-then-write outside a transaction permits races. A filesystem release plus a database event is not one atomic effect. A future external publisher requires a transactional outbox and recovery protocol.

## Consequences

Concurrent duplicate execution cannot create a second effect. Attestations may remain reusable; effect idempotency does not make every receipt a one-use token. Model calls must stay outside transactions.

## Validation

Revocation between decision and execution blocks the effect. Duplicate/concurrent attempts create exactly one release. A failing audit insertion rolls back the release.
