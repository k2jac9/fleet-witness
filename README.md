# Fleet Witness

Evidence and accountability for AI agent fleets: a runnable local demonstration of how genuine evidence can still be insufficient to authorize an action. A deterministic supervisor proposes releases; a trusted controller checks receipt applicability and current policy before committing a local release and its audit event together.

Alejandro Castellanos (`k2jac9`) is the sole human owner and entrant. AI agents assisted implementation and review as development tools. The simulated fleet under evaluation is a separate controlled system. See [AI assistance and provenance](docs/AI_ASSISTANCE.md) and [submission requirements and official sources](docs/SUBMISSION.md).

The current pilot includes a 32-seed scripted campaign, offline provider-accounting fixtures, four successfully exercised GCP workers, and an authenticated managed dashboard. Real-model calibration has not run. See the [current gate inventory](docs/GATES.md), [research report draft](docs/research-report.md), and [runtime adoption record](docs/RUNTIME_ADOPTION.md).

## Clone, test, and run

Use current stable Python and Node versions from [the runtime matrix](ci/runtime-matrix.json), plus Git, on Linux/POSIX. Python 3.11+ and Node 24 remain supported consumers. The runtime and Python tests use only the standard library; Node runs the viewer-logic tests. No model account, package installation, cloud service, or external spend is needed. The repository contains the code, pinned Nix environment, architecture decisions, and operating instructions needed to continue from a fresh clone.

```sh
git clone https://github.com/k2jac9/fleet-witness.git
cd fleet-witness
python3 -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
python3 -m fleet_witness demo --output runs/demo --seed 42
python3 -m fleet_witness serve --directory runs/demo --port 8765
```

Open `http://127.0.0.1:8765` in a browser, then stop serving with Ctrl-C. The demo creates a SQLite database, `replay.json`, and browser assets in a fresh output directory. It refuses to overwrite an existing database; use a different `--output` directory for a second run. Serving is loopback-only by default, read-only, and exposes an asset allowlist. The implementation uses POSIX file-descriptor APIs; Windows serving is not supported by this slice. Browser assets have no CDN, telemetry, or build step.

The dashboard lets you inspect a decision, its evidence and receipt scope, the execution outcome, and ordered audit events. Filter and compare the paired presentations to follow where a supervisor's recommendation diverges from controller enforcement. Replay strings are displayed as text.

For a pinned Linux development environment with Nix and flakes enabled:

```sh
nix develop
# The shell provides Python, Node, and Git; run the same commands above.
```

## Handbook

| Goal | Instructions |
| --- | --- |
| Continue development from a fresh clone | [Development](docs/DEVELOPMENT.md), [contributing](CONTRIBUTING.md), [agent contract](AGENTS.md) |
| Run tests and understand their evidence | [Testing](docs/TESTING.md), [observed build status](docs/BUILD_STATUS.md) |
| Understand the design and trust boundaries | [Architecture](docs/architecture.md), [ADRs](docs/adr/README.md) |
| Prepare reviewed development tasks | [Fleet workflow](fleet/README.md), [NixOS worker configuration and acceptance](docs/NIXOS_FLEET.md) |
| Build and deploy the implemented baseline on GCP | [Complete deployment runbook](docs/DEPLOY_GCP.md), [local configuration template](deploy/gcp.env.example) |
| Inspect services, collect output, recover, and clean up | [Operations](docs/OPERATIONS.md), [deployment lifecycle](docs/DEPLOY_GCP.md) |
| Plan the $1,500 Adaption balance and separate hosting bill | [Adaption API and credit plan](docs/ADAPTION.md), [cost model](docs/COSTS.md) |
| Apply cybersecurity and research policy | [Security and policy](docs/SECURITY_POLICY.md), [resource map](docs/RESOURCES.md) |
| Prepare the solo research submission | [Roadmap](docs/ROADMAP.md), [submission guide](docs/SUBMISSION.md), [AI assistance](docs/AI_ASSISTANCE.md) |

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
| [0009](docs/adr/0009-gcp-deployment.md) | Native GCP image, private administration, optional HTTPS, and deployment lifecycle |
| [0010](docs/adr/0010-trusted-live-model-gateway.md) | Trusted live-model gateway design; paid activation remains gated |
| [0011](docs/adr/0011-managed-read-only-dashboard.md) | Separate authenticated managed replay dashboard |

## Develop through reviewed tasks

```sh
python scripts/fleet.py validate
python scripts/fleet.py plan
# Prepare only a task reported ready by the plan:
# python scripts/fleet.py prepare TASK_ID
```

The implemented tool validates a local task DAG, computes readiness, and prepares a dedicated branch/worktree plus ignored task brief. It rejects blocked tasks, unsafe paths, overlapping ready-task ownership, and existing task artifacts. It does not run acceptance commands, models, or containers. Manual `done` status is scheduling metadata; review the exact commit and real test evidence before integration. See the [fleet guide](fleet/README.md).

The optional [NixOS fleet configuration](docs/NIXOS_FLEET.md) defines ephemeral containers with an unprivileged offline task, immutable source snapshots, resource limits, and bounded output collection. The GCP host declares four manually started workers. Each runs the same offline verification script; their names do not dispatch coding agents. Worktree preparation supplies the change boundary. A mediated provider/tool gateway and automatic coding-worker dispatch remain future work.

## Deploy the implemented baseline

The committed flake exports a hosted scripted demo and a native NixOS GCP image:

```sh
nix flake check --no-build
nix build .#checks.x86_64-linux.offline-tests
nix build .#packages.x86_64-linux.demo
# Full image construction requires an x86_64 Linux builder with usable KVM.
nix build .#nixosConfigurations.fleet-gcp.config.system.build.googleComputeImage
```

Follow [DEPLOY_GCP.md](docs/DEPLOY_GCP.md) for prerequisites, private image upload, IAM, IAP/OS Login, VM creation, access, optional DNS/HTTPS, verification, updates, rollback, and teardown. The default host serves the read-only replay on loopback, keeps workers offline, and has no attached workload service account in the documented provisioning command. Public HTTPS is an explicit configuration option. Provider keys never belong in a flake, image, or worker.

**Observed:** Native image construction, GCP boot, IAP/OS Login, all four offline workers and a separate authenticated Cloud Run dashboard have executed. The NixOS VM is stopped. Remaining confinement, recovery, runtime-migration and cost gates stay open. [BUILD_STATUS.md](docs/BUILD_STATUS.md) records these separately. Scenario outcomes are reproducible; generated timestamps and fresh synthetic signatures make replay bytes vary between builds.

## Current limits and next work

See [the build verification record](docs/BUILD_STATUS.md) for observed test results and pending host/browser acceptance.

The baseline uses synthetic evidence, in-process HMAC signing, SQLite, and a scripted supervisor. It does not measure real model performance, detect a live swarm, provide independent notarization, or establish containment of compromised operating-system processes. Containers share a kernel; bounded passing probes do not close all host acceptance. The authenticated dashboard serves synthetic assets and has a scheduled expiry. A production provider transport/authorization boundary, paid calibration, unattended coding dispatch, public honeypot, and global fleet map remain gated work.

The [roadmap](docs/ROADMAP.md) prioritizes independent review, expanded scenarios, a bounded adapter proposal, and a reproducible research report. [Submission preparation](docs/SUBMISSION.md) links the current official rules and tracks remaining report work; repository preparation is not event submission. Original code is available under the [MIT license](LICENSE).
