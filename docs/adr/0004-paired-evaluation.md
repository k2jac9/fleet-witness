# ADR-0004: Paired evidence and independent evaluation

- Status: Accepted for the initial prototype
- Date: 2026-11-08

## Context

A controller can mask unsafe supervisor recommendations. A presentation comparison is confounded if one condition receives different evidence.

## Decision

Run a 2 x 2 honest/adversarial worker-reviewer matrix. Reuse the underlying trajectory and facts for raw and scope-explicit presentations. Label the deterministic supervisor as an illustrative baseline. Capture immutable decision inputs and policy. Score decision validity against decision-time truth independently from the authorization at execution and the actual effect. Preserve correct refusals and incorrect refusals as well as approvals.

## Alternatives

Scoring only released artifacts hides bad decisions. Rescoring a past recommendation against current policy incorrectly penalizes legitimate decisions followed by revocation. More informative evidence is an information intervention and must be labeled separately.

## Consequences

Baseline counts are software checks, not model findings or statistical claims. A real experiment needs frozen prompts/models, repeated trials, budget limits, and predeclared analysis before sponsor credits are used.

## Validation

Paired episodes expose equal underlying facts. The evaluator does not call the gate's policy evaluator. Revocation preserves a valid decision score while denying execution. Identical seeds reproduce scenario identities and outcomes.
