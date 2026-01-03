#!/bin/bash
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
CORPUS_HOST="$REPO_ROOT/benchmark/.docker_test_corpus"
RESULTS_HOST="$REPO_ROOT/benchmark/.docker_test_results"
LOGS_HOST="$REPO_ROOT/benchmark/.docker_test_logs"
MANIFEST_HOST="$CORPUS_HOST/manifest.txt"

# Default configuration
DEFAULT_SENDER="0x064d87c3da8b7201b18c05bfc3189eb817920b2d089b33e207d1d99dc5ce08e0"
DEFAULT_MODEL="google/gemini-3-flash-preview"

# Ensure corpus exists
if [ ! -d "$CORPUS_HOST" ]; then
    echo "Corpus not found. Attempting to run prepare_test_corpus.sh..."
    if [ -f "$REPO_ROOT/scripts/prepare_test_corpus.sh" ] && command -v sui &> /dev/null; then
        "$REPO_ROOT/scripts/prepare_test_corpus.sh"
    else
        echo "Warning: could not run prepare_test_corpus.sh (sui missing or script not found)."
        echo "Creating minimal fallback mock corpus..."
        mkdir -p "$CORPUS_HOST/0x00/fixture/bytecode_modules"
        echo '{"id": "0x0000000000000000000000000000000000000000000000000000000000000001"}' > "$CORPUS_HOST/0x00/fixture/metadata.json"
        touch "$CORPUS_HOST/0x00/fixture/bytecode_modules/dummy.mv"
    fi
fi

# Create manifest file
# The package ID must match what's in metadata.json
# Use the quickstart_2 dataset if available, otherwise fallback to mock
if [ -f "$REPO_ROOT/benchmark/manifests/datasets/quickstart_2.txt" ]; then
    echo "Using Quickstart dataset (2 packages)..."
    cp "$REPO_ROOT/benchmark/manifests/datasets/quickstart_2.txt" "$MANIFEST_HOST"
    # Ensure we mount the real corpus if we are using real packages
    # This logic assumes the user has the 'sui-packages' repo adjacent or we need to fetch them
    # For now, if we are in the test script, we might not have the full corpus. 
    # Let's check if we can symlink the mainnet_most_used if it exists
    REAL_CORPUS_PARENT="$REPO_ROOT/../sui-packages/packages"
    CONTAINER_CORPUS_PATH="/app/corpus"
    
    if [ -d "$REAL_CORPUS_PARENT/mainnet_most_used" ]; then
       CORPUS_HOST="$REAL_CORPUS_PARENT"
       # We mount the PARENT 'packages' dir to /app/corpus to support symlinks
       # So the actual root for the runner is /app/corpus/mainnet_most_used
       CONTAINER_CORPUS_PATH="/app/corpus/mainnet_most_used"
    fi
else
    echo "0x0000000000000000000000000000000000000000000000000000000000000001" > "$MANIFEST_HOST"
    CONTAINER_CORPUS_PATH="/app/corpus"
fi

echo "Cleaning up old results and logs..."
rm -rf "$RESULTS_HOST"/*
rm -rf "$LOGS_HOST"/*
mkdir -p "$RESULTS_HOST"
mkdir -p "$LOGS_HOST"

echo "Building Docker image smi-bench:test..."
docker build -t smi-bench:test .

# Allow overriding model and agent via env
AGENT="${SMI_AGENT:-real-openai-compatible}"
MODEL="${SMI_MODEL:-$DEFAULT_MODEL}"
SENDER="${SMI_SENDER:-$DEFAULT_SENDER}"

echo "Starting container..."
# Mount corpus to /app/corpus
# Mount results to /app/results
# Load .env if it exists
ENV_ARGS=""
if [ -f "$REPO_ROOT/benchmark/.env" ]; then
    echo "Using env-file: benchmark/.env"
    ENV_ARGS="--env-file $REPO_ROOT/benchmark/.env"
fi

# Determine volumes
# If we are using the real corpus, we mount it. Otherwise we use the test corpus.
# We also explicitly mount the manifest file to /app/manifest.txt
MOUNT_ARGS="-v $CORPUS_HOST:/app/corpus -v $MANIFEST_HOST:/app/manifest.txt"

# Ensure port 9999 is free
existing=$(docker ps -q --filter "publish=9999")
if [ ! -z "$existing" ]; then
    echo "Freeing port 9999..."
    docker stop $existing > /dev/null
fi

CONTAINER_ID=$(docker run -d --rm \
    $ENV_ARGS \
    -e SMI_MODEL="$MODEL" \
    $MOUNT_ARGS \
    -v "$RESULTS_HOST:/app/results" \
    -v "$LOGS_HOST:/app/logs" \
    -p 9999:9999 \
    smi-bench:test)

echo "Container started: $CONTAINER_ID"

function cleanup {
    echo "Stopping container..."
    docker stop "$CONTAINER_ID"
}
trap cleanup EXIT

echo "Waiting for agent to be ready..."
# Simple retry loop
for i in {1..30}; do
    if curl -s http://localhost:9999/ > /dev/null; then
        echo "Agent is up!"
        break
    fi
    sleep 1
done

# Prepare task payload
# We use the 'message/send' method which is standard for A2A agents in this project.
# The config is passed as a JSON string inside the message text part.
# We pass the SENDER to ensure the runner has funds.
PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": {
      "messageId": "docker_smoke_$(date +%s)",
      "role": "user",
      "parts": [
        {
          "text": "{\\"config\\": {\\"corpus_root\\": \\"$CONTAINER_CORPUS_PATH\\", \\"package_ids_file\\": \\"/app/manifest.txt\\", \\"agent\\": \\"$AGENT\\", \\"samples\\": 2, \\"simulation_mode\\": \\"dry-run\\", \\"run_id\\": \\"quickstart_test\\", \\"continue_on_error\\": true, \\"resume\\": false, \\"sender\\": \\"$SENDER\\", \\"checkpoint_every\\": 1}, \\"out_dir\\": \\"/app/results\\"}"
        }
      ]
    }
  }
}
EOF
)

echo "Submitting task (Agent: $AGENT, Model: $MODEL, Sender: $SENDER)..."
curl -X POST http://localhost:9999/ \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD"

echo ""
echo "Task submitted. Waiting for results (up to 20s)..."

# Poll for result file
for i in {1..20}; do
    if [ -f "$RESULTS_HOST/quickstart_test.json" ]; then
        # Check if we have results for both packages or if it finished
        # We can just cat the summary
        echo "SUCCESS: Result file generated."
        cat "$RESULTS_HOST/quickstart_test.json" | head -n 50
        exit 0
    fi
    sleep 1
done

echo "FAILURE: Result file not found after 20s."
docker logs "$CONTAINER_ID"
exit 1

# --- Production Security Verification ---

echo "Running Security Verification..."

# 1. Non-Root Test
echo "Test: Running as non-root (UID 1000)..."
docker run --rm \
    -u 1000:1000 \
    $ENV_ARGS \
    -e SMI_AGENT="mock-empty" \
    -v "$CORPUS_HOST:/app/corpus" \
    -v "$RESULTS_HOST:/app/results" \
    -v "$LOGS_HOST:/app/logs" \
    smi-bench:test smi-inhabit --corpus-root /app/corpus --samples 1 --agent mock-empty --out /app/results/non_root_test.json --no-log

if [ -f "$RESULTS_HOST/non_root_test.json" ]; then
    echo "  SUCCESS: Non-root execution passed."
else
    echo "  FAILURE: Non-root execution failed."
    exit 1
fi

# 2. Read-Only Root FS Test
echo "Test: Running with Read-Only root filesystem..."
# Note: we must ensure /tmp is mounted as tmpfs for SMI_TEMP_DIR to work
docker run --rm \
    --read-only \
    --tmpfs /tmp \
    $ENV_ARGS \
    -e SMI_AGENT="mock-empty" \
    -v "$CORPUS_HOST:/app/corpus" \
    -v "$RESULTS_HOST:/app/results" \
    -v "$LOGS_HOST:/app/logs" \
    smi-bench:test smi-inhabit --corpus-root /app/corpus --samples 1 --agent mock-empty --out /app/results/readonly_test.json --no-log

if [ -f "$RESULTS_HOST/readonly_test.json" ]; then
    echo "  SUCCESS: Read-Only filesystem passed."
else
    echo "  FAILURE: Read-Only filesystem failed."
    exit 1
fi

echo "ALL TESTS PASSED: Docker image is production-ready."

