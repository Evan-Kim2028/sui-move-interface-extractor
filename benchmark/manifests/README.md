# Standard Benchmark Manifests

This directory contains the canonical package lists for AgentBeats/Sui benchmarks.

## `standard_phase2_benchmark.txt` (n=292)

**This is the primary benchmark set for Phase II (Type Inhabitation).**

### Why use this list?
The full `mainnet_most_used` corpus contains ~1000 packages, but the vast majority (>95%) are strictly **not viable** for the current Phase II evaluation harness. They require:
- Complex setup transactions (which the harness doesn't support).
- Specific object arguments (which the harness can't easily resolve).
- Admin capabilities that arbitrary senders don't possess.

Running blindly against the top 1000 results in a ~98% rejection rate (mostly "No Candidates"), wasting time and API tokens.

### Origin
This list of **292 packages** is the subset of `mainnet_most_used` that has been empirically verified to contain at least one "inhabitable" entry point (a `public entry` function accessible to a standard user).

- **Source**: Recursive baseline analysis (v0.2.1).
- **Count**: 292 Packages.
- **Goal**: Measure an agent's ability to plan and execute transactions on *feasible* targets, rather than measuring the harness's limitations.

### Usage
To run the standard Phase II benchmark:

```bash
uv run smi-inhabit \
  --corpus-root ../../sui-packages/packages/mainnet_most_used \
  --package-ids-file manifests/standard_phase2_benchmark.txt \
  --agent real-openai-compatible \
  --out results/my_benchmark_run.json
```

