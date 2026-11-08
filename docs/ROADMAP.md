# Roadmap

The current pilot has expanded receipt scenarios, an accepted gateway design,
offline accounting and authorization fixtures, a 640-trial scripted campaign,
a built and booted NixOS image, four exercised offline workers, and a separately
hosted authenticated dashboard. The VM is stopped. The Python/Node stable,
upcoming, previous and consumer matrix has executed. This is a scripted
mechanism demonstration; live inference has not run. See [current gates](GATES.md)
for individual acceptance states and [BUILD_STATUS.md](BUILD_STATUS.md) for
source-bound evidence and preserved failures.

1. **Integrate the reviewed continuation.** Publish all source branches, retain
   baseline/rollback identities, reproduce required checks and obtain independent
   review before integrating main. Scheduling status is not acceptance.
2. **Resolve provider facts.** Verify account-specific balance, rates, all billed
   reasoning bounds, per-request accounting and actual data-handling terms. Public
   model tables and the owner-reported balance do not establish these facts.
3. **Qualify the production gateway.** Continue ADR-0010: pin runtime and trust,
   implement the bounded no-retry transport and one shared production authorization,
   preserve controller authority and worker isolation, test failure/accounting
   behavior and independently review the exact candidate. The current modules
   remain offline fixtures.
4. **Finish runtime and cloud recovery acceptance.** Migrate the durable Nix launch
   path with current stable evidence and previous/preview lanes, qualify remaining
   host/gateway and collector cases, rehearse cloud rollback and reconcile costs.
   Preserve the existing image, lock, storage, receipts and consumer checks.
5. **Run separately bounded calibration, then freeze the study.** Only after all
   applicable ADR-0010 gates pass, execute and reconcile the authorized calibration.
   A confirmatory 320-request study needs its own frozen model/prompt/schedule/
   analysis/budget identities and live replay schema. Failed and unstarted calls
   remain visible; do not extrapolate from scripted repetitions.
6. **Finish the research artifact.** The [report draft](research-report.md)
   describes observed synthetic results and limitations. The independent integration
   review is delivered; official template/PDF, affiliation confirmation and an owner submission decision
   remain distinct from code publication. The [submission guide](SUBMISSION.md)
   links the official requirements.

A public observation sensor, autonomous coding-worker dispatch, stronger
attestation, persisted-key/resume support and any Rust controller remain separate
future work. No current task authorizes third-party scanning, unsolicited fleet
contact, broader provider spend or retirement of retained recovery assets.
