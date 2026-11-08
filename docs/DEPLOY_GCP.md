# Deploy Fleet Witness on Google Compute Engine

This is the operator procedure for the implemented **scripted-demo** viewer and
four offline development workers. It serves a packaged, read-only replay; it does
not connect to models, dispatch coding agents, operate sensors, or show a live
global fleet. Default development costs nothing; provisioning below is a separate
**manual cloud phase that creates billable resources**. Review [costs](COSTS.md)
and choose a run window before starting it. Adaption credit is a separate budget.

[BUILD_STATUS](BUILD_STATUS.md) records observed checks. A real committed lock,
Nix evaluation, and demo/offline derivation builds are available; full GCE image
build, VM boot, worker containment, OS Login/IAP, and deployed TLS acceptance
remain unverified until actually executed. Keep each evidence level distinct.
The design extends [ADR-0008](adr/0008-ephemeral-nixos-workers.md) and
[ADR-0005](adr/0005-replay-and-viewer.md); see [ADR-0009](adr/0009-gcp-deployment.md).

## 1. Prepare the operator, project, and builder

Use a dedicated existing GCP project with billing enabled, Compute Engine,
Cloud Storage and IAP permitted, and quota for four E2 vCPUs, a 50 GiB balanced
persistent disk, an external IPv4 address, and a custom image in the selected
region. Check organization restrictions on external addresses, OS Login, and
IAP before provisioning. Install a current [Google Cloud CLI](https://docs.cloud.google.com/sdk/docs/install)
on the trusted operator machine and use its normal interactive authentication.
Keep its credentials and SSH keys outside the checkout and the Nix store.

Separate cloud provisioning from everyday VM operation. A project administrator
assigns the provisioner only the permissions needed for APIs, private bucket,
images/disks/instances, network/firewall and IAM changes. Relevant predefined
roles include Service Usage Admin, Storage Admin, Compute Storage Admin,
Compute Instance Admin (v1), Compute Network Admin, and Compute Security Admin;
IAM grants require a separate IAM administrator. Prefer narrower resource-scoped
or custom permissions for an established deployment; do not grant Owner to workers.
The trusted operator needs OS Login administration, IAP tunneling, and Compute
Viewer, as configured in section 4. OS Login sudo is host authority: it is never
a worker tool. External-organization operators may also need the organization-level
[OS Login External User role](https://docs.cloud.google.com/compute/docs/oslogin/set-up-oslogin).

The image builder must be **x86_64 Linux with usable `/dev/kvm`** and sufficient
memory, disk and dependency-fetch access. Native GCE image creation runs a build
VM; ordinary Cloud Shell and an E2 VM without nested KVM are unsuitable builders.
Use a local KVM host or a separately reviewed remote builder. E2 is suitable for
the deployed host: systemd-nspawn workers do not need nested virtualization.
Fetching Nix inputs/substitutes uses network access even when application tests
are offline. The committed pin is `c56a87d8e41ce69bd2af57eb35dcc117a9dfca33`;
keep `flake.lock` and review any deliberate update.

## 2. Clone, test, configure, and record provenance

Follow [DEVELOPMENT](DEVELOPMENT.md) and [TESTING](TESTING.md) to continue work,
including task worktrees, ownership and review. On the trusted build machine:

```sh
git clone https://github.com/k2jac9/fleet-witness.git
cd fleet-witness
cp deploy/gcp.env.example .env.gcp
# Edit .env.gcp: existing project, unique bucket, operator and optional domain.
. ./.env.gcp
: "${FW_PROJECT:?}" "${FW_BUCKET:?}" "${FW_OPERATOR_EMAIL:?}"
test "$FW_PROJECT" != replace-with-existing-project-id
test "$FW_BUCKET" != replace-with-globally-unique-build-bucket
test "$FW_OPERATOR_EMAIL" != replace-with-operator@example.org
nix develop --command python -m unittest discover -s tests -v
nix develop --command node --test tests/viewer.test.mjs
nix develop --command python scripts/fleet.py validate
nix develop --command python scripts/fleet.py plan
```

`.env.gcp` is ignored. Source it only after reviewing its shell content; it holds
identifiers, never secrets. Examples use Bash/POSIX shell with variables retained
between blocks. Run these manual snippets one command at a time; stop on any
failed command and resolve it before continuing. Resource commands select the
project explicitly; authentication is global, and project-level commands name the
project as a positional argument. Check account and billing using read-only
commands before changes:

```sh
gcloud auth list
gcloud projects describe "$FW_PROJECT"
gcloud billing projects describe "$FW_PROJECT"
gcloud compute regions describe "$FW_REGION" --project="$FW_PROJECT"
```

If opting into public HTTPS before image build, first make the tracked Nix change
in section 7. Commit every reviewed source/configuration change, including new
files: Git-backed flakes exclude untracked files. Require a clean tracked commit
and no unexpected untracked inputs, then create an evidence directory outside it:

```sh
git diff --exit-code
git diff --cached --exit-code
test -z "$(git ls-files --others --exclude-standard)"
FW_REV=$(git rev-parse HEAD)
FW_IMAGE="fleet-witness-$(git rev-parse --short=12 HEAD)"
FW_OBJECT="$FW_IMAGE.tar.gz"
FW_BOOT_DISK="$FW_VM"
mkdir -p "$FW_EVIDENCE"
chmod 700 "$FW_EVIDENCE"
printf '%s\n' "$FW_REV" > "$FW_EVIDENCE/source-commit.txt"
cp flake.lock "$FW_EVIDENCE/flake.lock"
```

The image retains this public source at `/etc/fleet-witness/source`, including
its lock. Ignored files are not a secret-management mechanism: inspect all tracked
inputs; no keys, private datasets, or provider credentials may enter the source,
Nix expressions, image, VM metadata or replay. Synthetic demo keys stay in the
build sandbox; the packaged viewer includes no database. See [security](SECURITY_POLICY.md).

## 3. Evaluate and build the native image

Run on the builder, from the clean reviewed checkout. These evaluations/builds
must succeed before uploading anything:

```sh
nix eval --raw .#nixosConfigurations.fleet-gcp.config.system.build.googleComputeImage.drvPath
nix eval --json .#nixosConfigurations.fleet-gcp.config.security.googleOsLogin.enable
nix eval --json .#nixosConfigurations.fleet-gcp.config.networking.firewall.enable
nix eval --json .#nixosConfigurations.fleet-gcp.config.services.fleetWitnessDemo.publicHostName
nix build .#checks.x86_64-linux.offline-tests --no-link
FW_DEMO_OUT=$(nix build .#demo --no-link --print-out-paths)
"$FW_DEMO_OUT/bin/fleet-witness-demo"
```

The last command serves loopback port 8765; inspect `http://127.0.0.1:8765` in a
second terminal, then Ctrl-C. Expect the scripted label and 20 episodes, 13
approvals, 7 invalid recommendations, 15 attempts, 4 effects and 9 denials.
The two authorized duplicates are no-ops. Default evaluations return OS Login
`true`, guest firewall `true`, and public hostname `null`.

Build the actual image, deriving its archive name from the configuration instead
of guessing an upstream filename:

```sh
test -c /dev/kvm && test -r /dev/kvm && test -w /dev/kvm
FW_IMAGE_OUT=$(nix build \
  .#nixosConfigurations.fleet-gcp.config.system.build.googleComputeImage \
  --no-link --print-out-paths)
FW_IMAGE_FILE=$(nix eval --raw .#nixosConfigurations.fleet-gcp.config.image.fileName)
FW_ARCHIVE="$FW_IMAGE_OUT/$FW_IMAGE_FILE"
test -f "$FW_ARCHIVE"
sha256sum "$FW_ARCHIVE" > "$FW_EVIDENCE/image-sha256.txt"
tar -tzf "$FW_ARCHIVE"
printf '%s\n' "$FW_IMAGE_OUT" "$FW_ARCHIVE" > "$FW_EVIDENCE/image-paths.txt"
```

Expect a gzip tar archive containing `disk.raw`. A successful derivation evaluation
or demo build is not an image build, and a built image is not a boot test. The
[native NixOS GCE module](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/nixos/modules/virtualisation/google-compute-image.nix)
is the source of this target. Do not use public-upload helper scripts.

## 4. Manual cloud phase: private image, IAM, and network

The provisioner performs this phase in the explicitly selected existing project.
API enablement and IAM grants change project state; bucket/image/VM use can incur
charges. There are no cloud calls in the normal application tests.

```sh
gcloud services enable compute.googleapis.com storage.googleapis.com iap.googleapis.com \
  --project="$FW_PROJECT"
gcloud storage buckets create "gs://$FW_BUCKET" --project="$FW_PROJECT" \
  --location="$FW_REGION" --uniform-bucket-level-access --public-access-prevention
```

This new build-only bucket is private. [Bucket creation](https://docs.cloud.google.com/sdk/gcloud/reference/storage/buckets/create)
defaults to seven-day soft deletion. To intentionally give up deleted-object
recovery and avoid that retention for a disposable image staging bucket, add
`--soft-delete-duration=0` **to its creation command**. Record the choice; retain
evidence elsewhere. Do not repurpose an evidence bucket or silently change an
existing bucket's protection. [Soft delete](https://docs.cloud.google.com/storage/docs/soft-delete)
can retain billed data after deletion. Never add `allUsers` or `allAuthenticatedUsers`.

```sh
gcloud storage cp "$FW_ARCHIVE" "gs://$FW_BUCKET/$FW_OBJECT" --project="$FW_PROJECT"
gcloud compute images create "$FW_IMAGE" --project="$FW_PROJECT" \
  --source-uri="https://storage.googleapis.com/$FW_BUCKET/$FW_OBJECT" \
  --storage-location="$FW_REGION" \
  --description="Fleet Witness source $FW_REV; scripted-demo; native NixOS GCE"
gcloud compute images describe "$FW_IMAGE" --project="$FW_PROJECT" \
  --format=json > "$FW_EVIDENCE/cloud-image.json"
```

The full HTTPS Cloud Storage URI is the [image source URI](https://docs.cloud.google.com/sdk/gcloud/reference/compute/images/create),
not an instruction to make the object public. Use the same project for bucket
and image; the authenticated provisioning flow needs access to the private source.
Wait for image status `READY`. No public image IAM binding is created.

An IAM administrator grants the operator these project-scoped roles for this
dedicated project. Review existing conditional bindings rather than overwriting
policy. See [OS Login setup](https://docs.cloud.google.com/compute/docs/oslogin/set-up-oslogin)
and [IAP permissions](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding).

```sh
for role in roles/compute.osAdminLogin roles/iap.tunnelResourceAccessor roles/compute.viewer; do
  gcloud projects add-iam-policy-binding "$FW_PROJECT" \
    --member="user:$FW_OPERATOR_EMAIL" --role="$role" --condition=None
done
gcloud compute networks create "$FW_NETWORK" --project="$FW_PROJECT" --subnet-mode=custom
gcloud compute networks subnets create "$FW_SUBNET" --project="$FW_PROJECT" \
  --network="$FW_NETWORK" --region="$FW_REGION" --range="$FW_SUBNET_RANGE"
gcloud compute firewall-rules create "$FW_SSH_RULE" --project="$FW_PROJECT" \
  --network="$FW_NETWORK" --direction=INGRESS --action=ALLOW \
  --rules=tcp:22 --source-ranges=35.235.240.0/20 --target-tags="$FW_TAG"
```

This custom VPC receives no default public SSH rule. Only IAP's documented source
range can reach TCP 22; the guest firewall independently permits SSH. IAP is an
administration access path, **not outbound internet connectivity**. The VM below
uses an ephemeral external IPv4 address for host dependency fetches and optional
ACME; workers retain ADR-0008 private networking and no NAT. A no-external-address
variant requires separately designed egress, such as Cloud NAT, with its own costs.

## 5. Create and accept the VM

The provisioner creates one disposable host. The explicit no-service-account and
no-scopes flags prevent attaching the project's default workload identity:

```sh
gcloud compute instances create "$FW_VM" --project="$FW_PROJECT" \
  --zone="$FW_ZONE" --machine-type="$FW_MACHINE_TYPE" \
  --image="$FW_IMAGE" --image-project="$FW_PROJECT" \
  --boot-disk-size="${FW_BOOT_DISK_GB}GB" --boot-disk-type=pd-balanced \
  --boot-disk-auto-delete \
  --network="$FW_NETWORK" --subnet="$FW_SUBNET" --tags="$FW_TAG" \
  --no-service-account --no-scopes \
  --metadata=enable-oslogin=TRUE,block-project-ssh-keys=TRUE \
  --max-run-duration=12h --instance-termination-action=STOP --no-restart-on-failure
```

The [instance CLI reference](https://docs.cloud.google.com/sdk/gcloud/reference/compute/instances/create)
defines these flags. The automatic stop is twelve hours from each start; starting
again resets that duration. It does not delete the boot disk, images, or reserved
addresses. See [VM runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime).
The boot disk is named after the VM and auto-deletes only when the VM is deleted.
Record the actual configuration and serial boot output:

```sh
gcloud compute instances describe "$FW_VM" --project="$FW_PROJECT" --zone="$FW_ZONE" \
  --format=json > "$FW_EVIDENCE/instance.json"
gcloud compute instances get-serial-port-output "$FW_VM" \
  --project="$FW_PROJECT" --zone="$FW_ZONE" > "$FW_EVIDENCE/serial-boot.txt"
gcloud compute ssh "$FW_VM" --account="$FW_OPERATOR_EMAIL" \
  --project="$FW_PROJECT" --zone="$FW_ZONE" --tunnel-through-iap
```

Authenticate the operator account separately before SSH. Check the recorded VM has no `serviceAccounts`,
the intended image/disk/network/tag, OS Login metadata, and scheduled stop. On host:

```sh
sudo -v
sudo systemctl status fleet-witness-demo.service --no-pager
sudo journalctl -u fleet-witness-demo.service -n 100 --no-pager
curl --fail --silent http://127.0.0.1:8765/replay.json | python3 -m json.tool
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  http://127.0.0.1:8765/witness.sqlite3
readlink -f /etc/fleet-witness/source
cat /etc/fleet-witness/source/flake.lock
sudo ss -lntup
```

Expect an active service, the section 3 summary, HTTP `404` for SQLite, a retained
source with the lock, and the viewer listening only on `127.0.0.1:8765`. Workers
must not be running automatically. On the operator machine, open a second session:

```sh
gcloud compute ssh "$FW_VM" --account="$FW_OPERATOR_EMAIL" \
  --project="$FW_PROJECT" --zone="$FW_ZONE" --tunnel-through-iap -- \
  -o ExitOnForwardFailure=yes -N -L 127.0.0.1:8765:127.0.0.1:8765
```

Open `http://127.0.0.1:8765` locally and perform [browser acceptance](TESTING.md#http-and-manual-browser-acceptance).
Leave the tunnel running; Ctrl-C closes it. If local 8765 is occupied, use 18765
on the left side and open that port. No GCP ingress for 8765 is needed.

## 6. Start workers and preserve evidence

The host defines `w-runtime`, `w-viewer`, `w-scenario`, and `w-review`, with manual
starts. All currently run the same offline tests/demo; names do not dispatch
models or role-specific agents. On the host, start one at a time initially:

```sh
sudo systemctl start container@w-runtime.service
sudo systemctl show container@w-runtime.service \
  -p ActiveState -p Result -p TimeoutStartUSec -p RuntimeMaxUSec -p ControlGroup
sudo systemctl -M w-runtime show fleet-task.service \
  -p ActiveState -p SubState -p Result -p ExecMainStatus
sudo journalctl -M w-runtime -u fleet-task.service --no-pager
```

Require inner `active/exited`, `Result=success`, and `ExecMainStatus=0`, then
use the [bounded collector](NIXOS_FLEET.md#collect-before-stopping) **before stop
or expiry**. It freezes the worker and copies only small allowlisted regular
files to fresh host quarantine, recording host/inner systemd status. Preserve
that quarantine on the operator machine with `gcloud compute scp --recurse
--tunnel-through-iap --account="$FW_OPERATOR_EMAIL" --project="$FW_PROJECT"
--zone="$FW_ZONE" "$FW_VM:/absolute/quarantine/path" "$FW_EVIDENCE/"` after substituting the actual
trusted collector path. Inspect untrusted report text; execute none of it.

ADR-0008 limits remain: one CPU, 1 GiB memory/no swap, 256 tasks, 512 MiB `/work`,
10-minute inner task timeout, 12-minute outer startup allowance, then 15-minute
active container lifetime after readiness. Startup and active budgets add; this
is not a 15-minute launch-to-stop promise. Restart is disabled. Stop or VM expiry
destroys uncollected worker state. Containers share the host kernel. Complete
[NixOS boot/containment acceptance](NIXOS_FLEET.md#required-boot-acceptance-checks-not-yet-executed)
on the disposable host before claiming isolation. [OPERATIONS](OPERATIONS.md)
covers status, outputs and failure handling. No database-resume command exists;
new experiments require fresh outputs and synthetic keys are not persisted.

## 7. Optional public HTTPS

Public access is an explicit configuration change. Keep the replay synthetic;
it exposes evaluator results and is unsuitable as future supervisor input.
Choose a real FQDN you control. In tracked `nix/hosts/gcp.nix`, set:

```nix
services.fleetWitnessDemo.publicHostName = "fleet.example.org";
```

Replace that example with the real hostname, review and commit before section 2's
provenance/build steps, or apply it through the reviewed host rebuild in section 8.
Setting `FW_DOMAIN` or DNS alone does not change NixOS. The option enables Caddy,
its reverse proxy to loopback, and guest TCP 80/443 plus UDP 443. Default `null`
keeps application ingress closed. [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
needs correct DNS, reachable validation ports and outbound certificate access.

To preserve the running VM's ephemeral IPv4 address, promote it to a regional
static reservation before publishing DNS (operator machine, provisioner identity):

```sh
FW_PUBLIC_IP=$(gcloud compute instances describe "$FW_VM" --project="$FW_PROJECT" \
  --zone="$FW_ZONE" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')
test -n "$FW_PUBLIC_IP"
gcloud compute addresses create "$FW_STATIC_ADDRESS" --project="$FW_PROJECT" \
  --region="$FW_REGION" --addresses="$FW_PUBLIC_IP"
gcloud compute firewall-rules create "$FW_HTTPS_RULE" --project="$FW_PROJECT" \
  --network="$FW_NETWORK" --direction=INGRESS --action=ALLOW \
  --rules=tcp:80,tcp:443,udp:443 --source-ranges=0.0.0.0/0 --target-tags="$FW_TAG"
```

[Address promotion](https://docs.cloud.google.com/compute/docs/ip-addresses/configure-static-external-ip-address)
keeps the attached address; do not remove its access configuration. Alternatively,
reserve a regional address before VM creation and pass its address with `--address`
to section 5. Publish a DNS A record for the real `FW_DOMAIN` pointing to that
address through your DNS provider. Publish no AAAA record without a separately
configured IPv6 path. Wait for public DNS resolution before checking certificates.

After switching the reviewed configuration, on the host run `sudo systemctl
status caddy --no-pager` and `sudo journalctl -u caddy -n 100 --no-pager`. From
outside the VM run `curl --fail --head "https://$FW_DOMAIN/"` and fetch
`https://$FW_DOMAIN/replay.json`; require a valid certificate and expected fixture.
HTTP should redirect to HTTPS; SQLite stays 404. Verify actual guest/GCP rules
and TCP/UDP listeners. No public controller, worker interface, or live fleet is
created. To withdraw access, delete the exact public firewall rule, set the option
back to `null` in a reviewed rebuild, and remove DNS/static IP if no longer needed.

## 8. Updates and recovery

Keep a known-good image, source revision/lock, evidence and a second working
IAP/OS Login session while changing host configuration. Use the image's preserved
source for an identical-configuration rebuild:

```sh
FW_PREVIOUS_SYSTEM=$(readlink -f /run/current-system)
test -x "$FW_PREVIOUS_SYSTEM/bin/switch-to-configuration"
printf 'Known-good running system: %s\n' "$FW_PREVIOUS_SYSTEM"
sudo nixos-rebuild test --flake /etc/fleet-witness/source#fleet-gcp
# Recheck a new SSH session, sudo, loopback viewer and any enabled HTTPS.
# Continue only after acceptance succeeds; otherwise use test recovery below.
sudo nixos-rebuild switch --flake /etc/fleet-witness/source#fleet-gcp
```

For updates, clone the public repository to a protected operator-owned host path,
check out an exact reviewed commit, retain deliberate hostname/worker settings in
tracked configuration, and commit/review those settings. Never rebuild a dirty
checkout or overwrite the preserved source symlink. Allocate a fresh directory
under a protected deployment parent for every update, preserving old checkouts
and evidence. On the host (replace the revision before running):

```sh
FW_UPDATE_REV=replace-with-exact-reviewed-commit
sudo install -d -m 0750 -o "$(id -u)" -g "$(id -g)" /var/lib/fleet-witness-deploy
FW_UPDATE_DIR=$(mktemp -d /var/lib/fleet-witness-deploy/update.XXXXXX)
git clone https://github.com/k2jac9/fleet-witness.git "$FW_UPDATE_DIR"
git -C "$FW_UPDATE_DIR" checkout --detach "$FW_UPDATE_REV"
# Apply/review/commit any retained hostname or worker settings before continuing.
git -C "$FW_UPDATE_DIR" diff --exit-code
git -C "$FW_UPDATE_DIR" diff --cached --exit-code
test -z "$(git -C "$FW_UPDATE_DIR" ls-files --others --exclude-standard)"
git -C "$FW_UPDATE_DIR" rev-parse HEAD
FW_PREVIOUS_SYSTEM=$(readlink -f /run/current-system)
test -x "$FW_PREVIOUS_SYSTEM/bin/switch-to-configuration"
printf 'Known-good running system: %s\n' "$FW_PREVIOUS_SYSTEM"
sudo nixos-rebuild test --flake "$FW_UPDATE_DIR#fleet-gcp"
# Verify access and services in a second SSH session before making it persistent.
# Continue only after acceptance succeeds; otherwise use test recovery below.
sudo nixos-rebuild switch --flake "$FW_UPDATE_DIR#fleet-gcp"
```

The new generation preserves its own source snapshot. Keep OS Login enabled and
the intended firewall/IAP path; do not substitute the upstream generic GCE config.
`/etc/nixos/configuration.nix` intentionally throws an instruction to use this
explicit flake, preventing an accidental rebuild that silently removes Fleet
Witness. `test` changes the running generation without making it the boot default;
`switch` activates and makes it persistent. Review [NixOS rebuild behavior](https://nixos.org/manual/nixos/stable/#sec-changing-config).

Before either `test`, retain the printed `FW_PREVIOUS_SYSTEM` path outside that
SSH session. Variables are not shared between sessions: copy the recorded path
into `FW_PREVIOUS_SYSTEM` in the recovery session if needed. If test acceptance
fails while SSH still works, restore that exact previously running system:

```sh
sudo "$FW_PREVIOUS_SYSTEM/bin/switch-to-configuration" test
```

Recheck access and services. This restores the running configuration while leaving
the boot profile unchanged. Do not use persistent profile rollback for a failed
`test`; on the first image there may be no older boot generation to select.

Only after a persistent `switch` advanced the system profile, inspect
`sudo nix-env --list-generations -p /nix/var/nix/profiles/system` and confirm the
previous generation is the intended known-good configuration before using
`sudo nixos-rebuild switch --rollback`. Inspect the selected generation again and
recheck access/services. If SSH is broken, use the provisioner to inspect
serial output, preserve the stopped disk if evidence is needed, and create a
replacement VM from the known-good image with section 5's access settings and a
new VM name. Do not assume a GRUB menu or an already configured serial root login.
Keep the old disk until evidence review, then delete its exact resource. Rollback
restores configuration, not previous in-memory experiments or signing keys.

## 9. Inventory, stop, and tear down

Collect worker output before its shorter lifetime and export all host evidence
before the VM's scheduled stop. Record exact resource names/IDs, image digest,
source/lock, real service results, serial logs, DNS and optional IP reservation.
Before deletion, review this deployment's inventory using its actual names:

```sh
gcloud compute instances describe "$FW_VM" --project="$FW_PROJECT" --zone="$FW_ZONE"
gcloud compute disks describe "$FW_BOOT_DISK" --project="$FW_PROJECT" --zone="$FW_ZONE"
gcloud compute images describe "$FW_IMAGE" --project="$FW_PROJECT"
gcloud storage ls "gs://$FW_BUCKET/$FW_OBJECT" --project="$FW_PROJECT"
gcloud compute firewall-rules describe "$FW_SSH_RULE" --project="$FW_PROJECT"
gcloud compute networks subnets describe "$FW_SUBNET" --project="$FW_PROJECT" --region="$FW_REGION"
gcloud compute networks describe "$FW_NETWORK" --project="$FW_PROJECT"
gcloud compute instances stop "$FW_VM" --project="$FW_PROJECT" --zone="$FW_ZONE"
```

Stopping retains a billed boot disk and image; reserved IPv4 can also incur
charges. The runtime limit and billing alerts are not complete spending caps.
After preserving evidence, the provisioner deletes **only these named resources**:

```sh
gcloud compute instances delete "$FW_VM" --project="$FW_PROJECT" --zone="$FW_ZONE"
# Its auto-delete boot disk should disappear; describe it again to verify.
# If deliberately retained/detached, review it, then delete that exact disk:
# gcloud compute disks delete "$FW_BOOT_DISK" --project="$FW_PROJECT" --zone="$FW_ZONE"
gcloud compute images delete "$FW_IMAGE" --project="$FW_PROJECT"
gcloud storage rm "gs://$FW_BUCKET/$FW_OBJECT" --project="$FW_PROJECT"
gcloud storage buckets delete "gs://$FW_BUCKET" --project="$FW_PROJECT"
# Run only if optional public HTTPS resources were actually created:
# gcloud compute firewall-rules delete "$FW_HTTPS_RULE" --project="$FW_PROJECT"
# gcloud compute addresses delete "$FW_STATIC_ADDRESS" --project="$FW_PROJECT" --region="$FW_REGION"
gcloud compute firewall-rules delete "$FW_SSH_RULE" --project="$FW_PROJECT"
gcloud compute networks subnets delete "$FW_SUBNET" --project="$FW_PROJECT" --region="$FW_REGION"
gcloud compute networks delete "$FW_NETWORK" --project="$FW_PROJECT"
```

Delete public DNS records when withdrawing the service. [Named bucket deletion](https://docs.cloud.google.com/sdk/gcloud/reference/storage/buckets/delete)
requires an empty bucket. An empty-bucket check
must succeed; inspect unexpected objects/versions rather than recursively deleting
a bucket. Verify the listed resources are gone and review billing for soft-deleted
storage or retained recovery disks/snapshots/images/static addresses. Remove only
IAM bindings newly granted exclusively for this deployment, after reviewing their
other uses; never delete the project, inherited policy, or shared resources.

## Troubleshooting

| Symptom | Check and action |
| --- | --- |
| Image build requires `kvm` / permission denied | Use an x86_64 Linux KVM-capable builder with daemon access; Cloud Shell/E2 runtime is not that builder. Do not bypass sandboxing to claim a build. |
| Missing new flake file / old configuration | Add, review and commit files; verify clean HEAD and lock. Flakes omit untracked Git files. |
| IAP denied or SSH hangs | Check selected account/project, IAP role, Compute Viewer, OS Admin Login, OS Login metadata, SSH service, VM tag and both firewalls. Keep source TCP 22 restricted to IAP. |
| OS Login user cannot sudo | Require `roles/compute.osAdminLogin`, not only `osLogin`; external organizations may require an organization-level grant. No attached service account is needed. |
| Host cannot fetch dependencies | IAP supplies ingress only; confirm the ephemeral/static IPv4 and VPC route/egress, or the separately designed NAT. Workers intentionally have no internet. |
| Generic rebuild throws | Use the explicit `--flake /etc/fleet-witness/source#fleet-gcp` or reviewed updated checkout; the source-preservation guard is intentional. |
| Worker times out / output absent | Inspect outer and inner journals/results and limits; collect before the active lifetime or VM stop. Outer active state is not task success. See OPERATIONS. |
| TLS fails | Check public A/AAAA, static IP, real tracked hostname, Caddy logs, outbound ACME, and matching GCP/guest 80/443 TCP and 443 UDP rules. |
| Provider API unavailable / budget unknown | No live provider exists in this image. Follow the separate [Adaption proposal](ADAPTION.md); never put provider keys in workers or treat GCP billing as the Adaption ledger. |
