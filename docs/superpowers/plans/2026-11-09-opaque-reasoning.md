# Opaque reasoning compatibility and failed-cohort accounting

Task `opaque-reasoning-20261109`; base `92754a906aa6618034abd5b3886800550a4c67ed`.
The owner delegated improvements from observed experiments and green integration.
The first 160-call cohort stopped after one response contained documented Azure
opaque reasoning metadata despite `reasoning.exclude=true`. No decision or effect
was committed; 159 calls remain unstarted. Preserve that cohort and its original
report, receipt, response bytes, closed claim and authorization unchanged.

Owned paths: `fleet_witness/swarm/openrouter_controlled.py`,
`fleet_witness/pilot_store.py`, `tests/test_openrouter_controlled.py`,
`tests/test_controlled_pilot.py`, `docs/BUILD_STATUS.md`, `docs/CONTROLLED_PILOT.md`,
this plan. Operator artifacts/scripts only under the parent task packet's
`iteration-reasoning/` directory. Accepted ADRs and frozen prompts are unchanged.

1. Reproduce encrypted-details rejection with synthetic transport. Accept only
   bounded encrypted metadata for reviewed Azure route/model: one object with
   exactly type/data/format/id/index, type reasoning.encrypted, Azure format,
   rs_ identifier, integer zero index and nonempty bounded URL-safe opaque data.
   Never decrypt, interpret, replay, include in proposals or use as authority.
   Plaintext reasoning, summaries, tools, unknown fields/formats and malformed
   usage remain refused. Keep combined 256-token ceiling, no retries and costs.
2. Reconcile the failed request using response usage, generation and key delta.
   Actual charge $0.0016104; 287 input/89 output including 28 reasoning; conservative
   accounting $0.00176825. Independently review a guarded operator transaction,
   backup first, retain original bytes/receipt and append an atomic reconciliation
   audit entry. The cohort remains failed and closed; no resume or replacement
   call within it. Add export support for that explicit audit-linked terminal
   accounting status so later read-only recovery preserves both old failure
   receipt and reconciled amounts. Reject unlinked status/amount alterations.
3. Full Python/viewer tests, independent diff/operator-script review, exact-source
   hosted matrix and green integration. Then a newly source-bound one-call
   calibration, read-only account reconciliation, and one separately frozen
   exploratory cohort with unchanged prompts/design and fresh opaque IDs. Earlier
   failed data stays excluded and separately reported. Shared provider cap $50,
   run cap $15, GCP $100 separate and unused by this work; no Adaption calls.

Primary documentation reviewed November 9:
https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
Documents encrypted reasoning_details, Azure format and combined output billing.
The exclusion discrepancy is observed, not explained away: a request flag is not
proof that the provider returned no opaque metadata. This change tolerates the
strict opaque form as inert data without expanding model authority or retention
claims. Raw encrypted bytes remain in private response evidence only.
