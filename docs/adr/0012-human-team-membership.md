# ADR-0012: Human team membership

- Status: Accepted membership decision, confirmed by the owner
- Date: 2026-11-08
- Supersedes: ADR-0006's solo-entrant and solo-authorship assumption only
- Extends: ADR-0006's task ownership and integration workflow

## Context

Fleet Witness began as Alejandro Castellanos's solo project. After inviting
GitHub user `IPBin` to the repository, Alejandro explicitly confirmed that IPBin
is joining as a teammate. Current contributor and submission documents must
reflect the two-person human team while preserving earlier evidence and the
existing task and operator responsibilities.

## Decision

The human team consists of Alejandro Castellanos (`k2jac9`, repository owner)
and `IPBin` (teammate). AI assistants remain development tools rather than
human entrants. Use IPBin's confirmed GitHub handle until the team supplies a
preferred publication name and affiliation. Record actual contributions and
confirm the final report author list, order and affiliations before submission.

Alejandro remains the repository owner and integration authority. Keep the
version-1 fleet manifest's `owner: "k2jac9"`, one owner per task, dedicated
branches/worktrees, independent review and actual acceptance evidence. Human
teammates coordinate task ownership through this workflow. Team membership
does not change provider/cloud budgets, credential grants, agent authority or
the controller's exclusive authority over experimental effects.

## Alternatives

- Keep current documents describing a solo submission: inconsistent with the
  owner's explicit membership confirmation.
- Rewrite earlier accepted decisions and review records: loses historical
  context and could imply IPBin contributed to earlier work without evidence.
- Expand account access or spending with team membership: a separate operational
  decision, not a consequence of this authorship update.

## Consequences and migration

Update current project, contributor, research, submission and task-brief text.
Preserve ADR-0001 through ADR-0011, prior plans, build records and reviews;
their solo wording describes the earlier project state. This record replaces
only ADR-0006's current solo assumption; its task and agent boundaries continue.
The report remains a draft, and repository membership is not event registration
or a completed submission. No past code, experiments or results are newly
attributed to IPBin by this change.

## Validation

Check that current documents identify both teammates and keep unconfirmed
publication details explicit. Validate the fleet manifest after updating its
research-report brief; keep schema, owner, budgets and acceptance commands
unchanged. Verify that accepted ADRs and historical receipts have no changes,
check links and whitespace, run the required Python suite, and independently
review the exact documentation diff before integration.
