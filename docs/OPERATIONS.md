# Operations

Operate a reviewed checkout on a disposable NixOS VM. Provisioning, image
build/upload, IAP/OS Login SSH, optional public HTTPS, updates, and teardown are in
[DEPLOY_GCP](DEPLOY_GCP.md); spending and retained-resource costs are in
[COSTS](COSTS.md). These instructions describe operation, not evidence that a VM
has been deployed. Check [BUILD_STATUS](BUILD_STATUS.md) for observed verification.

## Inspect the replay service

The GCP configuration is `nixosConfigurations.fleet-gcp`. Its packaged synthetic
replay is `packages.x86_64-linux.demo`; `fleet-witness-demo.service` serves its
allowlisted assets at `127.0.0.1:8765` under an unprivileged account.
`services.fleetWitnessDemo.publicHostName` is an optional public HTTPS opt-in;
follow the deployment guide for domain, firewall, and proxy setup.

On the host, inspect the service and local HTTP response:

```sh
sudo systemctl status fleet-witness-demo.service --no-pager
sudo journalctl -u fleet-witness-demo.service -n 100 --no-pager
sudo systemctl show fleet-witness-demo.service -p ActiveState -p SubState -p Result
python3 - <<'PYHTTP'
import json
from urllib.request import urlopen
with urlopen('http://127.0.0.1:8765/replay.json', timeout=5) as response:
    replay = json.load(response)
print(replay['summary'])
PYHTTP
```

Use an SSH tunnel as documented in the deployment guide for private browser access.
Public HTTPS serves the scripted viewer, not a controller or remote agent API.
The SQLite file is not an HTTP asset. Never put credentials or sensitive evidence
in a replay intended for public access.

## Start and inspect offline workers

The GCP host declares `w-runtime`, `w-viewer`, `w-scenario`, and `w-review`, all
manually started. Each currently executes the same offline tests and fixture demo;
these names do not select roles or invoke coding/model agents. Start only the
workers needed for the check. For one worker:

```sh
sudo systemctl start container@w-runtime.service
sudo systemctl show container@w-runtime.service \
  -p ActiveState -p Result -p TimeoutStartUSec -p RuntimeMaxUSec -p ControlGroup
sudo systemctl -M w-runtime show fleet-task.service \
  -p ActiveState -p SubState -p Result -p ExecMainCode -p ExecMainStatus
sudo journalctl -u container@w-runtime.service -n 100 --no-pager
sudo journalctl -M w-runtime -u fleet-task.service --no-pager
```

Wait until the inner service leaves `activating`; task success requires
`active/exited`, `Result=success`, and `ExecMainStatus=0`. An active outer
container alone establishes none of these. Record outer and inner status and
collect output promptly. Inspect actual cgroups and confinement with the
[NixOS acceptance checklist](NIXOS_FLEET.md#required-boot-acceptance-checks-not-yet-executed).

| Budget | Configured value |
| --- | --- |
| Aggregate CPU / memory / tasks | 100% of one CPU / 1 GiB without swap / 256 |
| Writable `/work` tmpfs | 512 MiB |
| Inner task startup/run timeout | 10 minutes |
| Outer startup allowance | 12 minutes |
| Outer active lifetime after readiness | 15 minutes |

Readiness can wait for the boot-attached task. The 15-minute lifetime begins after
readiness; startup and active budgets can add to approximately 27 minutes before
shutdown handling. Automatic restarts are disabled. These are configured limits,
not measured capacity or a 15-minute launch-to-stop guarantee. Workers share the
host kernel; worktrees and containers do not prove isolation from hostile code.
Do not grant workers sudo, systemd administration, or host/provider credentials.

## Collect results before stopping

Results live in ephemeral `/work/task/results`, including `report.txt`,
`tests.log`, `viewer.log`, and `demo.log`. Use the existing
[bounded collector](NIXOS_FLEET.md#collect-before-stopping) as the trusted operator:
record status, freeze output mutation, copy only its allowlisted regular singly
linked files into fresh quarantine, then thaw and stop. Adjust the exact worker
name consistently when operating a different worker. If freezing or validation
fails, investigate; recursive copying is not a recovery path.

The collector intentionally omits the database, replay directory, patches, and
archives. Inspect quarantined logs as untrusted text and compare them with
systemd state and an independent reproduction. Do not execute report contents,
automatically apply patches, or treat a worker-written success message as proof.
Stop or expiry destroys uncollected output; collect before either. Ephemeral
roots do not erase host journals or ordinary Nix profile/gcroot state.

## Diagnose and recover

If startup fails, inspect both journals before restarting. Check timeout results,
resource limits, available host memory, and `/work` capacity; a missing report
can mean timeout or an interrupted/full-disk task. Collect allowed evidence
before teardown. A subsequent start is a new task with new ephemeral state.
Do not disable limits or silently grant a retry another budget to hide failure.

For a viewer failure, inspect service logs and the loopback response first, then
IAP/tunnel or optional DNS/TLS/proxy settings using the deployment guide. Reproduce
with the local [testing](TESTING.md) commands before attributing a fixture failure
to cloud networking.

The image preserves its exact Nix source at `/etc/fleet-witness/source`. Generic
`/etc/nixos` rebuilds are deliberately refused: use the explicit `--flake` target
ending in `#fleet-gcp` in the deployment update procedure. Configuration rollback
restores a reviewed NixOS generation; retain administration access while testing it.
It does not resume a historical experiment. Signing keys exist only in memory,
saved databases are inspection artifacts, and no database resume command exists.
Generate a new replay into a fresh output for a fresh run. Keep exact commit,
configuration, status, and collected evidence with an incident report.
