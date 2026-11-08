# Development

Fleet Witness's default path is a local, scripted fixture demonstration with zero
external spend. Begin with a reviewed commit and an isolated task worktree;
[CONTRIBUTING](../CONTRIBUTING.md) describes ownership and review. Read
[AGENTS.md](../AGENTS.md), [architecture](architecture.md), and the
[accepted ADRs](adr/README.md) before changing behavior.

## Fresh clone and prerequisites

Use Linux/POSIX, Git, and the current stable Python/Node candidates in
[the runtime matrix](../ci/runtime-matrix.json). Python 3.11+ and Node 24 remain
supported consumers. The optional Nix environment below retains its older lock
pending a separately verified migration. The viewer server uses POSIX
file-descriptor APIs; native Windows serving is unsupported. Python runtime and
tests use the standard library; browser assets need no npm install or build step.
Git is required for the full Python suite, even if only testing the application.

```sh
git clone https://github.com/k2jac9/fleet-witness.git
cd fleet-witness
python --version
node --version
git --version
git rev-parse HEAD
git status --short
python -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
```

If your system names Python `python3`, use that executable consistently after
checking its version. No virtual environment or dependency installation is
required. Keep credentials, private configuration, and generated runs out of Git.

## Generate and inspect a fixture

Choose a fresh output directory for each run. This example keeps artifacts outside
the checkout and preserves them for inspection:

```sh
run_root=$(mktemp -d "${TMPDIR:-/tmp}/fleet-demo.XXXXXXXX")
python -m fleet_witness demo --output "$run_root/demo" --seed 42
python -m fleet_witness serve --directory "$run_root/demo" --port 8765
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
nix develop --command python -m unittest discover -s tests -v
nix develop --command node --test tests/viewer.test.mjs
nix build .#checks.x86_64-linux.offline-tests
nix build .#packages.x86_64-linux.demo
```

These are optional evaluation/build steps, not proof of a booted worker or GCP
deployment. Add and commit reviewed source files before Git-backed flake builds:
untracked files are excluded. The worker snapshot also filters paths; inspect
[NIXOS_FLEET](NIXOS_FLEET.md) before assuming local files enter a worker image.

## Prepare a development task

From a clean tracked checkout, validate the DAG and prepare a ready task:

```sh
python scripts/fleet.py validate
python scripts/fleet.py plan
python scripts/fleet.py prepare adapter-proposal
cd .worktrees/adapter-proposal
cat .fleet/brief.md
```

The initial plan has `adapter-proposal` and `expanded-scenarios` ready; report and
review tasks remain blocked until their dependencies are marked done. Preparation
creates branch `fleet/adapter-proposal` from the current HEAD and an ignored brief.
It runs no acceptance command, model, or container. Follow the brief's owned paths;
the owner updates scheduling status only after reviewing actual evidence.

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
covers host provisioning. Future live providers and their spending boundary are
separate work in [Adaption](ADAPTION.md) and [costs](COSTS.md).
