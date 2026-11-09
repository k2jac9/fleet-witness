# Swarm stabilization design

The owner approved the six-step stabilization recommendation with "let's do it"
on 2026-11-09. This records that approved scope and the implementation choices
needed to execute it; it is not a replacement for an accepted ADR.

Keep `feat/live-swarm` at its original reviewed head and implement on
`fix/swarm-stabilization-20261109`, based on
`6061cb20f39ac19fcc95b09303e02ebcd43a9887`. Preserve the historical ZIP, AI review
records and original experiment outputs. Defaults remain offline and free.

1. Replace per-tag JSON accounting with a private transactional SQLite ledger,
   fixed-point USD units, shared provider limits, per-run limits, durable request
   reservations and atomic audit records. Tags are metadata. Existing JSON
   ledgers block silent initialization until an operator reconciles them; do not
   read or migrate the owner's real ledger during development. Unknown charges
   retain reservations and halt dispatch; known overruns retain the larger liability.
2. Disable automatic retries, including rate-limit retries. Use one attempt per
   logical call and one in-flight paid request. Bound inputs, outputs and timeouts;
   disallow redirects/proxy inheritance and protected request-field overrides.
   Paid activation requires a source-bound operator record with verified pricing,
   units, provider/model, canonical ledger, request-count and expiry limits.
   Lack of qualification must fail before credentials or network are accessed.
   No record is created to authorize actual spending as part of offline tests.
3. Retain each request/response attempt privately, with hashes, bounded raw content,
   usage, status, cost and provider ID. Public detector events must not expose
   private colluder prompts, sealed truth or credentials. Manifests distinguish
   logical outcomes from provider attempts, settled costs and unresolved holds,
   and include executable source/runtime/configuration provenance.
4. Add safe portable extraction of the immutable Windows-path ZIP, rejecting path
   traversal, links, collisions, excessive growth and overwrites. Reconstruct
   synthetic receipt cases with fresh keys and recorded vote totals, and execute
   the gated-majority control through the actual institution. Explicitly label
   this reconstructed replay: historical signing keys were never retained.
   Allow zero committee/quorum only with required majority. Derive denominators,
   refuse incomplete/inconsistent inputs, and omit invalid pooled confidence
   intervals. Encode undefined statistics as JSON null.
5. Correct manuscript encoding, causal figure titles, conventional medians and
   evidence/cost/provenance descriptions. Regenerate current artifacts, preserving
   original raw data/reviews and documenting the new artifact identities.
6. Verify failing regressions before fixes, full Python/Node suites, complete
   offline reproduction and independent review. Merge only the exact reviewed
   candidate with successful CI. Paid canaries and public-web observation retain
   their separate qualification gates; local success does not close them.

Use Python 3.11+ standard library and existing static viewer contracts. Do not
alter accepted ADRs, cloud resources, credentials, historical receipts or budget
authority. The $100 GCP envelope remains separate from provider credits.

Task ownership: core provider/ledger, reproduction/kernel baseline, and parent
runner/provenance/publication each own disjoint paths in isolated worktrees.
Workers may commit only their owned changes; the parent reviews and integrates.
