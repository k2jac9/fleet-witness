# ADR-0008: Ephemeral NixOS development workers

- Status: Accepted design; Nix evaluation and boot validation pending
- Date: 2026-11-08
- Extends: ADR-0006

## Context

The owner selected ephemeral NixOS containers for the development fleet. Git worktrees isolate changes but do not restrict a worker's processes, network, or access to host services. Disposable task environments also make dependency state reproducible.

## Decision

Provide a revision-pinned Nix flake and an opt-in NixOS host module. Run one unprivileged task service per named ephemeral container. Set container `ephemeral = true`, `privateUsers = "pick"`, `privateNetwork = true`, and `autoStart = false`. Use a filtered immutable source snapshot, copied into a bounded writable workspace inside the container. No custom writable host mounts, model credentials, forwarding, or NAT are added.

The task service has its own private network namespace, no new privileges or capabilities, a read-only system, hidden home directories, and explicitly bounded writable paths. Mask `/nix/var/nix` for the task service: the standard NixOS container module otherwise exposes host Nix service paths, and a read-only socket mount does not make socket operations read-only. Keep loopback available for the project's local HTTP tests.

Apply aggregate CPU, memory, process, and lifetime limits to the host's `container@NAME.service`, because the NixOS launcher uses `--keep-unit`. Use `TimeoutStartSec` for the inner oneshot task. Initial proposed budgets are one CPU, 1 GiB hard memory, 256 tasks, a 512 MiB workspace, a ten-minute task timeout, a twelve-minute host startup allowance, and a fifteen-minute active container lifetime after readiness. Startup and active budgets are additive, so this is not a fifteen-minute wall-clock cap from launch. The startup allowance covers the boot-attached ten-minute oneshot plus overhead. These are configured limits, not measured performance requirements.

Keep task outputs inside the container until collection. The trusted operator records the actual systemd result and collects a small allowlist of reports/logs/patches into a fresh host quarantine directory before teardown. Never automatically apply a patch or execute/extract collected content. The worker's self-reported success is not a trusted verification result. A stop or lifetime expiry destroys uncollected state.

The initial container task runs the repository's offline tests and demo. The AI orchestrator and provider credentials remain outside. A provider/tool gateway and automatic coding-worker dispatch require a later ADR; this configuration does not claim those are implemented.

## Alternatives

Writable host worktree mounts are convenient but complicate private UID mappings and expose persistent state. Running workers as container root or sharing the host network is unnecessary. A disposable NixOS VM provides a separate kernel; use one as the fleet host when evaluating potentially hostile code.

## Consequences

Containers share the host kernel. Ephemerality is lifecycle cleanup, not proof of containment or deletion of host-side logs. Standard NixOS container plumbing still has host-backed state; the restrictions apply to the unprivileged task service and must be tested on the pinned revision. Root administrative commands bypass worker restrictions and are never an agent tool interface.

Nix is unavailable in the current build environment. Ship configuration, static review, and reproducible validation commands, with evaluation/build/boot status explicitly pending. Do not invent a flake lock hash or claim deployed containers. Generate and commit a real lock on a Nix-capable host before deployment.

## Validation

Evaluate the flake/module, build the offline test derivation, then boot on a disposable NixOS VM. Verify worker identity, user mapping, source immutability, Nix daemon denial, network restrictions, actual cgroup limits, success/failure/timeout propagation, a successful task exceeding sixty seconds during boot, output collection before active expiry, and clean workspace after restart. A successful unit-test derivation alone does not prove container isolation.

## Primary references

- [NixOS container options](https://nixos.org/manual/nixos/unstable/options.html)
- [NixOS container implementation](https://github.com/NixOS/nixpkgs/blob/master/nixos/modules/virtualisation/nixos-containers.nix)
- [systemd-nspawn](https://www.freedesktop.org/software/systemd/man/latest/systemd-nspawn.html)
- [systemd service timeouts](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd resource controls](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
