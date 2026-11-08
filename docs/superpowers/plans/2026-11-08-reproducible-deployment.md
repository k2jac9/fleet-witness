# Reproducible Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a fresh clone sufficient to continue development, test, and deploy the implemented Fleet Witness baseline on GCP.

**Architecture:** Retain the current controller and offline workers. Add a native NixOS GCE image target and a loopback viewer service with explicit opt-in public HTTPS. Document cloud operations and future provider boundaries separately from observed verification.

**Tech Stack:** Python 3.11+ standard library, Node 24, Git, pinned NixOS, systemd-nspawn, Google Compute Engine, IAP/OS Login, optional Caddy.

**Spec:** ../specs/2026-11-08-reproducible-deployment-design.md

## Global Constraints

- Product name: Fleet Witness; repository: k2jac9/fleet-witness; sole human owner: Alejandro Castellanos.
- Default backend is scripted-demo; default external spend remains zero.
- Preserve controller/evaluator boundaries and ADR-0008 worker isolation and limits.
- No cloud resources, model calls, credentials, or event submission in this update.
- Configuration, evaluation, build, boot, and deployed acceptance are distinct evidence levels.
- Keep cloud identifiers, domains, and personal environment values configurable; no secrets in Git or Nix images.

## Review Focus

- A fresh clone must contain every file referenced by a command; Nix Git inputs exclude untracked files.
- OS Login/IAP access and local firewall settings must agree; recovery must not assume a GRUB menu.
- Image creation must preserve the Fleet configuration for later rebuilds and require a KVM builder explicitly.
- Worker outputs and the cloud metadata endpoint remain outside worker authority; collection precedes teardown.
- Spending estimates are not enforced caps; stopped VMs can retain billed disks and images.

---

### Task 1: GCP image and viewer configuration

**Files:** Modify `flake.nix`; create `nix/hosts/gcp.nix`, `nix/demo.nix`; generated `flake.lock` only if Nix is available.

**Interfaces:** Produces `nixosConfigurations.fleet-gcp`, `packages.x86_64-linux.demo`, a `fleet-witness-demo.service` on 127.0.0.1:8765, and `services.fleetWitnessDemo.publicHostName` (null by default). Default host declares four manually started workers: w-runtime, w-viewer, w-scenario, w-review.

- [ ] Implement the native GCE host and unprivileged read-only scripted viewer, preserving offline worker restrictions.
- [ ] Evaluate the flake and image derivation where Nix is available; build the demo and offline checks when feasible. Record exact limitations.
- [ ] Review the configuration independently, including optional public HTTPS and later rebuild behavior.

### Task 2: Fresh-clone development and test instructions

**Files:** Create `docs/DEVELOPMENT.md`, `docs/TESTING.md`, `docs/OPERATIONS.md`, `CONTRIBUTING.md`.

**Interfaces:** Consumes existing CLI, task planner, and Nix worker contract. Links `docs/DEPLOY_GCP.md`, `docs/ADAPTION.md`, `docs/COSTS.md`, and the new service/output names from Task 1.

- [ ] Document prerequisites, setup, clean output paths, tests, change ownership, task preparation, review, evidence interpretation, operations, and troubleshooting.
- [ ] Exercise the documented zero-spend commands from a clean checkout and check local links.
- [ ] Review for completeness and unsupported claims.

### Task 3: Resources, credit plan, and cybersecurity/policy scope

**Files:** Create `docs/ADAPTION.md`, `docs/COSTS.md`, `docs/RESOURCES.md`, `docs/SECURITY_POLICY.md`.

**Interfaces:** Uses the confirmed $1,500 Adaption planning balance, zero default spend, GCP estimates, and proposed host-side gateway. Does not mark the existing adapter-proposal task complete.

- [ ] Record sourced resources, API/SDK availability, balance assumptions, rate units, budget design, free-tier constraints, and clear implementation gaps.
- [ ] Describe controlled research, separate public honeypot deployment, metadata/credential boundaries, retention, and evidence limits.
- [ ] Check sources and review consistency with code and ADRs.

### Task 4: Deployment runbook, ADR, and integration

**Files:** Create `docs/DEPLOY_GCP.md`, `docs/adr/0009-gcp-deployment.md`; update `README.md`, `AGENTS.md`, `docs/adr/README.md`, `docs/architecture.md`, `docs/ROADMAP.md`, `docs/BUILD_STATUS.md`, `docs/NIXOS_FLEET.md`, `.gitignore` as required.

**Interfaces:** Consumes Tasks 1-3. Includes reviewed commands for project prerequisites, private image upload, IAM, networking, instance creation, IAP, optional HTTPS, worker operation, updates, recovery, exports, and cleanup.

- [ ] Write the end-to-end runbook with placeholder values and expected verification outcomes.
- [ ] Add the decision and connect every guide from the README; preserve historical verification and accepted prior ADRs.
- [ ] Run Python/Node tests, local demo/HTTP verification, task preparation in a disposable clone, Nix checks where possible, shell syntax and documentation-link checks.
- [ ] Obtain a whole-change review, resolve material issues, publish the reviewed tree, and verify the remote revision and CI outcome.
