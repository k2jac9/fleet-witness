# Fleet Witness

Evidence and accountability for AI agent fleets: a runnable local demonstration of how genuine evidence can still be insufficient to authorize an action. A deterministic supervisor proposes releases; a trusted controller checks receipt applicability and current policy before committing a local release and its audit event together.

Alejandro Castellanos (`k2jac9`) is the sole human owner and entrant. AI agents assisted implementation and review as development tools. The simulated fleet under evaluation is a separate controlled system. See [AI assistance and provenance](docs/AI_ASSISTANCE.md) and [submission requirements and official sources](docs/SUBMISSION.md).

## Run the implemented baseline

Use Python 3.11+ on Linux/POSIX. The runtime and Python tests use only the standard library. Git is required for every fleet command and the full Python test suite; Node 24 runs the optional browser-logic tests. No model account, package installation, cloud service, or external spend is needed.

```sh
python -m unittest discover -s tests -v
python -m fleet_witness demo --output runs/demo --seed 42
python -m fleet_witness serve --directory runs/demo --port 8765
```

Open `http://127.0.0.1:8765` in a browser, then stop serving with Ctrl-C. The demo creates a SQLite database, `replay.json`, and browser assets in a fresh output directory. It refuses to overwrite an existing database; use a different `--output` directory for a second run. Serving is loopback-only by default, read-only, and exposes an asset allowlist. The implementation uses POSIX file-descriptor APIs; Windows serving is not supported by this slice. Browser assets have no CDN, telemetry, or build step.

The dashboard lets you inspect a decision, its evidence and receipt scope, the execution outcome, and ordered audit events. Filter and compare the paired presentations to follow where a supervisor's recommendation diverges from controller enforcement. Replay strings are displayed as text.

For browser-logic verification:

```sh
node --test tests/viewer.test.mjs
```

## Interpret the demo

Every run is labeled `scripted-demo`. The honest/adversarial worker and reviewer combinations reuse one underlying trajectory across `raw` and `scope_explicit` evidence presentations, with the same facts. Each presentation has its own isolated trial state. Additional scenarios exercise forged evidence, wrong artifact or run, missing policy, revocation after approval, and duplicate execution.

Three outcomes answer different questions: `decision_valid_at_snapshot` judges the recommendation against policy at decision time; `execution_authorized_at_attempt` records authorization when the controller attempts the effect; `effect_occurred` records the actual committed release. A valid approval can be followed by revoked permission and a denied execution. An invalid approval remains invalid even when the controller blocks it. An already completed authorized execution is a no-op, so it creates neither a duplicate release nor an authorization denial. `denied_attempts` counts authorization failures.

A genuine build receipt does not establish release safety, and a reusable attestation is not an authorization token. The controller verifies receipt integrity, exact issuer and claim, artifact, scope, and run applicability. It rechecks current authorization inside the same SQLite transaction that commits the release and audit event. Database uniqueness bounds a run/artifact to one release in each isolated trial.

These traces demonstrate mechanisms. Differences between deterministic scripted presentations are illustrative and provide no empirical evidence that a prompt improves a real model. The local effect is a database row. Saved databases are historical inspection artifacts; the in-memory HMAC key is deliberately not persisted, and there is no resume command.

## Architecture and accepted decisions

[Architecture](docs/architecture.md) defines the controller, independent evaluator, replay schema, and trust boundaries. Scenario truth and issuer keys stay outside supervisor-visible inputs. Exported replays include evaluator results for human inspection and are not future agent inputs.

| ADR | Contract |
| --- | --- |
| [0001](docs/adr/0001-local-evaluation-slice.md) | Dependency-free local evaluation slice |
| [0002](docs/adr/0002-evidence-and-authority.md) | Evidence, applicability, and authorization are separate checks |
| [0003](docs/adr/0003-transactional-effects.md) | Transactional release and audit effects |
| [0004](docs/adr/0004-paired-evaluation.md) | Paired evidence and independent evaluation |
| [0005](docs/adr/0005-replay-and-viewer.md) | Versioned replay and read-only viewer |
| [0006](docs/adr/0006-development-fleet.md) | Task DAG, owned paths, isolated branches, and owner integration |
| [0007](docs/adr/0007-isolated-paired-trials.md) | Independent counterfactual trial state |
| [0008](docs/adr/0008-ephemeral-nixos-workers.md) | Optional ephemeral NixOS workers; boot validation pending |

## Develop through reviewed tasks

```sh
python scripts/fleet.py validate
python scripts/fleet.py plan
python scripts/fleet.py prepare adapter-proposal
```

The implemented tool validates a local task DAG, computes readiness, and prepares a dedicated branch/worktree plus ignored task brief. It rejects blocked tasks, unsafe paths, overlapping ready-task ownership, and existing task artifacts. It does not run acceptance commands, models, or containers. Manual `done` status is scheduling metadata; review the exact commit and real test evidence before integration. See the [fleet guide](fleet/README.md).

The optional [NixOS fleet configuration](docs/NIXOS_FLEET.md) targets ephemeral containers with an unprivileged offline task, source snapshots, resource limits, and explicit output collection. Nix is unavailable in this build environment: configuration and static review are supplied, while Nix evaluation, building, booting, and containment validation remain pending. It is not a deployed coding fleet. A mediated provider/tool gateway and automatic coding-worker dispatch are future decisions. Worktree preparation supplies a reviewable change boundary; the Nix configuration supplies a separately validated worker environment.

## Current limits and next work

See [the build verification record](docs/BUILD_STATUS.md) for observed test results and pending host/browser acceptance.

The baseline uses synthetic evidence, in-process HMAC signing, SQLite, and a scripted supervisor. It does not measure real model performance, detect a live swarm, provide independent notarization, publish artifacts externally, or establish containment of compromised operating-system processes. Containers share a kernel; their configured restrictions need host validation. No paid runner, credentials gateway, unattended merge path, or cloud deployment is implemented.

The [roadmap](docs/ROADMAP.md) prioritizes independent review, expanded scenarios, a bounded adapter proposal, and a reproducible research report. [Submission preparation](docs/SUBMISSION.md) links the current official rules and tracks remaining report work; repository preparation is not event submission. Original code is available under the [MIT license](LICENSE).
