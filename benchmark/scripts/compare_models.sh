#!/usr/bin/env bash
set -euo pipefail

# Run multiple models in sequence and compare results
#
# Usage:
#   ./scripts/compare_models.sh <model1> <model2> [model3...] [--samples N]
#
# Examples:
#   ./scripts/compare_models.sh claude-sonnet gemini-pro --samples 10
#   ./scripts/compare_models.sh gpt-4o-mini deepseek glm --samples 50

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Parse arguments
MODELS=()
SAMPLES=10

while [[ $# -gt 0 ]]; do
    case $1 in
        --samples)
            SAMPLES="$2"
            shift 2
            ;;
        *)
            MODELS+=("$1")
            shift
            ;;
    esac
done

if [ ${#MODELS[@]} -eq 0 ]; then
    echo "Usage: $0 <model1> <model2> [model3...] [--samples N]"
    echo ""
    echo "Available models (from models.yaml):"
    grep "^  [a-z]" models.yaml | grep -v "^  #" | sed 's/:$//' | sed 's/^  /  - /'
    exit 1
fi

OUTPUT_DIR="results/comparison_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "Comparing ${#MODELS[@]} models with $SAMPLES samples each"
echo "Models: ${MODELS[*]}"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Run each model
for model in "${MODELS[@]}"; do
    echo "=========================================="
    echo "Running: $model"
    echo "=========================================="
    ./scripts/run_model.sh "$model" "$SAMPLES" "$OUTPUT_DIR/${model}.json"
    echo ""
done

echo "=========================================="
echo "All models complete!"
echo "=========================================="
echo ""

# Generate comparison
echo "Generating comparison..."
python scripts/phase2_leaderboard.py "$OUTPUT_DIR"/*.json

echo ""
echo "Detailed results in: $OUTPUT_DIR/"
