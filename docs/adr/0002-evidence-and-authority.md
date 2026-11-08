# ADR-0002: Separate evidence from authority

- Status: Accepted for the initial prototype
- Date: 2026-11-08

## Context

A receipt may be authentic while proving an irrelevant or insufficient fact. An agent's convincing explanation cannot grant permission.

## Decision

Keep three checks separate: authentic issuer/content, claim applicability to artifact/scope/run, and current authority to execute. A local HMAC establishes prototype receipt integrity using a controller-held key. Check issuer, claim, artifact digest, scope, and run. A build receipt cannot satisfy a release-safety requirement. The supervisor proposes; the controller authorizes. Inputs are built by allowlist and exclude signing keys and privileged scenario truth.

## Alternatives

Trusting signatures alone ignores applicability. Letting the supervisor execute directly removes independent enforcement. An external identity/notary service is unnecessary for this local slice.

## Consequences

HMAC is not public verifiability or protection from a compromised controller. In-process agents are logical roles, not an operating-system security boundary. Reviewer assertions are untrusted evidence.

## Validation

Forgery, wrong artifact, wrong run, insufficient claim, missing policy, and revoked authorization produce denials; a valid in-scope release succeeds. Serialized supervisor inputs exclude privileged fields.
