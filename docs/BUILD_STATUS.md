# Initial build verification

Verified on 2026-11-08 on Linux, Python 3.12.14, Node 24.22.1, and Git
2.52.0. The final source fingerprints below identify the tested code independently
of documentation-only commits. This document records observed
checks, not a claim of a deployed fleet or a completed hackathon submission.

## Observed checks

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

## Generated scripted baseline

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

## Acceptance still pending

- **Nix evaluation, build, and boot:** Nix, `nixos-container`, and
  `systemd-nspawn` are unavailable in this environment. The worker script was
  executed as an ordinary process; its success does not prove container
  confinement. Generate a real `flake.lock` and execute the acceptance procedure
  in [NIXOS_FLEET.md](NIXOS_FLEET.md) on a disposable NixOS VM. In particular,
  verify network and daemon denial, actual cgroup limits, a successful task
  longer than sixty seconds, bounded collection, and clean restart.
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

## Tested source fingerprints

| Git tree or blob | Object ID |
| --- | --- |
| `fleet_witness` | `8fe578874e0041a6d62a5a3079fcb971c6c2f893` |
| `tests` | `aac2506c3e920ceeeb70753c2867ef1544eea7ca` |
| `scripts` | `ab1dbc272f9c1c268a9a124c0e90d7e4829c5a0e` |
| `nix` | `42207aec2321f1c41e293222c516e32dc0ea9aa7` |
| `flake.nix` | `2636f0d34d0630566545c28610faec557f8f1d65` |
| `.github/workflows/ci.yml` | `58d8a80de863595f7fd8d70de6db738b38fcd31d` |

For example, `git rev-parse HEAD:fleet_witness` verifies the runtime and viewer
fingerprint after cloning. Documentation or repository screenshots may change
without changing these tested objects.
