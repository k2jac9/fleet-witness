# Contributing to Fleet Witness

Alejandro Castellanos (`k2jac9`) is the sole human owner and entrant. AI agents
are development tools; disclose assistance and provenance as described in
[AI_ASSISTANCE](docs/AI_ASSISTANCE.md). Begin with [AGENTS.md](AGENTS.md),
[architecture](docs/architecture.md), and the relevant [accepted ADRs](docs/adr/README.md).
[Development](docs/DEVELOPMENT.md) and [testing](docs/TESTING.md) give reproducible
commands; [security policy](docs/SECURITY_POLICY.md) defines the operating and research boundaries.

## Work on a bounded task

Prefer one owner, explicit owned paths, a dedicated branch/worktree, and a
reviewable commit. Use `fleet/tasks.json` and `python scripts/fleet.py plan` to
identify ready work, then prepare it as documented in the
[fleet guide](fleet/README.md). Edit only assigned paths. Propose changes to task
scope or a superseding ADR when necessary; do not silently revise accepted
architectural decisions. Keep truth, signing keys, controller authority, and
independent evaluation outside supervisor-visible inputs.

A clean tracked checkout is required for preparation; untracked notes are allowed
but do not travel to the new worktree. Existing branches, paths, symlinks, and
stale registrations are refused. Executable Git filters (including Git LFS) and
conditional includes are also refused. Do not disable the guard or rewrite global
Git configuration to make preparation succeed; report the environment conflict
or use a reviewed environment compatible with the tool's refusal contract.

Preparation does not execute acceptance commands or dispatch agents. Run each
required command explicitly and record what actually happened. Keep default
external spend at zero. Model/provider access, cloud provisioning, publishing,
credential grants, and external messages require separate authorization. Future
provider boundaries are described in [ADAPTION](docs/ADAPTION.md); they are not
an implemented dispatch system.

## Review and integration

For security-sensitive behavior, demonstrate a failing behavioral test before the
fix. Run the full standard-library Python suite, relevant Node tests, manifest
validation, and `git diff --check` as appropriate to the change. Test behavior,
not implementation spelling. Review documentation commands and links when changing
the handoff. [TESTING](docs/TESTING.md) distinguishes local checks, visual checks,
Nix builds, boot acceptance, and deployment evidence.

A task report must include its ID, exact commit, changed paths, actual commands
and results, failed checks, unexecuted checks, and remaining limitations. Label
fixtures as scripted; do not infer model robustness, production isolation, live
sensors, or cloud success from local checks. An independent reviewer checks the
exact diff and evidence. The owner integrates accepted commits and updates task
status; workers do not merge or publish. `done` is scheduling metadata.

## Recover a partially prepared worktree

Refusal protects existing work. Inspect before acting, substituting the one exact
task path rather than a broad pattern:

```sh
git worktree list --porcelain
git branch --list fleet/adapter-proposal
git -C .worktrees/adapter-proposal status --short
git -C .worktrees/adapter-proposal log -5 --oneline
```

If that directory is missing, inspect its registration and filesystem state instead
of assuming it is disposable. Preserve useful edits and commits first. A worktree
moved accidentally can be repaired with `git worktree repair /exact/existing/path`
after confirming its identity. Once the owner has confirmed a specific worktree is
clean and no longer needed, use `git worktree remove .worktrees/adapter-proposal`
without `--force`; retain its branch until integration/review is resolved.
An existing branch may still intentionally block re-preparation: resume it or
choose a newly reviewed task, rather than deleting it blindly.

Do not run `git clean -fdx`, recursive deletion of `.worktrees`, forced checkout,
or bulk `git worktree prune` as a preparation fix. If ordinary removal refuses,
inspect the reason and preserve work; refusal is useful evidence, not a request
for a larger hammer.
