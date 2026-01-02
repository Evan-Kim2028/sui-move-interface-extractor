#!/usr/bin/env bash
set -euo pipefail

# Generates benchmark/manifests/datasets/packages_with_keys.txt from corpus scan results.
# Definition: packages with score.targets >= MIN_TARGETS (default 1).

CORPUS_ROOT=${1:-"../../sui-packages/packages/mainnet_most_used"}
MIN_TARGETS=${2:-"1"}
SCAN_SAMPLES=${3:-"1000"}
SEED=${4:-"0"}

OUT_JSON="results/datasets_scan_packages_with_keys.json"
OUT_DATASET="manifests/datasets/packages_with_keys.txt"

echo "Scanning corpus for key-struct targets (samples=${SCAN_SAMPLES}, seed=${SEED})"
uv run smi-inhabit \
  --corpus-root "${CORPUS_ROOT}" \
  --samples "${SCAN_SAMPLES}" \
  --seed "${SEED}" \
  --agent baseline-search \
  --simulation-mode build-only \
  --continue-on-error \
  --no-log \
  --out "${OUT_JSON}"

echo "Filtering dataset: targets >= ${MIN_TARGETS}"
uv run smi-phase2-filter-manifest "${OUT_JSON}" --min-targets "${MIN_TARGETS}" --out-manifest "${OUT_DATASET}"

echo "Wrote dataset: ${OUT_DATASET}"
