# Experiment 2: independent human reproduction handoff

Status: **human reproduction pending**. This document is a procedure and an
unfilled record, not a completed review. See the
[dated publication report](2026-11-16-experiment2-publication.md) for scope and
the [recovery report](2026-11-16-experiment2-recovery.md) for historical limits.

## Choose the revision and workspace

A second person should select the full 40-character commit SHA from the reviewed
publication PR, record their identity/date, and use a fresh checkout. Do not infer
the reviewed revision from the moving `main` branch. Use the current stable
Python in `ci/runtime-matrix.json`; Python 3.11+ is supported and only the standard
library is needed. Clone access uses the network; the verification commands below
do not. No model account or credentials are needed for verification.

On the owner's workstation, source must be under `~/Projects`, retained evidence
under the project artifact directory, and storage admission must precede substantial
work. Expected additional disk use is below 0.5 GiB, with no extraction or runtime
download. A temporary exception from another session must not be assumed active.

Set `FW_REVIEW_COMMIT` to the exact reviewed SHA before running this block:

```sh
set -eu
: "${FW_REVIEW_COMMIT:?Set the full reviewed commit SHA first}"
test "${#FW_REVIEW_COMMIT}" -eq 40
case "$FW_REVIEW_COMMIT" in *[!0-9a-f]*) exit 1 ;; esac
mkdir -p "$HOME/Projects/fleet-witness-artifacts"
checkout_dir=$(mktemp -d "$HOME/Projects/fleet-witness-review.XXXXXXXX")
record_dir=$(mktemp -d "$HOME/Projects/fleet-witness-artifacts/experiment2-human-review.XXXXXXXX")
git clone --no-checkout https://github.com/k2jac9/fleet-witness.git "$checkout_dir"
git -C "$checkout_dir" checkout --detach "$FW_REVIEW_COMMIT"
cd "$checkout_dir"
test "$(git rev-parse HEAD)" = "$FW_REVIEW_COMMIT"
test -z "$(git status --porcelain)"
git rev-parse HEAD > "$record_dir/source-commit.txt"
python3 --version > "$record_dir/python-version.txt" 2>&1
sha256sum scripts/sanitize_experiment2_archive.py scripts/verify_experiment2_archive.py \
  docs/report/experiment2/analysis-honest.json docs/report/experiment2/analysis-swarm.json \
  ci/runtime-matrix.json > "$record_dir/source-input-sha256.txt"
```

## Verify, rebuild, compare

Continue in that checkout with `record_dir` still set. Each command must exit zero;
retain stderr and any failed output and record the failure before attempting a new
run. Do not change assertions, manifests or evidence to obtain a pass.

```sh
printf '%s\n' \
  '56d38f3dfec31a7c1d87773ff1001f792d105502838342546f0e4a4a12d36eb0  data/fleet-witness-judge-runs-2026-11-10.zip' \
  'f19127a49dea94e581e3714be3733ba480db7405632f1292b1f737273a23da04  data/fleet-witness-judge-runs-public-2026-11-16.zip' \
  | sha256sum --check > "$record_dir/archive-hashes.txt"
python3 -B scripts/sanitize_experiment2_archive.py verify \
  > "$record_dir/verification.json" 2> "$record_dir/verification.stderr"
python3 -B scripts/sanitize_experiment2_archive.py build \
  --output "$record_dir/rebuilt.zip" \
  > "$record_dir/build.json" 2> "$record_dir/build.stderr"
python3 -B scripts/sanitize_experiment2_archive.py verify --archive "$record_dir/rebuilt.zip" \
  > "$record_dir/rebuilt-verification.json" 2> "$record_dir/rebuilt-verification.stderr"
sha256sum "$record_dir/rebuilt.zip" > "$record_dir/rebuilt-sha256.txt"
python3 -B -m unittest discover -s tests -p 'test_experiment2*.py' -v \
  > "$record_dir/tests.stdout" 2> "$record_dir/tests.stderr"
git status --porcelain > "$record_dir/final-status.txt"
```

Expected results: 11 changed manifests, 66 byte-identical data members, three
explicitly superseded metadata members, 78 successor members, 14 runs, 41,995
bound recorded calls, and 46 frozen-count comparisons with an empty mismatch
list. All 36 focused tests should pass. Read the emitted limitations too.
The committed artifact's exact hash is required. ZIP compression bytes may vary
across zlib versions when rebuilding; the rebuilt archive must still pass the
complete member-byte and mapping comparison. Record its hash and any byte-level
difference instead of substituting it for the committed artifact's identity.

## Human result template

Copy this into a new record alongside the actual logs. Fill every field; do not
convert this template into an accepted result merely because commands exist.

```text
Reviewer identity and role: PENDING
Review date/time and timezone: PENDING
Full source commit: PENDING
Python version, platform and zlib version: PENDING
Archive/source-input SHA-256 evidence: PENDING
Commands and exit codes (including failures): PENDING
Verification counts and mismatches: PENDING
Rebuilt archive hash / compression differences: PENDING
Focused test result and final checkout status: PENDING
Artifacts retained at (keep private paths private): PENDING
Findings, limitations and reviewer conclusion: PENDING
```

Publish a concise result with the source/input hashes and necessary logs after
checking them for private paths. Keep the private preservation inventory separate.
AI assistance may be disclosed, but an AI agent's run is not a second human review.

## Source-holder private inventory handoff

Pio/source holder should preserve the originals unchanged and make a private
inventory containing: source machine/directory or backup identity, search scope,
search/recovery timestamps and timezone, relative file name, byte size, SHA-256,
run/completion classification, preservation/backup location and missing artifacts.
Record stopped, failed and incomplete attempts too. Do not paste credentials,
machine-local paths or raw private inventories into GitHub.

For the public issue, provide a summary of the scope checked, missing artifacts,
whether the originals remain preserved, and links/hashes tying the public
derivative to the retained originals. A source-holder statement and independent
verification are distinct evidence. No private inventory or backup has been
obtained by this task. If recovery is incomplete, record that outcome explicitly;
do not replace it with a new paid experiment.
