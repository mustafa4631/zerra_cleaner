#!/usr/bin/env bash
set -euo pipefail

scenario="${1:-}"
tag="${2:-}"

if [[ -z "${scenario}" ]]; then
  echo "usage: $0 <scenario-script|none> [tag]" >&2
  echo "examples:" >&2
  echo "  $0 none pre" >&2
  echo "  $0 tests/docker/scenarios/low_bloat.sh low_bloat" >&2
  exit 2
fi

mkdir -p /workspace/artifacts

if [[ "${scenario}" != "none" ]]; then
  if [[ ! -f "${scenario}" ]]; then
    echo "scenario not found: ${scenario}" >&2
    exit 2
  fi
  bash "${scenario}"
fi

python3 /workspace/tests/docker/run_report.py --out-dir /workspace/artifacts --tag "${tag}"

