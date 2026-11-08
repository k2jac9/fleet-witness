# Offline Fake Gateway Receipts Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution, with an independent diff review before owner integration.

**Goal:** Preserve fake gateway input and outcome atomically so a result survives a caller crash.

**Architecture:** Add an additive receipt table in the private SQLite ledger. Reservation saves the validated visible input; settlement or unresolved handling saves a bounded result with its existing state and audit transition. Reopening provides read-only lookup; legacy rows receive no invented data.

**Tech Stack:** Python 3.11+, SQLite, unittest; no provider SDK or network access.

**Spec:** `docs/superpowers/specs/2026-11-08-offline-receipts-design.md`

## Global Constraints

Fake mode only; preserve existing reservation, hold, duplicate-ID, controller and scripted replay boundaries. Store no raw exception text. Preserve legacy ledgers and their unresolved requests. Retain all failure evidence.

## Review Focus

- Mutation after submission: test persisted input equals the validated snapshot.
- Crash after settlement: test result is readable after reopening and ID cannot be reused.
- Transaction failure: abort receipt or audit write and verify state and hold roll back together.
- Malformed or oversized fake output: test no unbounded or invalid UTF-8 text is persisted, and outcomes remain classified.
- Existing ledger with unresolved request: reopen and verify migration leaves its hold and status unchanged with no invented receipt.

## Task: durable fake receipts

**Files:** Modify `fleet_witness/gateway.py`; modify `tests/test_gateway.py`; design and plan above.

**Interfaces:** `BudgetLedger.receipt(request_id: str) -> dict | None` reads a detached record with `request_id`, `mode`, `model_input`, `max_output_tokens`, `raw_output` and `result`. `Gateway.run(...)` retains its existing signature and result shape. Internal reservation and settlement may carry the payload/result as keyword-only arguments; direct legacy ledger callers remain compatible.

- [x] Add focused behavioral tests for all five review-focus cases, plus unresolved provider error and duplicate-ID behavior; prove the tests fail against the current gateway for missing receipts.
- [x] Implement an additive receipt schema and atomic reservation, outcome and audit writes. Preserve the full hold when the outcome transaction fails. Reject or omit unsafe raw output as specified; never serialize exception messages.
- [x] Run `python3 -m unittest discover -s tests -p test_gateway.py -v` and the full `python3 -m unittest discover -s tests -v`; run `node --test tests/viewer.test.mjs`, `python3 scripts/fleet.py validate`, and `git diff --check`.
- [x] Have an independent reviewer inspect the diff, migration and tests; fix concrete findings with failing tests first.
The exact commit identity is recorded in the task handoff after the commit is created.

Observed: focused regressions were run red then green; the final terminal run passed 85 Python tests, five viewer tests, fleet validation and diff checks. Independent review found no remaining material code defect. Crash checks do not demonstrate power-loss recovery. The GCP image predates this change.
