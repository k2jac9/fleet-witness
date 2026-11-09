# Runtime adoption and retained baseline

Owner: Alejandro Castellanos. Repository: k2jac9/fleet-witness. The matrix is
integrated on `main`. Selections verified 2026-11-08; review due 2026-11-15 and
before a new runtime activation. These are the recorded selections, not a fresh
upstream release query. Machine-readable source is
[`ci/runtime-matrix.json`](../ci/runtime-matrix.json).

| Runtime | Latest stable | Upcoming, isolated | Previous supported stable | Additional retained checks |
| --- | --- | --- | --- | --- |
| Python | 3.15.2 | 3.16.0a1 | 3.14.10 | Promised 3.11.18, 3.12.16, 3.13.18; retained-host compatibility 3.13.17 |
| Node | 26.13.0 | 27.0.0-alpha.0.0.0 | 24.22.2 | Retained viewer compatibility 24.22.1 |

Sources: [Python releases](https://www.python.org/downloads/),
[Python preview](https://www.python.org/downloads/release/python-3160a1/),
[GitHub's Python build releases](https://github.com/actions/python-versions/releases),
[Node releases](https://nodejs.org/dist/index.json), and
[Node support schedule](https://github.com/nodejs/Release/blob/main/schedule.json).
Node 25's support ended before this selection, so Node 24 is the previous
supported line. Python 3.11+ and Node 24 consumers remain supported.

The workflow downloads exact Ubuntu 24.04 x64 Python build artifacts and official
Linux x64 Node archives, checks their pinned SHA-256 before extraction, and uses
isolated runtime directories. Python versions include the immutable Actions
build identity in their URL. Python archive digests came from release-asset API
metadata; Node digests came from each official SHASUMS256.txt. No floating tool
version or mutable artifact tag is accepted. CI verifies the selected version
against the actual executable, records its SHA-256, source commit, flake-lock
hash, matrix hash, OS/architecture and hosted runner image version, and uploads
logs for successful and failed jobs. Failed previews are visible; fail-fast is
false. The weekly schedule enforces the review interval but does not itself
re-query upstream or prove the selections remain newest: the technical owner
must refresh the official sources and exact pins.

Each Python lane runs the full standard-library suite, task validation/planning
and a real scripted demo. Each Node lane runs all viewer tests. This checks
runtime families independently; it is not every Python/Node Cartesian pairing.
Recorded results belong in BUILD_STATUS.md after actual workflow execution.
Configured lanes are not passing evidence. PR #13 subsequently passed all 11
lanes on tree `690d42c2f5ef77778b6a1ad3d599c2ea6aeb0ce8`: seven Python lanes
with 309 tests each and four Node lanes with five each, in
[run 42591134143](https://github.com/k2jac9/fleet-witness/actions/runs/42591134143).
That result qualifies that tree, not subsequent edits.

## Accepted deployment and rollback boundary

The last recorded Cloud Run Caddy 2.11.9 image is
`sha256:87b42722fd6f73995756f650690b11fcf97cb5528eb2043fe8b4bc654fa3957b`.
The NixOS VM was last recorded stopped, with its earlier image, source `857e716`, committed
nixpkgs lock `c56a87d8e41ce69bd2af57eb35dcc117a9dfca33` and observed Python
3.13.17. Preserve the exact images, GC roots, old lock, data and receipts. This
editorial pass does not refresh cloud inventory or prove retained-resource state.
Testing the same Python version in an Ubuntu artifact is compatibility evidence,
not a reproduction of the NixOS interpreter or acceptance of the stopped host.

No local workstation default, running service or Nix lock is promoted by this
documentation change. Stable is the normal development target, but a durable local Nix
migration, current Caddy/NixOS previous/preview matrices, security backport
review, cloud rollback exercise, cost reconciliation and applicable host
acceptance remain tracked gaps. Neither a newer Python interpreter nor its
version string alone qualifies the production TLS path. Promotion requires
source-bound required checks and recovery evidence; no rollback version or
older consumer has been retired.
