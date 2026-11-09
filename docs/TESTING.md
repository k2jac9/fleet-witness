# Testing and evidence

Run behavioral checks from the repository root on Linux/POSIX, using Git and
the [pinned Python/Node matrix](RUNTIME_ADOPTION.md). Python 3.11+ and Node 24
remain supported consumers. No model account, cloud project, npm installation, or runtime
Python package is required. [Development](DEVELOPMENT.md) covers setup.

## Automated checks

```sh
python3 -m unittest discover -s tests -v
node --test tests/viewer.test.mjs
python3 scripts/fleet.py validate
python3 scripts/fleet.py plan
git diff --check
```

The publication base merged in [PR #13](https://github.com/k2jac9/fleet-witness/pull/13)
passed 309 Python tests per Python lane and five viewer tests per Node lane across
all 11 pinned runtime lanes. [Build status](BUILD_STATUS.md) retains the exact
tested tree and run identities, including earlier 49- and 233-test checkpoints.
Synthetic source identities are restricted to offline test fixtures; production
missing-source rejection remains tested. Record the exact commit,
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
| Model gateway and pilot | Bounded transport/schema validation, source/account authorization, shared accounting, failure liabilities and recovery without new dispatch |
| Publication | Scalar-only trial export, private-field refusal, package allowlist and symlink/path protections |

Add tests for changed behavior and trust boundaries. For security-sensitive code,
first reproduce the failure with a failing behavioral test, then fix and run the
full Python suite. Documentation changes need exercised commands and link review;
tests that merely match document wording do not establish correctness.

## Swarm stabilization checks

`tests/test_swarm_provider.py`, `test_swarm_ledger.py` and
`test_swarm_provenance.py` exercise real accounting/runner code using temporary
private ledgers, synthetic credentials and network doubles. They cover restarts,
competing processes, preserved failure liabilities, one-attempt behavior,
protected request fields, authorization before I/O, complete-run accounting and
private/public receipt boundaries. They never qualify a real provider account.
`test_reproduction.py` covers archive traversal/collisions, complete denominators,
actual-kernel reconstruction and unchanged raw inputs. Figure tests check
answered-only populations and conventional even/odd medians.

Use the explicit extraction/reproduction commands in [SWARM.md](SWARM.md) for the
retained archive. Default reproduction includes the depth-six checker and seven
mutants; `--skip-checker` must be reported as an omitted check. Source/runtime,
raw input and derived hashes are retained in `reproduction-provenance.json`.
Inherited unclosed-SQLite warnings remain visible in the full test logs; a pass
does not assert warning-free execution or production isolation.

## Full offline smoke

The same launcher used by the configured worker copies the source, runs Python
and available Node tests, then generates the scripted demo. Use a fresh checkout
without secrets; outside Nix this command copies the supplied source directory
without the Nix snapshot filter. Its shell requires Bash and `realpath`. The
example assumes a primary checkout; in a worktree, point `artifact_root` at the
project's existing artifact directory. Apply storage admission before a heavy run.

```sh
artifact_root="../fleet-witness-artifacts"
mkdir -p "$artifact_root"
smoke_root=$(mktemp -d "$artifact_root/smoke.XXXXXXXX")
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
`python3 -m fleet_witness serve --directory "$smoke_root/task/results/demo" --port 8765`.
The server tests cover responses and forbidden requests; a manual HTTP check can
also confirm `/`, `/replay.json`, `/app.js`, and `/styles.css` return 200 while
`/witness.sqlite3` returns 404. If port 8765 is occupied, use another port rather
than stopping an unknown process. Stop your own server with Ctrl-C.

Automated Node tests exercise data logic without a real browser. Visual appearance,
keyboard interaction and responsive layout need a separate recorded browser check
for the candidate under review. Earlier checks remain dated evidence; use this
checklist when the viewer changes:

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
