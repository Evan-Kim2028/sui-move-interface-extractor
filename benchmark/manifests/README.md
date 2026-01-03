# Standard Benchmark Manifests

This directory contains the canonical package lists for AgentBeats/Sui benchmarks.

## `type_inhabitation_top25.txt` (n=25)

**Curated subset for fast iteration on Type Inhabitation benchmarks.**

### Why use this list?
Top 25 packages selected by composite interest score for type inhabitation evaluation:
- High key struct counts (more targets)
- High entry function counts (more planning paths)
- Good entry/key ratios (planning efficiency)
- Function/struct diversity (signature complexity)

**Selection Methodology:**
- Filtered to `standard_phase2_benchmark.txt` (inhabitable only)
- Scored by weighted composite metric (key structs: 40%, entry functions: 30%,
  entry/key ratio: 15%, diversity: 15%)
- Applied diversity constraints to avoid clustering:
  - Max 5 packages with same key_structs count
  - Max 30% from large packages (top 50% by key_structs)
- Total corpus: 292 packages → selected 25 (8.5%)

**Use Cases:**
- **Fast iteration**: Run in ~8% of time vs full 292
- **Agent development**: Quick feedback during LLM prompt tuning
- **Debugging**: Investigate failures on small, diverse set
- **CI/CD**: Run full evaluation on meaningful subset

### Usage
To run the top-25 Phase II benchmark:

```bash
uv run smi-inhabit \
  --corpus-root ../../sui-packages/packages/mainnet_most_used \
  --dataset type_inhabitation_top25 \
  --agent real-openai-compatible \
  --out results/top25_run.json
```

**Note:** Use `--dataset` flag for datasets under `manifests/datasets/`. For custom manifest files, use `--package-ids-file` with the full path.

**Generation:**
```bash
cd benchmark
python scripts/generate_top25_dataset.py
```

Outputs:
- `manifests/datasets/type_inhabitation_top25.txt` (dataset file)
- `results/dataset_top25_scoring.json` (detailed scores and methodology)

---

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
  --dataset standard_phase2_benchmark \
  --agent real-openai-compatible \
  --out results/my_benchmark_run.json
```

