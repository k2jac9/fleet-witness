# Independent whole-branch integration review

Reviewer: `/root/integration_review`, 2026-11-08.

Task: publication and gate closure. Reviewed candidate
`d90857e2de80cd1823d881fd2b2ea0333c42a32e` against published base
`87156f5419aa4c02c96091bfcad4a5d8a5dd2936` in
`/home/neo/Projects/fleet-witness/.worktrees/gate-closure`.
Read owner policies, project AGENTS.md, architecture, accepted ADRs and the
gate-closure plan. No source, index, checkout or ref mutations were performed.
This report is the reviewer's only retained write. No credentials were read,
paid resources used, deployment performed or provider inference requested.

## Verdict

**Not ready to merge at d90857e.** One Important CI failure-propagation defect
must be corrected and verified. No additional material defect was found in the
reviewed integration. After the narrow fix, obtain passing required checks
bound to the final source and the corrected Nix offline build, and review the
final delta before integration. This verdict is about branch integration, not
paid calibration, deployment promotion or research acceptance.

## Findings

### Critical

None found.

### Important — I1: CI can hide archive verification and test failures

Locations at reviewed HEAD: `.github/workflows/ci.yml:47`, `:63`, `:64`, `:65`,
`:66`, `:69`; no explicit run-shell default at `:10`.

The archive verifier and every behavioral check pipe their status through
`tee`, but no run step explicitly selects Bash or enables `pipefail`. GitHub's
unspecified Linux shell uses `bash -e {0}`; an explicitly selected Bash uses
`bash --noprofile --norc -eo pipefail {0}`. Consequently, a verifier failure can
be followed by extraction of the rejected archive, and failing Python, viewer,
fleet or demo checks can leave the job successful when `tee` succeeds.
This undermines both artifact admission and required acceptance checks.
[Official shell semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#defaultsrun-shell).

Independent local reproduction: `false | tee /dev/null` returns 0 under
`bash -e -c` and 1 under `bash --noprofile --norc -eo pipefail -c`.
Set the workflow run default to `shell: bash` (or explicitly enable equivalent
failure propagation for every relevant step). Verify a deliberately failing
producer cannot pass the pipeline or reach the subsequent extraction/check,
then run the actual hosted matrix on the corrected candidate.

The coordinator independently identified this same issue during this review.
It was not fixed at the exact reviewed HEAD. The historical run is not declared
invalid wholesale: the retained logs themselves show successful tests and
matching archive hashes in all 11 lanes, as detailed below.

### Minor

None requiring a change found.

## Evidence and probes

- Independent local `python3 -m unittest discover -s tests -v`: 149 tests, OK,
  exit 0; bytecode disabled and ambient Git configuration isolated.
- Independent `node --test tests/viewer.test.mjs`: 5 passed, 0 failed, exit 0.
- `python3 scripts/fleet.py validate` and `plan`: valid four-task DAG; three
  delivered tasks and the independent-review task ready; scheduling is
  explicitly distinguished from verification. `git diff --check` passed.
- Examined all 11 retained `identity.json`, archive hash and test logs in
  `hosted-runtime-42515494887`: each source is
  `7a3db75bfc779d973d6f00659cf451cf33cab4e0`; selected version agrees with the
  recorded executable version and each archive receipt matches its lane digest.
  All seven Python logs explicitly end in 149 tests / OK; all four Node logs
  explicitly report five passing tests and zero failures. This independently
  inspects retained evidence, not a new hosted run or runner attestation.
- Examined the CI matrix, selection/identity helper and seven regression tests,
  Nix snapshot inclusion of `ci`, campaign aggregation, dashboard boundary,
  gateway/registry fixtures and current handoff/report claims. The matrix
  separates stable, upcoming, previous-supported and retained consumer checks;
  docs correctly distinguish Ubuntu compatibility from the retained NixOS
  runtime and exact rollback assets.
- Compared earlier review receipts with current implementation SHA-256 values:
  live gateway `b79a3cf716177ff2696f7de9b464c8dca8039c93481649699c3fac994a5b238c`,
  registry `5437bfb482c267b4e66cde951eb41cfac05b7cab8c5d3e41cdfd4b516f133550`,
  dashboard checker `ebfa4c512bf7e26caf03508fef1ae44ef891909933f778cfb61da2f7e467a822`.
  All match the earlier scoped review receipts. Their stated fixture and
  deployment limits remain applicable.
- A bounded pattern scan of all 80 unique branch blobs in base..HEAD found
  zero potential private-key, GitHub-token, Google-key, provider-key or TLS
  session-secret matches. Inspection of the changed-file inventory found no
  private operational ledger, raw TLS transcript or browser-profile addition.
  This is a heuristic publication check, not proof against every possible secret.
- Original accepted ADRs remain unchanged; the new ADRs extend authority under
  the recorded owner scope. Current reports distinguish scripted counts from
  independent model observations, public prices from account-confirmed billing,
  and an inert fixture from production transport or paid activation.

## Declined to judge

- Fresh account balance, billable reasoning bounds, applicable private rates,
  provider retention terms, or actual total cloud charges. No account or
  credential access was made. Missing facts are openly recorded, not concealed.
- Production TLS trust/alternate-chain behavior, egress, real credential loading,
  deadline enforcement, live authorization, calibration or confirmatory results.
  The reviewed code and documentation do not claim these are qualified.
- Full hostile-process isolation, cloud rollback, NixOS/Caddy migration, or the
  future scheduled dashboard deletion. Prior deployment receipts establish only
  their recorded bounded observations.
- New Nix build success while the coordinator's corrected build is running;
  no heavy build was launched by this reviewer. Final-source CI remains the
  integrator's gate and cannot be inferred from the earlier 7a3db75 workflow.
- Independent live upstream version/artifact freshness discovery, cryptographic
  runner attestation, and exhaustive literature/novelty or submission acceptance.
  The exact selections and dated source references were inspected; this review
  did not independently repeat all upstream release lookups.

Only the Important code defect above is a newly discovered merge blocker.
The legitimate external and deployment gaps remain explicit follow-up gates;
they are not grounds to misrepresent this offline integration as incomplete
implementation of an already claimed production capability.

## Integrator resolution (separate from the independent verdict)

Finding I1 was accepted and corrected in `a405921`: the workflow now explicitly
sets `defaults.run.shell: bash`, enabling `-eo pipefail` for its commands.
The real archive verifier was run against a tampered runtime file through `tee`:
unspecified-shell semantics returned 0 despite the digest rejection; explicit
Bash semantics returned 1. The original reviewer verdict above is retained.
The reproduction is preserved in `workflow-failure-propagation.json` under the
artifact root named in the gate-closure plan. The final hosted matrix is a
required integration check; its exact run is linked from the integration PR.

The corrected offline Nix build at `d90857e` exited 0 and produced
`/nix/store/amqa7nj96g203lwyblmln4ybmn45ncnl-fleet-witness-offline-tests`.
Its report says `stage=complete`, `exit_code=0`; the retained logs explicitly
show 149 Python tests OK and five Node tests passed, zero failed. This closes
the missing-manifest build regression, not cloud deployment qualification.
The failed derivation and its five reproduced missing-manifest errors remain
retained. The `a405921` delta changes only the workflow shell default.

This report is a delivered review artifact. Marking its fleet task done does
not turn the original verdict into an approval or waive final-source checks.
The owner requested publication and gate closure on 2026-11-08. The coordinator
will integrate only after the corrected candidate passes required checks;
branches, worktrees and rollback assets are preserved.
