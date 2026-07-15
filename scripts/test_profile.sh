#!/usr/bin/env bash
# Lot 1 baseline — pytest duration profiling (non-blocking measurement artifact).
# Usage: bash scripts/test_profile.sh [output_dir]
# Requires: Docker stack up (make backend-test uses same contract).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-${ROOT}/.artifacts/lot1-baseline}"
mkdir -p "${OUT_DIR}"

PYTEST_MARKERS='not openai_observation_smoke and not openai_smoke and not slow'
API_DIR="/app/apps/api"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

log() { echo "[test_profile ${TIMESTAMP}] $*" >&2; }

run_timed_pytest() {
  local label="$1"
  local durations="$2"
  shift 2
  local out="${OUT_DIR}/${label}-${TIMESTAMP}.txt"
  local timing="${OUT_DIR}/${label}-${TIMESTAMP}.timing"
  log "Running ${label} (durations=${durations}) -> ${out}"
  local start end elapsed
  start=$(date +%s)
  # shellcheck disable=SC2086
  docker compose exec -T api sh -lc \
    "cd ${API_DIR} && uv run pytest -m '${PYTEST_MARKERS}' --durations=${durations} -q $*" \
    2>&1 | tee "${out}"
  end=$(date +%s)
  elapsed=$((end - start))
  echo "${elapsed}" > "${timing}"
  log "${label} wall time: ${elapsed}s"
}

log "Output directory: ${OUT_DIR}"

# Full PR suite
run_timed_pytest "pytest-pr-suite-d50" 50

# Domain profiles
run_timed_pytest "pytest-establishments-d30" 30 houston/establishments/tests
run_timed_pytest "pytest-action-plans-d30" 30 houston/action_plans/tests
run_timed_pytest "pytest-signals-d30" 30 houston/signals/tests
run_timed_pytest "pytest-notifications-d30" 30 houston/notifications/tests

# imported_catalog: files using the fixture vs rest of establishments
run_timed_pytest "pytest-establishments-catalog-files-d20" 20 \
  houston/establishments/tests/test_catalog_import.py \
  houston/establishments/tests/test_business_unit_catalog.py \
  houston/establishments/tests/test_catalog_suggest_api.py \
  houston/establishments/tests/test_onboarding_manual_v2.py \
  houston/establishments/tests/test_onboarding_proposal_api.py \
  houston/establishments/tests/test_onboarding_tenant_isolation_api.py \
  houston/establishments/tests/test_verify_catalog_counts_command.py \
  houston/establishments/tests/test_catalog_priority_descriptions.py

run_timed_pytest "pytest-establishments-no-catalog-files-d20" 20 \
  houston/establishments/tests --ignore=houston/establishments/tests/test_catalog_import.py \
  --ignore=houston/establishments/tests/test_business_unit_catalog.py \
  --ignore=houston/establishments/tests/test_catalog_suggest_api.py \
  --ignore=houston/establishments/tests/test_onboarding_manual_v2.py \
  --ignore=houston/establishments/tests/test_onboarding_proposal_api.py \
  --ignore=houston/establishments/tests/test_onboarding_tenant_isolation_api.py \
  --ignore=houston/establishments/tests/test_verify_catalog_counts_command.py \
  --ignore=houston/establishments/tests/test_catalog_priority_descriptions.py

# v3 golden isolated (included in PR suite; measure for Lot 2 prep)
run_timed_pytest "pytest-v3-golden-d15" 15 \
  houston/signals/tests/test_observation_pipeline_v3_golden.py

log "Done. Artifacts in ${OUT_DIR}"
