# Development task fleet

This is the development coordination tool for Alejandro Castellanos's solo project. It is separate from the simulated worker/reviewer fleet evaluated by the demo. [ADR-0006](../docs/adr/0006-development-fleet.md) governs task ownership and [ADR-0008](../docs/adr/0008-ephemeral-nixos-workers.md) records the optional ephemeral NixOS worker target.

From the repository root with Python 3.11+ and Git installed:

```sh
python scripts/fleet.py validate
python scripts/fleet.py plan
python scripts/fleet.py prepare adapter-proposal
```

`validate` and `plan` read the manifest and local Git state. The plan is deterministic and topologically ordered; a `todo` task is ready when every direct dependency is `done`. Marking a task `done` is a manual scheduling decision, never evidence that its acceptance commands passed. The owner must review its actual commit and verification report before updating status. Branches and prepared worktrees do not automatically change task status.

`prepare` requires clean tracked files, an unused `fleet/<id>` branch, and an unused `.worktrees/<id>` path, including no stale worktree registration. It creates the branch and worktree from the current `HEAD`, then writes `.worktrees/<id>/.fleet/brief.md`. Both worktrees and briefs are ignored by the committed `.gitignore`. Untracked local notes are allowed and are not copied into the task worktree. Existing artifacts are refused rather than overwritten or pruned. All fleet commands refuse any effective Git `filter.*.clean`, `filter.*.smudge`, or `filter.*.process` configuration, including included/global/worktree entries, before status or checkout can run a filter. Refusal applies even if no tracked attribute currently selects the filter. Conditional Git includes (`includeIf`) are also refused, because a new branch or worktree path can activate filter configuration that is inactive in the original checkout. The tool reads only matching configuration names and does not rewrite Git configuration. Preparation also suppresses Git checkout hooks and fsmonitor helpers. A failed OS or Git operation can leave a branch/worktree; inspect actual state before an explicit operator cleanup. No automatic cleanup removes another task's work.

For a disposable clone or an explicitly selected existing worktree, put `--root /absolute/repository` before the command. The root must be the exact Git worktree top level; symlink roots and path components are refused. Manifest, ADR, ownership, and worktree paths must not redirect through existing symlinks. These checks defend against accidental redirection at preparation time; a concurrently hostile process can still race filesystem changes. Use the separate worker environment for process isolation.

The version-1 manifest has exact top-level fields `version: 1`, `owner: "k2jac9"`, `default_budget_usd: 0`, and `tasks`. Each task declares an `id`, `title`, `role`, `status` (`todo` or `done`), `depends_on`, `owned_paths`, `adrs`, `acceptance`, and `brief`. Acceptance commands are nonempty arrays of string argv arrays. Unknown fields and duplicate JSON keys fail closed. Ownership paths are literal repository-relative paths, with directory ownership extending to descendants; globs, reserved tool directories, absolute paths, traversal, and ambiguous separators are refused. Accepted ADR files must exist locally. All simultaneously ready tasks must have disjoint ownership. A blocked task may reuse a predecessor's paths after that predecessor completes.

The starter DAG has two ready tasks, `adapter-proposal` and `expanded-scenarios`. `research-report` waits for both; `independent-review` waits for the report. Each task references accepted ADRs and includes a report contract. Prepared briefs contain repository data and suggested commands; they do not confer authority to execute those commands.

Preparation runs no acceptance command or model, reads no credential, and grants no spending, publishing, merging, access, or ADR-changing authority. It does not contact a provider or create a container. An operator can carry a reviewed source snapshot into the optional [NixOS environment](../docs/NIXOS_FLEET.md); evaluation, boot, and containment checks are pending on a Nix-capable host. The initial configured worker runs offline tests and a demo. Automatic coding-worker dispatch and a mediated provider/tool gateway require future decisions. Worktrees alone are change isolation, with all the process-confinement powers of a very tidy folder.
