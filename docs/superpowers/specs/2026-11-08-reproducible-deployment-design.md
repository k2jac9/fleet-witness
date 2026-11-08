# Reproducible development and deployment handoff

## Intent

A fresh clone of Fleet Witness must contain the context, commands, configuration,
and verification steps needed to continue development, test the implemented
baseline, and deploy that baseline and its offline development workers on GCP.
The owner requested this handoff after selecting NixOS and reviewing the GCP
deployment approach. Updating the public repository is authorized; creating paid
cloud resources, making model calls, or submitting the hackathon entry is outside
this repository-update task.

## Scope and decisions

- Preserve the dependency-free Python 3.11+ baseline, static viewer, controller
  invariants, solo ownership, and zero-spend default.
- Add a real `nixosConfigurations.fleet-gcp` image target using the existing
  nixpkgs pin and the upstream GCE image module. Preserve ADR-0008 worker limits
  and default manual starts. Generate a real lock only with Nix.
- Package a synthetic replay and run the allowlisted viewer as an unprivileged
  NixOS service on loopback port 8765. An explicitly configured domain may enable
  Caddy HTTPS; the default image exposes administration through IAP/OS Login and
  does not open public application ports.
- Use a dedicated GCP project/network, private image upload, no attached workload
  service account by default, OS Login metadata, an explicit guest firewall, and
  a VM runtime limit. Build the image on an x86_64 Linux KVM-capable builder; the
  E2 runtime host does not need nested virtualization.
- Document clone/setup, tests, task ownership, local demo, image build, IAM,
  provisioning, SSH, worker operation, collection, public HTTPS, updates,
  recovery, teardown, troubleshooting, cost estimates, and research limitations.
- Record $1,500 as the owner-confirmed Adaption credit planning balance, separate
  from GCP spending. Provider dispatch and an enforced shared credit budget are
  future work; describe their contracts without implying implementation.
- Keep public honeypots, global attribution, real-model results, and automated
  coding dispatch clearly separated from the shipped scripted baseline.

## Alternatives and boundaries

Use the native GCE configuration instead of the reference nixos-vps repository's
Hostinger/Proxmox platform module. Its modular deployment and secret-handling
patterns are useful references; preserve licensing if substantial code is copied.
Keep optional HTTPS on the VM so deployment does not require a second hosting
platform. Static export can also be hosted separately. A production multi-tenant
service, a live sensor network, and a model-provider integration are not created
by these operating instructions.

## Acceptance

A clean checkout passes the existing Python and Node suites, prepares a task in a
disposable clone, produces and serves a real demo, and contains no broken local
documentation links. Evaluate the new Nix outputs and build available offline
derivations where the environment permits. Record image/boot/cloud checks that
cannot run; never replace observed verification with mock cloud success. Independently
review the configuration and runbook before publishing the exact reviewed tree.
