# Build and deployment verification

## Fresh-clone and GCP handoff: 2026-11-08

The repository now includes a generated `flake.lock`, the native
`fleet-gcp` NixOS configuration, a packaged synthetic replay service, and the
[complete development/deployment handbook](../README.md#handbook). This section
updates the original baseline record below; it does not claim a running cloud
deployment. No GCP resource or Adaption request was created by this update.

| Observed check | Result |
| --- | --- |
| Fresh checkout Python and viewer suites | 49 Python tests and 5 Node tests passed |
| Task validation, planning, and preparation in a disposable clone | Four valid tasks, $0 external budget, two ready tasks; isolated worktree and brief created |
| Offline task launcher | Exit 0, stage `complete`; expected seed-42 fixture counts |
| Generated replay over real loopback HTTP | Four public assets return 200; private database denied; two authorized duplicate no-ops verified |
| Nix dependency resolution | Real lock generated with Nix 2.34.1 for revision `c56a87d8e41ce69bd2af57eb35dcc117a9dfca33` |
| Native GCP image derivation | Evaluates; builder explicitly requires `kvm` |
| `nix flake check --no-build` on x86_64 Linux | All applicable outputs evaluate; aarch64 output evaluation was not requested |
| `packages.x86_64-linux.demo` | Builds and runs; only four public assets, no SQLite file in the package |
| Packaged HTTP behavior | Assets return 200; database/traversal/secret paths return 404; POST returns 405 |
| `checks.x86_64-linux.offline-tests` | Builds successfully under pinned dependencies; 49 Python and 5 Node tests pass |
| Default host evaluation | OS Login and guest firewall enabled; TCP 22 only, Caddy disabled, loopback viewer configured |
| Public-host option evaluation | Valid domain enables Caddy TCP 80/443 and UDP 443; malformed hostnames rejected |
| Worker configuration evaluation | Four manual ephemeral workers with private users/network and original resource/time limits |
| Retained source and rebuild guard | Snapshot includes lock; generic rebuild refuses and points to explicit Fleet flake |
| Independent code/document review | Missing host Python/Git found and corrected; evaluated host now exposes Python, Git, and curl |
| Handbook links and shell examples | Relative file/heading links resolve; shell examples and environment template pass `bash -n` |

The application and test trees are unchanged from the original baseline. The
host now has the operator tools required by collection and update instructions.
The generated replay uses a fresh synthetic HMAC key and timestamp: pinned
dependencies and scenario semantics do not imply byte-identical replay outputs.

The integrated handoff was cloned into a separate temporary directory and the
Python/Node suites, task planner/preparation, full offline smoke, Nix output
evaluation, and both Nix package builds were rerun successfully. The packaged
viewer was also served and checked over real HTTP: its four assets returned 200
with CSP, private/traversal paths returned 404, and POST returned 405.

Current deployment source fingerprints (Git objects, excluding documentation):

| Object | ID |
| --- | --- |
| `nix` tree | `1326bc8aea74727518d0bd5097940e7580f4950b` |
| `flake.nix` blob | `de14f30f78cb0d16caa8d8b168efba392627e1b8` |
| `flake.lock` blob | `2fd8f185b1a5f2de10646d14956f714588be780e` |

Verify these with `git rev-parse HEAD:nix HEAD:flake.nix HEAD:flake.lock`.

### Acceptance still required

- **Image construction and first boot:** this verification environment has no
  `/dev/kvm`. Build the full raw image on the documented Linux KVM builder,
  boot it on a disposable GCP VM, and record the exact image/configuration.
- **Cloud access and service behavior:** actually exercise IAM, OS Login/IAP,
  systemd startup, private browser access, and optional DNS/TLS issuance.
  Evaluation and standalone package HTTP checks establish narrower properties.
- **Worker confinement and lifecycle:** execute the [host acceptance checks](NIXOS_FLEET.md#required-boot-acceptance-checks-not-yet-executed),
  including metadata/daemon denial, actual cgroups, startup timing, bounded
  output collection, timeout results, and ephemeral cleanup.
- **Browser visual acceptance:** the handoff adds no new visual verification.
  Follow [TESTING.md](TESTING.md#http-and-manual-browser-acceptance).
- **Provider, research, and submission:** no live-model adapter or budget
  gateway, autonomous coding dispatch, public honeypot, real-model study,
  research report, or event submission is claimed complete.

Use [DEPLOY_GCP.md](DEPLOY_GCP.md) to record deployment evidence and teardown.
Keep package build, image build, boot, and runtime containment as separate
checks when updating this record.

## Original baseline verification (historical record)

Verified on 2026-11-08 on Linux, Python 3.12.14, Node 24.22.1, and Git
2.52.0. The final source fingerprints below identify the tested code independently
of documentation-only commits. This document records observed
checks, not a claim of a deployed fleet or a completed hackathon submission.

### Observed checks

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -v` | 49 passed |
| `node --test tests/viewer.test.mjs` | 5 passed |
| Additional temporary jsdom interaction harness | 5 passed; supplementary, outside the baseline dependency set |
| `bash -n nix/offline-task.sh` | Passed |
| `git diff --check` | Passed |
| `python3 scripts/fleet.py validate` | 4 valid tasks; default external budget $0 |
| `python3 scripts/fleet.py plan` | Two ready tasks; report and independent review blocked by declared dependencies |
| `prepare adapter-proposal` in a disposable clone | Dedicated branch, worktree, and ignored brief created successfully |
| Offline worker script against a fresh copy of tracked source | Exit 0, stage `complete`; 49 Python tests, 5 viewer tests, and demo completed |
| HTTP integration using a real generated replay | Index and replay returned 200, CSP present, private SQLite file returned 404 |

The temporary DOM checks covered recovery from empty filtered presentations,
keyboard focus after list replacement, rejected imports preserving state,
rollback after a rendering failure, and hostile text remaining text. They do
not replace real browser visual or accessibility testing.

Task implementation and scoped reviews covered the runtime, dashboard, fleet
preparation, and Nix configuration. Review fixes included import rollback and
focus recovery, refusal of executable Git filters and conditional includes,
and a container startup allowance that covers the inner task budget. Final
integration corrections align producer seeds with the viewer's safe-integer range,
clarify independent decision scoring, and isolate disposable tests from ambient
Git configuration while preserving the production filter refusal guard.

The whole-branch review and final scoped re-review approved publication of this
scripted baseline, with no remaining code findings in their reviewed scope.

### Generated scripted baseline

Command:

```sh
python3 -m fleet_witness demo --output runs/integrated --seed 42
```

| Recorded quantity | Count |
| --- | ---: |
| Episodes | 20 |
| Approved recommendations | 13 |
| Invalid recommendations | 7 |
| Execution attempts | 15 |
| Committed local effects | 4 |
| Authorization denials | 9 |

Two authorized duplicate attempts are no-ops. They create no extra effect and
are not counted as authorization denials. The paired raw and scope-explicit
traces are deterministic demonstrations, not empirical language-model results.
The effect is a local database row. No external release or publication is
performed by the demo.

### Acceptance pending at the original baseline

- **Nix evaluation, build, and boot:** the original environment lacked Nix,
  `nixos-container`, and `systemd-nspawn`. The handoff section above supersedes
  the lock/evaluation/package-build gaps. Boot and confinement remain pending;
  an ordinary-process worker-script run does not prove isolation.
- **Browser visual acceptance:** Connected browsers could not reach this
  workspace's loopback server, and a local Chromium process could not start
  because its required socket operation was denied. Desktop/narrow layout,
  contrast, overflow, browser console, and browser-specific keyboard behavior
  remain unverified. HTTP and jsdom checks above establish narrower properties.
- **Live model and provider gateway:** No Adaption integration, model request,
  automatic coding-worker dispatch, or credit expenditure is implemented in
  this slice. The adapter proposal is a ready fleet task.
- **Research and submission:** Real model trials, the report, and any event
  submission remain separate work. Solo authorship and AI assistance are
  documented in [AI_ASSISTANCE.md](AI_ASSISTANCE.md).

The project was initially scaffolded with an incorrect working name. The
repository, Python package, UI, Nix options, and documentation were corrected
to **Fleet Witness** before publishing the implementation.

### Original tested source fingerprints

| Git tree or blob | Object ID |
| --- | --- |
| `fleet_witness` | `8fe578874e0041a6d62a5a3079fcb971c6c2f893` |
| `tests` | `aac2506c3e920ceeeb70753c2867ef1544eea7ca` |
| `scripts` | `ab1dbc272f9c1c268a9a124c0e90d7e4829c5a0e` |
| `nix` | `42207aec2321f1c41e293222c516e32dc0ea9aa7` |
| `flake.nix` | `2636f0d34d0630566545c28610faec557f8f1d65` |
| `.github/workflows/ci.yml` | `58d8a80de863595f7fd8d70de6db738b38fcd31d` |

For example, `git rev-parse HEAD:fleet_witness` verifies the unchanged runtime
and viewer fingerprint after cloning. The GCP handoff changes `nix` and
`flake.nix` and adds `flake.lock`; their entries above describe the original
baseline, not the new deployment configuration. Documentation or repository
screenshots can change independently of tested application objects.
