# ADR-0006: ADR-governed development fleet for a solo entrant

- Status: Accepted for the initial prototype
- Date: 2026-11-08

## Context

The owner wants AI agents to build Stratum Witness while preserving a coherent architecture and solo human authorship.

## Decision

Maintain a machine-readable task DAG under `fleet/`. Every task declares one role, dependencies, owned paths, ADR references, acceptance commands, and a report contract. Validate duplicate IDs, missing dependencies, cycles, unsafe paths, and overlapping ready-task ownership before preparation. Prepare a task in a separate git worktree on a dedicated branch with a generated brief. Never overwrite an existing task worktree.

The default fleet tool validates, plans, and prepares work. It does not silently launch a paid model or grant broad shell/credential authority. The current build uses explicitly assigned development agents. Provider-specific unattended execution is a later ADR; a worktree is change isolation, not a process sandbox. The owner reviews and integrates accepted commits. Reports must include actual test results and limitations.

## Alternatives

Several agents editing a shared branch creates ownership and integration ambiguity. Prompt-only architectural rules are difficult to audit. Automatically giving workers a GitHub credential, model account, and merge permission expands authority beyond a coding task.

## Consequences

ADRs constrain implementation; they are not executable access controls. The manifest and tooling catch coordination errors, while genuine agent containment requires an external sandbox. Solo means one human entrant; disclose AI assistance voluntarily. Budget defaults to zero, and only individually available credits may inform a future explicit budget.

## Validation

The manifest rejects cycles, unknown dependencies, traversal and overlapping ownership. Preparing a ready task creates only its named branch/worktree and a brief; blocked or already prepared tasks fail without modifying other work. Planning makes no network call or paid-model invocation.
