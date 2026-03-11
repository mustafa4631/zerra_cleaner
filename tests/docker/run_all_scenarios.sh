#!/usr/bin/env bash
set -euo pipefail

SCENARIOS=(
  "none:baseline"
  "tests/docker/scenarios/low_bloat.sh:low_bloat"
  "tests/docker/scenarios/medium_corruption.sh:medium_corruption"
  "tests/docker/scenarios/critical_failure.sh:critical_failure"
  "tests/docker/scenarios/security_misconfig.sh:security_misconfig"
  "tests/docker/scenarios/unattended_upgrades_disabled.sh:unattended_upgrades_disabled"
  "tests/docker/scenarios/suid_backdoor_simulation.sh:suid_backdoor_simulation"
  "tests/docker/scenarios/world_writable_storm.sh:world_writable_storm"
  "tests/docker/scenarios/pardus_repo_breakage.sh:pardus_repo_breakage"
  "tests/docker/scenarios/pseudo_malware_persistence.sh:pseudo_malware_persistence"
)

for entry in "${SCENARIOS[@]}"; do
  scenario="${entry%%:*}"
  tag="${entry##*:}"
  echo "=== Running scenario: ${tag} (${scenario}) ==="
  bash tests/docker/run_scenario_and_report.sh "${scenario}" "${tag}"
  echo
done

echo "All scenarios completed. Check /workspace/artifacts for reports."

