#!/usr/bin/env bash
# Trusted launcher for an offline task. Its report is untrusted task output.
set -euo pipefail
umask 077
if [[ $# != 2 ]]; then
  echo 'usage: offline-task.sh SOURCE NEW_WORKSPACE' >&2
  exit 64
fi
source_dir=$(realpath -- "$1")
[[ ! -L "$2" ]]
workspace=$(realpath -m -- "$2")
[[ -d "$source_dir" ]]
# Do not reuse a prior run, follow a pre-existing workspace symlink, or overwrite.
mkdir -- "$workspace"
mkdir -- "$workspace/results"
stage=copy
finish() {
  status=$?
  trap - EXIT
  printf 'mode=offline-scripted-demo\nstage=%s\nexit_code=%s\n' \
    "$stage" "$status" > "$workspace/results/report.txt"
  exit "$status"
}
trap finish EXIT
cp -R -- "$source_dir" "$workspace/repository"
chmod -R u+rwX -- "$workspace/repository"
cd -- "$workspace/repository"
export PYTHONDONTWRITEBYTECODE=1
stage=python-tests
python -m unittest discover -s tests -v > "$workspace/results/tests.log" 2>&1
if [[ -f tests/viewer.test.mjs ]]; then
  stage=viewer-tests
  node --test tests/viewer.test.mjs > "$workspace/results/viewer.log" 2>&1
fi
stage=demo
python -m fleet_witness demo --output "$workspace/results/demo" --seed 42 \
  > "$workspace/results/demo.log" 2>&1
stage=complete
