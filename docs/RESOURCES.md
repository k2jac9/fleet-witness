# Resource map for continuing Fleet Witness

Platform/provider references were checked **2026-11-08**; the
[latest bibliography](report/latest.references.json) records the separate
November 9 research checks. This editorial pass does not refresh external
prices or documentation. Start with the repository
contracts and use upstream material to verify platform behavior. A tutorial,
catalogue listing, or grant advertisement is not evidence that an account has
credit, a feature was integrated, or a deployment passed acceptance.

## Project context

| Read | Purpose |
| --- | --- |
| [Documentation map](README.md), [architecture](architecture.md), [accepted ADRs](adr/README.md) | Navigate the project and preserve evidence, applicability, and authorization as distinct checks |
| [Development](DEVELOPMENT.md), [testing](TESTING.md), [fleet guide](../fleet/README.md) | Continue from a fresh clone with scoped ownership and reproducible checks |
| [NixOS fleet](NIXOS_FLEET.md), [GCP deployment](DEPLOY_GCP.md), [operations](OPERATIONS.md) | Build, validate, operate, collect output, and clean up; configuration is distinct from observed boot/cloud acceptance |
| [Adaption](ADAPTION.md), [costs](COSTS.md), [security/policy](SECURITY_POLICY.md) | Distinguish recorded credits, implemented budget controls, provider qualification and authorized research scope |
| [Build status](BUILD_STATUS.md), [roadmap](ROADMAP.md), [AI assistance](AI_ASSISTANCE.md) | Recover observed evidence, implementation gaps, and provenance without a chat transcript |

## Research and submission

Start with the [latest report](report/latest.md), [public trial data](../data/paired-pilot-2026-11-09.json)
and [evidence guide](submission/latest/EVIDENCE.md). The [controlled-pilot runbook](CONTROLLED_PILOT.md)
records the qualified OpenRouter path separately from Adaption research.

- [Apart Swarm Alignment Sprint](https://apartresearch.com/sprints/swarm-alignment-2026):
  official tracks, resources, dates, and links to background research. Use the
  event's own resources section as the entry point to recommended reading.
- [Official guidelines](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines):
  verify the current report template, submission route, timing, eligibility,
  and disclosure requirements. [Submission preparation](SUBMISSION.md) records
  this project's scope. Repository publication is separate from submission.

Adaption grant descriptions on public pages need not match an existing
account's balance. The owner-confirmed $1,500 planning balance and its evidence
limits are recorded in [ADAPTION.md](ADAPTION.md); there is no four-person pooled
budget or automatic cloud-credit assumption.

## Provider integration

| Official source | Use and boundary |
| --- | --- |
| [Inference quickstart](https://docs.adaptionlabs.ai/inference-stacks/quickstart/) | API-key setup and Python Responses API; a live request is outside the default workflow |
| [Python SDK](https://docs.adaptionlabs.ai/api/python), [PyPI release](https://pypi.org/project/adaption/0.19.0/) | Historical SDK 0.19.0 reference, not a current install recommendation; the baseline has no SDK dependency |
| [Hosted models](https://docs.adaptionlabs.ai/inference-stacks/models/), [Responses reference](https://docs.adaptionlabs.ai/api/python/resources/responses/methods/create) | Hosted capabilities, credit units, request controls; account availability and USD conversion need separate verification |
| [FAQ](https://docs.adaptionlabs.ai/resources/faq/), [Adaptive Data configuration](https://docs.adaptionlabs.ai/adaptive-data/configure-adaptive-data/) | Dataset estimates and settings; distinct from inference and not an unbounded training budget |

## NixOS and deployment

- [Official NixOS GCE recipe](https://wiki.nixos.org/wiki/Install_NixOS_on_GCE)
  explains native images, KVM build requirements, and OS Login. Its example
  helper can make uploads/images public; use this repository's private-upload
  runbook instead of copying that helper wholesale.
- [Pinned GCE image module](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/nixos/modules/virtualisation/google-compute-image.nix)
  and [pinned container module](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/nixos/modules/virtualisation/nixos-containers.nix)
  are the implementation references. Read the actual pinned code before
  relying on behavior described for another revision.
- [dreamsofcode-io/nixos-vps](https://github.com/dreamsofcode-io/nixos-vps)
  is the reference VPS configuration discussed during planning. Its modular
  configuration, remote build/deploy approach, and encrypted-secret patterns
  are useful comparison points. Its Hostinger/Proxmox boot and filesystem
  assumptions must not replace the native GCE module. The reviewed
  [VPS base at revision `594211ef`](https://github.com/dreamsofcode-io/nixos-vps/blob/594211ef75c2d9b0ea2a75dd6f1cdda26752550c/vps_configuration.nix)
  configures BIOS boot and NoCloud/ConfigDrive provisioning for that platform;
  it is not a GCE image configuration. Recheck the revision and license before
  reuse. No code is copied here, and repository popularity is not validation.
- [systemd-nspawn](https://www.freedesktop.org/software/systemd/man/latest/systemd-nspawn.html),
  [execution sandboxing](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html),
  and [resource controls](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
  explain the mechanisms behind ADR-0008. Host boot checks still establish
  whether the configured restrictions work on the selected pin.

## Cloud operations and economical publication

Use [OS Login](https://docs.cloud.google.com/compute/docs/oslogin),
[IAP TCP forwarding](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding),
[service-account guidance](https://docs.cloud.google.com/compute/docs/access/service-accounts),
and [VPC firewall semantics](https://docs.cloud.google.com/firewall/docs/firewalls)
to check administration and credential boundaries. Metadata traffic is a
special case; VPC firewall rules do not confine it inside a VM.

For rates and lifecycle, consult the [GCP price tables](COSTS.md) and the
[Free Program](https://docs.cloud.google.com/free/docs/free-cloud-features).
[Spend cap budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)
cover selected API services and do not stop the persistent compute/storage in
this deployment. [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
and [Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage)
are alternatives for a reviewed static replay and public-repository checks,
subject to their current limits. No resource in this list promises that all
hosting, builders, model calls, or experiments are free.
