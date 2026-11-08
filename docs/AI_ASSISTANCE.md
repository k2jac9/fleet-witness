# Human ownership and AI assistance

## Human team

| Member | Project role | Publication details |
| --- | --- | --- |
| Alejandro Castellanos (`k2jac9`) | Repository owner and teammate | Affiliation to be confirmed |
| [`IPBin`](https://github.com/IPBin) | Teammate, confirmed by the owner on 2026-11-08 | Preferred author name and affiliation to be confirmed |

The project began as Alejandro's solo effort. The owner confirmed IPBin's team
membership on 2026-11-08; [ADR-0012](adr/0012-human-team-membership.md) records that
change. Earlier plans, reviews and accepted decisions retain their historical
wording. Record each member's actual contributions before finalizing the report's
author list, order and affiliations; membership does not retroactively attribute
the earlier implementation or experiments to IPBin.

AI assistants were used to research architectural options, draft ADRs, implement code, generate tests, review changes, and inspect the demo. They are development tools, not additional human entrants. The human team reviews submission accuracy and contribution attribution; Alejandro remains the repository owner and integration authority.

The runtime's initial `scripted-demo` backend uses deterministic policies. Its traces are synthetic examples and its metrics are software verification outputs. They are not measurements of Adaption or any other language model. No model credits are consumed by the baseline.

The repository was created on 2026-11-08. Earlier conceptual research informed the design; the initial implementation is new work for this repository. No source from the earlier `swarms` planning repository is copied as implemented runtime code. Imported third-party code, datasets, or pre-sprint work must be identified here and in any final report before inclusion.

This disclosure is a project practice. Check the current event rules and submission template for the exact required declarations.

The 2026-11-08 deployment handoff also used AI assistance to implement the native
NixOS/GCP configuration and packaged demo, write development and operating guides,
check primary platform documentation and cost arithmetic, and independently
review the integrated change. Verification included a fresh clone, local tests,
Nix evaluation/package builds, and real HTTP checks. Full image construction,
cloud boot, worker containment, live models, and submission remain separate
unexecuted steps as recorded in [BUILD_STATUS.md](BUILD_STATUS.md). The
`dreamsofcode-io/nixos-vps` repository informed platform comparisons; no source
from it was copied into this handoff.
