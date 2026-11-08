# Deployment costs and spending controls

Planning snapshot: **2026-11-08**, USD list prices, `us-central1`, ordinary
on-demand Linux Compute Engine. The local `scripted-demo`, tests, and replay
viewer need no external spend. No cloud resources or paid model calls were
created for this handoff. The owner's [Adaption balance](ADAPTION.md) is separate
from GCP billing; no GCP promotional credit or discount is assumed here.

## One VM with offline workers

The workers are containers on one host, not four separately billed VMs.
Configured per-worker limits are one CPU and 1 GiB; those are ceilings, not
measured demand. An `e2-standard-2` can be a sequential smoke-test host.
`e2-standard-4` gives four workers more CPU room, with host/service memory
headroom. Neither sizing recommendation is a benchmark or a guarantee against
resource pressure; start workers manually and measure. Image building needs a
separate x86_64 Linux KVM-capable builder, whose costs are excluded below.

| Component | Assumption | USD per hour |
| --- | --- | ---: |
| Small runtime VM | `e2-standard-2`, 2 vCPU, 8 GiB | 0.06701142 |
| Larger runtime VM | `e2-standard-4`, 4 vCPU, 16 GiB | 0.13402284 |
| Boot disk | 50 GiB zonal `pd-balanced` × 0.000136986/GiB/hour | 0.00684930 |
| Public address | One in-use external IPv4 | 0.00500000 |

Primary prices: [general purpose VMs](https://cloud.google.com/products/compute/pricing/general-purpose),
[disk and image pricing](https://cloud.google.com/compute/disks-image-pricing),
and [network and external IP pricing](https://cloud.google.com/vpc/network-pricing).
Confirm the selected region and account price before provisioning.

| Continuous runtime | Small VM + disk + IPv4 | Larger VM + disk + IPv4 |
| --- | ---: | ---: |
| 48 hours | $3.7853 | $7.0019 |
| 72 hours | $5.6780 | $10.5028 |
| 730 hours (planning month) | $57.5683 | $106.4867 |

Reproduce with `hours × (VM_hourly + 50 × 0.000136986 + 0.005)`.
The table assumes disk and address remain allocated for the entire interval.
It excludes image/snapshot storage, upload-bucket object storage, data transfer,
builder machines, DNS/domain registration, optional logging, other services,
and taxes. There is no GPU in this plan. A **$15 planning allowance for 72 hours**
of the larger runtime leaves some margin over the listed components; it is
not an enforced cap or a complete quote for all excluded items.

## Controls and cleanup

Use a dedicated project and explicit region, labels, budget notifications, a
named owner, and a cleanup checklist. Set alert thresholds below the planning
allowance; monitor billing and the resource inventory during the experiment.
Alerts can arrive after usage and are not a Compute Engine spending ceiling.

Google now offers [spend cap budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)
for eligible API services: Gemini API, Gemini Enterprise Agent Platform, Cloud
Run, and Cloud Run functions. They do **not** pause ongoing fixed usage such as
Compute Engine and storage. Even eligible in-flight requests can finish and
accrue charges. Do not treat these caps as protection for this VM plan.

The deployment runbook's VM runtime limit is **12 hours per start**, not an
absolute lifetime or dollar limit: restarting can grant a new interval.
Worker startup and active-lifetime limits are separate and do not stop the
host's cloud bill. See [GCP deployment](DEPLOY_GCP.md) and
[worker lifecycle details](NIXOS_FLEET.md).

[Stopping a VM](https://docs.cloud.google.com/compute/docs/instances/stop-start-instance)
ends its running compute charges, but retained disks and reserved static
addresses can remain billable. Unused reserved IP pricing may differ from the
in-use rate in the table. Images, snapshots, and upload objects also outlive
the VM unless deleted separately. After collecting needed results, follow the
runbook's deletion steps and inspect instances, disks, addresses, images,
snapshots, buckets/objects, and optional services. Confirm the actual remaining
inventory and subsequent billing; an empty worker or stopped VM is insufficient.

## Free options and their limits

The [GCP Free Program](https://docs.cloud.google.com/free/docs/free-cloud-features)
offers eligible new accounts a $300, 90-day trial, and a restricted Compute
Engine free tier using an `e2-micro` in selected US regions. Eligibility,
account status, quotas, storage/network limits, and excluded products matter.
The [general purpose VM table](https://cloud.google.com/products/compute/pricing/general-purpose)
lists 1 GiB RAM for `e2-micro`; it is not a suitable four-worker host when each
worker may use 1 GiB. No free-tier entitlement was verified for this owner.

For a public synthetic replay, [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
is static hosting available for public repositories on GitHub Free. Standard
GitHub-hosted [Actions runners](https://docs.github.com/en/actions/concepts/billing-and-usage)
are free for public repositories under the documented terms; larger runners
and other paid features have separate rules. Pages can serve reviewed viewer
assets and a sanitized replay, not Python processes, SQLite, development
workers, or a model gateway. No Pages deployment or Actions billing entitlement
is created by this guide. Recheck current service limits before publication.
