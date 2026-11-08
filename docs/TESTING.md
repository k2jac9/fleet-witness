# Testing and evidence

Run behavioral checks from the repository root with Python 3.11+, Git, and Node 24
on Linux/POSIX. No model account, cloud project, npm installation, or runtime
Python package is required. [Development](DEVELOPMENT.md) covers setup.

## Automated checks

```sh
python -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
python scripts/fleet.py validate
python scripts/fleet.py plan
git diff --check
```

The observed baseline is 49 Python tests and 5 Node tests. Record the exact commit,
versions, commands, exit codes, and real results when reporting a new run; counts
may change as meaningful coverage grows. A green planner is scheduling validation,
not evidence that task acceptance commands ran.

| Area | Behavioral coverage |
| --- | --- |
| Controller | Receipt integrity/applicability, current authorization, duplicates/concurrency, transactional audit rollback |
| Experiment/export | Independent decision scoring, paired facts and isolated trial state, real replay export |
| CLI/server | Existing-database refusal, allowlisted read-only serving, unsafe paths and writes denied |
| Fleet | DAG/ownership validation, preparation, dirty/existing artifacts and executable-filter refusal |
| Offline task | Fresh workspace requirement, success/failure propagation and result reports |
| Node viewer logic | Real producer replay import, validation/complexity limits, pairing, search and filtering |

Add tests for changed behavior and trust boundaries. For security-sensitive code,
first reproduce the failure with a failing behavioral test, then fix and run the
full Python suite. Documentation changes need exercised commands and link review;
tests that merely match document wording do not establish correctness.

## Full offline smoke

The same launcher used by the configured worker copies the source, runs Python
and available Node tests, then generates the scripted demo. Use a fresh checkout
without secrets; outside Nix this command copies the supplied source directory
without the Nix snapshot filter. Its shell requires Bash and `realpath`.

```sh
smoke_root=$(mktemp -d "${TMPDIR:-/tmp}/fleet-smoke.XXXXXXXX")
bash nix/offline-task.sh "$PWD" "$smoke_root/task"
cat "$smoke_root/task/results/report.txt"
cat "$smoke_root/task/results/demo.log"
```

Success requires process exit 0 and a report containing
`mode=offline-scripted-demo`, `stage=complete`, and `exit_code=0`. Inspect
`tests.log` and `viewer.log` as well; missing or partial reports are not success.
This local run verifies the task launcher, not Nix evaluation, cgroups, namespaces,
VM startup, or cloud access. Never reuse the task directory; choose a new parent
for another run. Preserve a failed run for diagnosis.

For seed 42, the current fixture produces:

| Metric | Expected |
| --- | ---: |
| Episodes | 20 |
| Approved recommendations | 13 |
| Invalid recommendations | 7 |
| Execution attempts | 15 |
| Committed effects | 4 |
| Denied attempts | 9 |
| Authorized duplicate attempts with no new effect | 2 |

The two duplicate no-ops are included in 15 attempts, but are neither effects nor
authorization denials. Score `decision_valid_at_snapshot` separately from
`execution_authorized_at_attempt` and `effect_occurred`: later revocation can deny
execution after a valid approval. Scripted differences between `raw` and
`scope_explicit` are illustrations, not empirical evidence about a real LLM.
Compare scenario facts and outcomes across runs, not byte-identical signatures.

## HTTP and manual browser acceptance

Serve the smoke replay with
`python -m fleet_witness serve --directory "$smoke_root/task/results/demo" --port 8765`.
The server tests cover responses and forbidden requests; a manual HTTP check can
also confirm `/`, `/replay.json`, `/app.js`, and `/styles.css` return 200 while
`/witness.sqlite3` returns 404. If port 8765 is occupied, use another port rather
than stopping an unknown process. Stop your own server with Ctrl-C.

Automated Node tests exercise data logic without a real browser. Visual appearance,
keyboard interaction, and responsive layout remain **visually unverified** until a
human or browser session performs and records this checklist:

- Open the real generated replay; confirm the scripted label and summary counts.
- Select scenarios and both presentations; compare receipt claim, scope, artifact,
  decision validity, attempt authorization, and actual effect.
- Search/filter; step ordered audit events and inspect the revocation/duplicate cases.
- Navigate selection and event controls with the keyboard and inspect visible focus.
- Inspect narrow and wide windows for readable text and reachable controls.
- Import malformed JSON and confirm a visible error; confirm markup-like replay
  strings display as text, without executing HTML.

## Deployment acceptance is separate

[NIXOS_FLEET](NIXOS_FLEET.md) owns required boot, cgroup, network, mount, timeout,
and bounded-collection checks. [DEPLOY_GCP](DEPLOY_GCP.md) owns image build and
cloud acceptance. Record configuration review, Nix evaluation, closure/image build,
boot checks, and deployed HTTP/SSH checks as different evidence levels. Consult
[BUILD_STATUS](BUILD_STATUS.md) for the observed record; no local test substitutes
for a check that has not run on the target host.
