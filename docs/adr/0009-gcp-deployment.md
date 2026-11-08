# ADR-0009: Native GCE image and opt-in HTTPS replay

- Status: Accepted design; cloud image/boot/deployment acceptance pending
- Date: 2026-11-08
- Extends: [ADR-0008](0008-ephemeral-nixos-workers.md), [ADR-0005](0005-replay-and-viewer.md)

## Context

A fresh clone needs enough configuration and instructions to continue development,
run offline checks, and deploy the implemented Fleet Witness baseline. ADR-0008
already defines ephemeral offline workers; ADR-0005 defines a read-only replay
viewer. Hosting those components must preserve their trust boundaries and clearly
separate reproducible configuration from evidence of actual deployment.

The default application is a scripted fixture, not a live model fleet or sensor
system. Cloud provisioning is an explicitly separate, billable operator phase;
ordinary development and tests retain zero external spend. Provider integration
and a shared enforced credit ledger remain future work.

## Decision

Use the pinned native NixOS GCE image module, exposed as
`nixosConfigurations.fleet-gcp.config.system.build.googleComputeImage`. Commit the
real generated `flake.lock` with the reviewed nixpkgs revision. Build on x86_64
Linux with KVM available to the Nix builder; runtime E2 instances need no nested
virtualization for systemd-nspawn containers. Obtain the archive name from
`config.image.fileName`, upload it to a private Cloud Storage staging bucket,
and create a private custom image without public IAM bindings.

Retain the exact public flake source and lock at `/etc/fleet-witness/source`.
The generic GCE `/etc/nixos/configuration.nix` deliberately throws an explanatory
error so a generic rebuild cannot silently replace the Fleet configuration.
Operators rebuild the preserved or reviewed updated source using an explicit
`--flake ...#fleet-gcp` target. Source snapshots and Nix store paths are public
inputs: credentials, private datasets and signing keys stay outside them.

Enable OS Login in the guest and instance metadata, disable password/root SSH,
and keep the guest firewall enabled. Use a dedicated custom VPC with IAP-only
TCP 22 ingress from `35.235.240.0/20`. Give the trusted operator OS Admin Login,
IAP tunnel access and Compute Viewer; provisioning/IAM permissions remain separate.
Attach no workload service account and no OAuth scopes. Use an ephemeral external
IPv4 address for host egress; IAP is an ingress path, not a substitute for egress.
A no-external-IP topology needs a separately designed outbound path and cost review.

The initial host is `e2-standard-4` with a 50 GiB balanced persistent boot disk,
manual worker starts, disabled automatic VM restart on failure, and a twelve-hour
maximum runtime with STOP action. Stopping preserves billable resources. Record
resource inventory and collect results before stop/expiry; remove only named
resources after preserving evidence.

Package a synthetic replay as `packages.x86_64-linux.demo` and run
`fleet-witness-demo.service` as an unprivileged account on `127.0.0.1:8765`.
Serve only allowlisted viewer assets, excluding SQLite and credentials. Default
application access is an SSH forward through IAP. An explicitly reviewed real
FQDN in `services.fleetWitnessDemo.publicHostName` enables Caddy HTTPS and guest
TCP 80/443 plus UDP 443; public deployment also needs matching cloud firewall,
a stable address and correct DNS. A shell environment value alone does not enable
public access. The public page remains a read-only scripted replay.

Preserve ADR-0008's manual workers `w-runtime`, `w-viewer`, `w-scenario`, and
`w-review`, private networking, unprivileged task service, source filtering,
resource/time limits, and bounded trusted collection before teardown. Their names
do not dispatch coding agents. Host administration and cloud credentials are
outside worker authority. Containers share the host kernel; configuration is not
proof of hostile-code confinement.

## Alternatives

An unrelated Hostinger/Proxmox host module would introduce platform assumptions
without producing the native GCE artifact. Public image/upload helpers unnecessarily
widen access. A public control API would add authority and authentication outside
the replay contract. Managed static hosting is possible for an exported synthetic
replay, but does not provide the optional NixOS development-worker host.

## Consequences and migration

The fresh-clone handoff gains a concrete image target, service, retained source,
and [ordered deployment runbook](../DEPLOY_GCP.md). Existing local CLI and replay
contracts continue to apply; historical ADRs retain their original verification
record. This extends deployment options without granting workers merge, spending,
publishing, model access, or cloud IAM authority.

The operator owns IAM, DNS, certificate health, updates, evidence retention and
resource teardown. A tested rollback keeps a known-good image and a second SSH
session; broken administration access is recovered by a replacement VM or a
separately designed recovery procedure, not an assumed GRUB/serial root login.
Configuration rollback cannot resume an experiment: synthetic signing keys are
in memory and no database-resume interface exists. Adaption and GCP budgets are
separate; a VM lifetime, estimate or billing alert is not a complete spending cap.

## Validation

Record clean source revision/lock, local Python/Node tests, real replay/HTTP
checks, Nix evaluations, demo/offline derivation builds, full image build, VM boot,
OS Login/IAP, optional TLS, worker containment, collection and teardown as distinct
evidence levels in [BUILD_STATUS](../BUILD_STATUS.md). Evaluation and available
package builds have been observed; full image/KVM, cloud boot and deployment
acceptance have not. This accepted design does not claim deployed success.

Follow [the runbook](../DEPLOY_GCP.md) and
[ADR-0008 boot acceptance](../NIXOS_FLEET.md#required-boot-acceptance-checks-not-yet-executed)
on a disposable host. Require no attached workload identity, no unintended ingress,
loopback-only default viewer, denied database HTTP access, successful fresh IAP
login/sudo, actual cgroup/network/mount restrictions, preserved source/lock, safe
collection before expiry, and successful named-resource cleanup.

## Primary references

- [Pinned native NixOS GCE module](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/nixos/modules/virtualisation/google-compute-image.nix)
- [Google Cloud instance creation](https://docs.cloud.google.com/sdk/gcloud/reference/compute/instances/create)
- [OS Login setup and roles](https://docs.cloud.google.com/compute/docs/oslogin/set-up-oslogin)
- [IAP TCP forwarding](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding)
- [VM runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime)
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
