#!/usr/bin/env bash
set -euo pipefail

# Runs Phase I repeatedly until it finishes successfully, resuming from --out if present.
#
# Usage:
#   ./scripts/run_phase1_until_done.sh <CORPUS_ROOT> <OUT_JSON>
#
# Example:
#   ./scripts/run_phase1_until_done.sh \
#     /path/to/sui-packages/packages/mainnet_most_used \
#     results/phase1_glm47_thinking_seed1_n1000_structs25.json

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CORPUS_ROOT="${1:?missing CORPUS_ROOT}"
OUT_JSON="${2:-results/phase1_glm47_thinking_seed1_n1000_structs25.json}"

# Help
if [[ "${CORPUS_ROOT}" == "-h" || "${CORPUS_ROOT}" == "--help" ]]; then
  echo "Usage: $0 <CORPUS_ROOT> <OUT_JSON>"
  exit 0
fi

# Tuneables via env vars.
SAMPLES="${SAMPLES:-1000}"
SEED="${SEED:-1}"
MAX_STRUCTS_IN_PROMPT="${MAX_STRUCTS_IN_PROMPT:-25}"
MAX_ERRORS="${MAX_ERRORS:-200}"
CHECKPOINT_EVERY="${CHECKPOINT_EVERY:-1}"
SLEEP_ON_FAIL_SECONDS="${SLEEP_ON_FAIL_SECONDS:-30}"

while true; do
  echo "[$(date -Iseconds)] starting/resuming Phase I..."
  set +e
  uv run smi-bench \
    --corpus-root "$CORPUS_ROOT" \
    --agent real-openai-compatible \
    --samples "$SAMPLES" \
    --seed "$SEED" \
    --max-structs-in-prompt "$MAX_STRUCTS_IN_PROMPT" \
    --continue-on-error \
    --max-errors "$MAX_ERRORS" \
    --checkpoint-every "$CHECKPOINT_EVERY" \
    --out "$OUT_JSON" \
    --resume
  status="$?"
  set -e

  if [[ "$status" -eq 0 ]]; then
    echo "[$(date -Iseconds)] Phase I finished: $OUT_JSON"
    exit 0
  fi

  echo "[$(date -Iseconds)] Phase I exited with status=$status; sleeping ${SLEEP_ON_FAIL_SECONDS}s then retrying..."
  sleep "$SLEEP_ON_FAIL_SECONDS"
done
