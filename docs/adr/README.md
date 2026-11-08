# Architectural decision records

Accepted decisions are the development fleet's contract. Propose changes in a new numbered record; preserve earlier records and mark them superseded only when the owner accepts the replacement. Each record states status, context, decision, consequences, alternatives, and validation.

| ADR | Decision |
| --- | --- |
| [0001](0001-local-evaluation-slice.md) | Dependency-free local evaluation slice |
| [0002](0002-evidence-and-authority.md) | Separate evidence, authority, and trust boundaries |
| [0003](0003-transactional-effects.md) | Transactional effects and audit |
| [0004](0004-paired-evaluation.md) | Paired evidence and independent evaluation |
| [0005](0005-replay-and-viewer.md) | Versioned replay and read-only viewer |
| [0006](0006-development-fleet.md) | ADR-governed development fleet for a solo entrant |
| [0007](0007-isolated-paired-trials.md) | Isolated counterfactual worlds for paired trials |
| [0008](0008-ephemeral-nixos-workers.md) | Ephemeral NixOS development workers; deployment validation pending |
| [0009](0009-gcp-deployment.md) | Native GCP image, private administration, optional HTTPS, and deployment lifecycle |
| [0010](0010-trusted-live-model-gateway.md) | Trusted live-model gateway and bounded pilot; implementation and validation pending |

| [0011](0011-managed-read-only-dashboard.md) | Authenticated managed static dashboard; deployment validation recorded separately |

Use [the template](template.md) for a new proposal.
