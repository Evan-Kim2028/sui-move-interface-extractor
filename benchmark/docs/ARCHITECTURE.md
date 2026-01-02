# Benchmark Code Architecture (`benchmark/src/smi_bench`)

This document is a maintainers’ map of the Python benchmark harness: **what lives where**, **how data flows**, and **which invariants matter** for refactors.

It is intentionally short and “source-first.” When in doubt, trust the code.

## High-level flow

Both Phase I and Phase II consume a local `sui-packages` checkout (bytecode corpus) and invoke the Rust extractor to emit a **bytecode-derived interface JSON** for each package:

- Rust CLI: `sui_move_interface_extractor --bytecode-package-dir <pkg_dir> --emit-bytecode-json -`
- Output is parsed as JSON and used as the ground truth substrate for benchmarks.

## Module map

### Corpus / dataset utilities

- `smi_bench/dataset.py`
  - Discovers packages under `--corpus-root` (expects `bytecode_modules/` + `metadata.json`).
  - Provides deterministic sampling (`seed` + FNV-1a).

### Phase I (key-struct discovery)

- `smi_bench/runner.py`
  - Orchestrates Phase I runs.
  - Extracts **truth** key types from the bytecode interface JSON (`abilities` contains `key`).
  - Builds an LLM prompt that **omits abilities** (to avoid leakage) and may truncate struct context.
  - Scores predictions with precision/recall/F1 (`smi_bench/judge.py`).

- `smi_bench/judge.py`
  - Deterministic set-matching metrics for Phase I.

### Phase II (type inhabitation)

- `smi_bench/inhabit_runner.py`
  - Orchestrates Phase II runs.
  - Targets are key structs from the same bytecode interface JSON.
  - Produces PTB plans via:
    - `baseline-search` (deterministic heuristics),
    - `real-openai-compatible` (LLM planning), or
    - `template-search` (baseline skeleton + LLM fills args).
  - Simulates transactions via Rust helper `smi_tx_sim` (dry-run/dev-inspect/build-only).
  - Scores created object types vs targets using base-type matching (`smi_bench/inhabit/score.py`).

- `smi_bench/inhabit/executable_subset.py`
  - The core deterministic “baseline-search” logic:
    - candidate selection for entry functions,
    - supported-arg construction rules,
    - shallow recursive constructor discovery,
    - prompt-oriented interface summaries (`summarize_interface`).

- `smi_bench/inhabit/score.py`
  - Phase II scoring: normalize type strings, compare **base types** (type args ignored).

- `smi_bench/inhabit/dryrun.py`
  - Parses dry-run responses into `exec_ok` + best-effort failure details (abort code/location).

### Agents / I/O

- `smi_bench/agents/real_agent.py`
  - OpenAI-compatible chat-completions client with retry/backoff and strict JSON parsing.
  - Outputs either a type list (Phase I) or a PTB JSON object (Phase II).

- `smi_bench/agents/mock_agent.py`
  - Deterministic mock behaviors for Phase I infrastructure testing.

- `smi_bench/json_extract.py`
  - Best-effort JSON extraction from model output (handles code fences and surrounding prose).

- `smi_bench/logging.py`
  - JSONL logging for runs (run metadata + event stream + per-package rows).

## Output schemas / versioning invariants

- Phase I output JSON includes `schema_version=1` (see `runner.py`).
- Phase II output JSON includes `schema_version=2` (see `inhabit_runner.py`).

Maintainers should treat these as **stable**:

- Changing output shapes should either:
  - be additive + backward compatible, or
  - bump the schema version and update readers/scripts accordingly.

## Refactor safety checklist

When refactoring:

- Keep **determinism**: sort keys / stable ordering where possible, keep sampling stable.
- Keep **scoring semantics** stable (especially Phase II base-type matching).
- Prefer `--require-dry-run` runs for comparisons/leaderboards; document any fallback logic.
- Avoid duplicating “how to call the Rust extractor” in multiple places without a clear reason.

