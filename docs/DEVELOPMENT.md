# Development

Fleet Witness's default path is a local, scripted fixture demonstration with zero
external spend. Begin with a reviewed commit and an isolated task worktree;
[CONTRIBUTING](../CONTRIBUTING.md) describes ownership and review. Read
[AGENTS.md](../AGENTS.md), [architecture](architecture.md), and the
[accepted ADRs](adr/README.md) before changing behavior.

## Fresh clone and prerequisites

Use Linux/POSIX, Git, and the current stable Python/Node selections in
[the runtime matrix](../ci/runtime-matrix.json). Python 3.11+ and Node 24 remain
supported consumers. The optional Nix environment below retains its older lock
pending a separately verified migration. The viewer server uses POSIX
file-descriptor APIs; native Windows serving is unsupported. Python runtime and
tests use the standard library; browser assets need no npm install or build step.
Git is required for the full Python suite, even if only testing the application.

```sh
git clone https://github.com/k2jac9/fleet-witness.git
cd fleet-witness
python3 --version
node --version
git --version
git rev-parse HEAD
git status --short
python3 -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
```

Examples use `python3`. If your environment provides it as `python`, use that
executable consistently after checking its version. No virtual environment or dependency installation is
required. Keep credentials, private configuration, and generated runs out of Git.

## Generate and inspect a fixture

Choose a fresh output directory for each run. From a primary checkout, this
example retains artifacts in a sibling directory. In a task worktree, set
`artifact_root` to the project's existing artifact directory instead:

```sh
artifact_root="../fleet-witness-artifacts"
mkdir -p "$artifact_root"
run_root=$(mktemp -d "$artifact_root/demo.XXXXXXXX")
python3 -m fleet_witness demo --output "$run_root/demo" --seed 42
python3 -m fleet_witness serve --directory "$run_root/demo" --port 8765
```

Open `http://127.0.0.1:8765`, then stop with Ctrl-C. The demo produces
`witness.sqlite3`, `replay.json`, `index.html`, `app.js`, and `styles.css`.
An existing database is refused, including a symlink; select another output
rather than deleting prior evidence. Serving exposes only the allowlisted replay
and browser assets, never the database. See [testing](TESTING.md) for counts,
HTTP checks, and the separate manual visual checklist.

`scripted-demo` uses deterministic policies, synthetic evidence, and local database
release records. It calls no model and provides no empirical model-performance
result. A seed reproduces scenario identities and outcomes, not identical HMAC
signatures: each invocation creates a new signing key. The key is not persisted;
a saved database supports historical inspection, not resumed execution.

## Optional Nix development

Install Nix using the [official instructions](https://nix.dev/install-nix), open
a new terminal, and check `nix --version`. This flake provides Linux outputs;
use a Linux environment or builder for them. If flakes are not enabled in your
Nix configuration, use `nix --extra-experimental-features 'nix-command flakes'`
in place of `nix` in each command below. For example:

```sh
nix --extra-experimental-features 'nix-command flakes' develop
```

On a Nix host with flakes enabled, use the committed `flake.lock` and inspect any
intentional pin/lock change. Fresh clones already include the resolved source
hash; no lock-generation step is needed. Fetching dependencies may require
network access. See [NixOS fleet setup](NIXOS_FLEET.md) for host acceptance.

```sh
nix develop --command python3 -m unittest discover -s tests -v
nix develop --command node --test tests/viewer.test.mjs
nix build .#checks.x86_64-linux.offline-tests
nix build .#packages.x86_64-linux.demo
```

These are optional evaluation/build steps, not proof of a booted worker or GCP
deployment. Add and commit reviewed source files before Git-backed flake builds:
untracked files are excluded. The worker snapshot also filters paths; inspect
[NIXOS_FLEET](NIXOS_FLEET.md) before assuming local files enter a worker image.

## Prepare a development task

From a clean tracked checkout, validate the DAG and inspect ready tasks:

```sh
python3 scripts/fleet.py validate
python3 scripts/fleet.py plan
```

Choose a ready task from the current plan, then run
`python3 scripts/fleet.py prepare TASK_ID`, replacing `TASK_ID` with its exact ID.
Preparation creates `fleet/TASK_ID`, `.worktrees/TASK_ID` and an ignored
`.fleet/brief.md` inside that worktree. It runs no acceptance command, model or
container. If no task is ready, define and review the next scoped task before
preparing it. Follow its owned paths; the owner updates scheduling status only
after reviewing actual evidence. Do not replay a completed starter task.

All fleet commands refuse effective executable Git clean/smudge/process filters,
including Git LFS configuration, and conditional includes. This is intentional,
even when current attributes do not select a filter. Inspect matching names with
`git config --includes --name-only --get-regexp '^(filter\..*\.(clean|smudge|process)|includeif\..*\.path)$'`.
Do not rewrite a developer's global Git configuration to bypass refusal. Use an
operator-reviewed development environment without those executable settings, or
report the incompatibility. The [fleet guide](../fleet/README.md) explains the
full refusal contract and exact-root `--root` option.

Worktrees separate edits, not hostile processes. The optional NixOS workers run
offline tests and a fixture demo; their names do not dispatch coding agents.
[Operations](OPERATIONS.md) covers those workers; [GCP deployment](DEPLOY_GCP.md)
covers host provisioning. The opt-in [controlled pilot](CONTROLLED_PILOT.md) has
its own provider and spending boundary; [Adaption](ADAPTION.md) remains a separate
qualification path. [Costs](COSTS.md) records budget distinctions.
