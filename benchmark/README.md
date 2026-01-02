# Benchmark Harness (`benchmark/`)

This directory contains the automated benchmarking harness for Sui Move packages.

## Start here

- **Run Phase II quickly:** `GETTING_STARTED.md`
- **Single model runner:** `scripts/run_model.sh`
- **Multi-model runner:** `scripts/run_multi_model.sh`
- **A2A integration:** `docs/A2A_EXAMPLES.md`

## Phase overview

- **Phase I (Key-Struct Discovery):** Predict which structs in a package have the `key` ability based on field shapes.
- **Phase II (Type Inhabitation):** Plan valid transaction sequences (Programmable Transaction Blocks) to create target Move objects.

## Key resources

- `../docs/METHODOLOGY.md` - Detailed scoring rules and extraction logic.
- `docs/A2A_COMPLIANCE.md` - Protocol implementation and testing strategy.
- `docs/A2A_EXAMPLES.md` - Concrete JSON-RPC request/response examples.
- `docs/FEEDBACK_PIPELINE_AUDIT.md` - Framework hardening notes.
- `docs/ARCHITECTURE.md` - Maintainers’ map of the harness internals.

## Quick command reference

```bash
# Single-model Phase II targeted
cd benchmark
./scripts/run_model.sh --env-file ./.env --model openai/gpt-5.2

# Multi-model Phase II targeted (start conservative to avoid RPC rate limits)
./scripts/run_multi_model.sh --env-file ./.env --models "openai/gpt-5.2,google/gemini-3-flash-preview" --parallel 1

# Local A2A scenario
uv run smi-agentbeats-scenario scenario_smi --launch-mode current
uv run smi-a2a-smoke --corpus-root ../sui-packages/packages/mainnet_most_used --samples 1
```
