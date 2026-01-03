# A2A Evaluation Tuning Guide

This guide provides practical guidance for tuning A2A Phase II evaluations, focusing on progressive exposure, interface summary modes, and cost-performance trade-offs.

## Overview

Phase II (`smi-inhabit` or `real-openai-compatible` agent) offers several tunable parameters that directly affect:
- **Cost**: API call count and token usage
- **Performance**: Model success rate and `avg_hit_rate`
- **Reproducibility**: Consistent results across runs

**Key tuning knobs:**
- Interface summary mode (`entry_only` vs `entry_then_public` vs `names_only`)
- `max_functions` (initial interface chunk size)
- `--max-planning-calls` (progressive exposure budget)
- `--per-package-timeout-seconds` (per-package time budget)

---

## Interface Summary Modes

The `summarize_interface()` function generates human-readable summaries of Move package interfaces for prompting. Each mode trades off information density vs context cost.

### Mode Comparison

| Mode | What's Included | When to Use | Cost Impact |
|-------|-----------------|--------------|-------------|
| `entry_then_public` | Entry functions first, then public functions | Default for `real-openai-compatible`; comprehensive package analysis | Medium |
| `entry_only` | Entry functions with full signatures | When models should focus strictly on transaction entry points | Low |
| `names_only` | Only function names (no signatures) | Rapid iteration testing; when signature detail isn't critical | Very Low |
| `focused` | Only specific functions from `requested_targets` | Progressive exposure; when model requests specific function details | N/A (used after `need_more`) |

### Mode Selection Guidelines

**Use `entry_then_public` (default) when:**
- Models need context about helper/utility functions and constructors
- Understanding package structure beyond transaction surface
- Evaluating comprehensive package comprehension

**Use `entry_only` when:**
- Focusing strictly on transaction construction
- Benchmarking reasoning about PTB composition
- Minimizing cost while maintaining entry-point coverage

**Use `names_only` when:**
- Fast iteration during model evaluation
- Testing whether models can locate relevant functions
- Reducing token usage for large packages

**Use `focused` when:**
- Implementing progressive exposure (via `need_more` requests)
- Narrowing down to specific functions after initial analysis
- Debugging specific function interactions

---

## Tuning `max_functions`

The `max_functions` parameter controls how many functions appear in the initial interface summary.

**Current default:** `60` functions for `real-openai-compatible` (hardcoded in `inhabit_runner.py`)

**Trade-offs:**

| Value | Pros | Cons |
|-------|------|------|
| `20-30` | Low token cost; fast responses | May miss relevant functions; higher chance of `need_more` requests |
| `60` (default) | Balanced cost/coverage | Standard setting for most evaluations |
| `100+` | Comprehensive coverage | Higher cost; may overwhelm model with irrelevant functions |

**Tuning strategy:**
1. Start with default (`60`) for baseline
2. If models consistently miss functions, increase to `80-100`
3. If models succeed with fewer functions, reduce to `30-40` for cost savings

**To change:** Edit `inhabit_runner.py` line ~1030:
```python
iface_summary = summarize_interface(iface, max_functions=60, mode="entry_then_public")
# Change max_functions to desired value
```

---

## Progressive Exposure Budget

The `--max-planning-calls` parameter limits how many LLM planning calls a model can make per package. This directly controls the progressive exposure budget.

**Current default:** `50` (configured in argument parser)
**Recommended for production:** `2-3`

### How It Works

1. Call 1: Model receives initial interface summary
2. Model can request more detail: `{"need_more": ["0xADDR::module::func"], "reason": "..."}`
3. Call 2-N: Model receives focused summaries
4. Final call: Model returns PTB plan

Each request to the LLM counts against `--max-planning-calls`.

### Trade-offs

| Planning Calls | Pros | Cons |
|----------------|------|------|
| `1` | Lowest cost; simplest evaluation | No progressive exposure; limited interface detail |
| `2-3` (recommended) | Balanced cost/quality; allows focused queries | Moderate cost increase |
| `5-10` | Allows deeper exploration of complex packages | Higher cost; diminishing returns |
| `50` (default) | Maximum flexibility | Very high cost; rarely needed |

### Tuning Guidance

**For fast model comparisons:**
```bash
--max-planning-calls 2
```
- Use `2-3` calls per package
- Sufficient for most models to request specific function details
- Balances cost with quality

**For comprehensive package analysis:**
```bash
--max-planning-calls 5
```
- Allows multiple rounds of refinement
- Useful for complex DeFi packages with many modules

**For cost-sensitive evaluation:**
```bash
--max-planning-calls 1
```
- Disable progressive exposure entirely
- Model must succeed with initial interface summary only
- Lowest cost but may miss edge cases

---

## Timeout Configuration

The `--per-package-timeout-seconds` parameter controls the wall-clock budget per package.

**Current default:** `90` seconds (A2A mode)

### Trade-offs

| Timeout | Use Case | Impact |
|----------|-----------|---------|
| `30-60` | Simple packages; fast iteration | May timeout on complex packages |
| `90` (default) | Most packages; balanced | Standard setting |
| `180-300` | Complex DeFi/AMM packages | Higher completion rate; longer total runtime |

### Tuning Guidelines

**For standard package set:**
```bash
--per-package-timeout-seconds 90
```

**For complex packages (DeFi, AMMs):**
```bash
--per-package-timeout-seconds 180
```

**For smoke testing:**
```bash
--per-package-timeout-seconds 30 --samples 1
```

**Monitor:** Check `packages_timed_out` in evaluation bundle metrics. If consistently high, increase timeout.

---

## Cost-Performance Optimization

### Baseline Configuration

Start with this balanced configuration:
```bash
--max-planning-calls 2 \
--per-package-timeout-seconds 90 \
--samples 10
```

### Step 1: Establish Baseline

Run with baseline config:
```bash
cd benchmark
./scripts/run_model.sh --env-file ./.env --model openai/gpt-5.2 \
  --phase2-targeted --scan-samples 50 --run-samples 10 \
  --max-planning-calls 2 --per-package-timeout-seconds 90
```

Record:
- `avg_hit_rate` (success metric)
- Total API cost (from logs or provider dashboard)
- `packages_timed_out` (timeout rate)

### Step 2: Optimize for Cost

Reduce budget parameters and observe impact:

```bash
# Reduce planning calls
./scripts/run_model.sh --env-file ./.env --model openai/gpt-5.2 \
  --phase2-targeted --scan-samples 50 --run-samples 10 \
  --max-planning-calls 1 --per-package-timeout-seconds 60
```

Compare metrics:
- If `avg_hit_rate` drops < 5%, cost savings are worth it
- If `packages_timed_out` increases significantly, revert to baseline

### Step 3: Optimize for Quality

Increase budget for complex packages:

```bash
# Allow more exploration
./scripts/run_model.sh --env-file ./.env --model openai/gpt-5.2 \
  --phase2-targeted --scan-samples 50 --run-samples 10 \
  --max-planning-calls 3 --per-package-timeout-seconds 120
```

Use this for:
- Leaderboard runs (maximize quality)
- Evaluating frontier models (high quality target)
- Production deployments (reliability over cost)

---

## Progressive Exposure Best Practices

### When Progressive Exposure Helps

Progressive exposure is most valuable when:

1. **Large packages** (> 100 functions)
   - Initial summary may miss relevant entry points
   - Models can narrow down with `need_more` requests

2. **Complex protocols** (DeFi, AMMs)
   - Multiple modules with cross-dependencies
   - Models benefit from focused exploration

3. **Context-constrained models**
   - Smaller context windows (128k tokens or less)
   - Need to manage token budget carefully

### When Progressive Exposure Wastes Cost

Avoid progressive exposure when:

1. **Small packages** (< 30 functions)
   - Entire interface fits in initial summary
   - No need for `need_more` requests

2. **Simple protocols**
   - Straightforward transaction paths
   - Models rarely need additional context

3. **High-cost environments**
   - API costs dominate evaluation budget
   - Prefer `--max-planning-calls 1`

### Monitoring Progressive Exposure Usage

When `need_more` handling is implemented, track:

```bash
# Count need_more requests in logs
grep "need_more" logs/a2a_phase2_*/events.jsonl | wc -l

# Compare planning call distribution
jq '.planning_calls' results/a2a/*.json | sort | uniq -c
```

**Healthy pattern:**
- Most packages: 1 planning call (succeed with initial summary)
- 10-20%: 2 planning calls (one `need_more` request)
- Rare: 3+ planning calls (very complex packages)

**Red flags:**
- All packages: 2+ planning calls → increase `max_functions`
- Frequent 5+ planning calls → packages too complex or model struggling

---

## Model-Specific Tuning

### Claude Models (Anthropic)

**Strengths:**
- Large context (200k tokens)
- Good at reasoning about transaction causality
- Strong at following structured output constraints

**Tuning:**
```bash
# Claude can handle larger initial summaries
# Edit inhabit_runner.py: max_functions=80 or 100
--max-planning-calls 2  # Claude rarely needs more
--per-package-timeout-seconds 60  # Fast execution
```

### GPT Models (OpenAI)

**Strengths:**
- Good at following instructions
- Strong PTB schema compliance
- Cost-effective for large-scale evaluation

**Tuning:**
```bash
# Moderate context size
max_functions=60  # Default is fine
--max-planning-calls 3  # May benefit from focused exploration
--per-package-timeout-seconds 90  # Standard
```

### Gemini Models (Google)

**Strengths:**
- Good at understanding package structure
- Strong at function selection

**Tuning:**
```bash
# Start with conservative settings
max_functions=40  # Smaller initial chunk
--max-planning-calls 2  # Allow progressive expansion
--per-package-timeout-seconds 90
```

### Reasoning Models (DeepSeek, GLM, O1/O3)

**Strengths:**
- Chain-of-thought for complex reasoning
- Better at understanding nuanced constraints

**Tuning:**
```bash
# Give more time for reasoning
max_functions=60  # Standard
--max-planning-calls 2  # Let them explore if needed
--per-package-timeout-seconds 180  # Allow extended reasoning
```

---

## Troubleshooting Common Issues

### Issue: High Timeout Rate

**Symptoms:**
- `metrics.packages_timed_out > 5`
- Many packages hit `per_package_timeout_seconds` limit

**Solutions:**
1. Increase timeout: `--per-package-timeout-seconds 180`
2. Reduce sample size: `--run-samples 5` for debugging
3. Check RPC health: Use a faster/fuller Sui fullnode

### Issue: Low Hit Rate

**Symptoms:**
- `metrics.avg_hit_rate < 0.3`
- Models create wrong types or no objects

**Solutions:**
1. Increase `max_functions` (e.g., from 60 to 80)
2. Use `entry_then_public` mode for more context
3. Increase `--max-planning-calls` to 3-5 for progressive exposure

### Issue: High API Cost

**Symptoms:**
- Evaluation costs exceed budget
- Many `max_planning_calls` warnings in logs

**Solutions:**
1. Reduce `--max-planning-calls` to 1-2
2. Decrease `max_functions` to 30-40
3. Reduce sample size: `--run-samples 10` for comparison runs

### Issue: Inconsistent Results Across Runs

**Symptoms:**
- Same model/package shows different `avg_hit_rate`
- Results vary 10-20% between runs

**Solutions:**
1. Ensure determinism: Use same `--seed` parameter
2. Check RPC consistency: Use same `--rpc-url`
3. Verify model version: Model slug shouldn't change between runs

---

## Example Tuning Workflows

### Workflow 1: Quick Model Comparison

Compare 3 models with minimal cost:

```bash
cd benchmark

# Model A
SMI_MODEL="anthropic/claude-sonnet-4.5" \
./scripts/run_model.sh --env-file ./.env \
  --phase2-targeted --scan-samples 50 --run-samples 20 \
  --max-planning-calls 1 --per-package-timeout-seconds 60

# Model B
SMI_MODEL="openai/gpt-5.2" \
./scripts/run_model.sh --env-file ./.env \
  --phase2-targeted --scan-samples 50 --run-samples 20 \
  --max-planning-calls 1 --per-package-timeout-seconds 60

# Model C
SMI_MODEL="google/gemini-3-flash-preview" \
./scripts/run_model.sh --env-file ./.env \
  --phase2-targeted --scan-samples 50 --run-samples 20 \
  --max-planning-calls 1 --per-package-timeout-seconds 60

# Compare results
python scripts/phase2_leaderboard.py results/run_*.json
```

### Workflow 2: Optimize for Specific Model

Tune parameters for Claude Sonnet 4.5:

```bash
cd benchmark

# Test with 2 planning calls
SMI_MODEL="anthropic/claude-sonnet-4.5" \
./scripts/run_model.sh --env-file ./.env \
  --phase2-targeted --scan-samples 100 --run-samples 30 \
  --max-planning-calls 2 --per-package-timeout-seconds 90

# If hit rate is good (>0.5), reduce to 1 call
SMI_MODEL="anthropic/claude-sonnet-4.5" \
./scripts/run_model.sh --env-file ./.env \
  --phase2-targeted --scan-samples 100 --run-samples 30 \
  --max-planning-calls 1 --per-package-timeout-seconds 60

# Compare cost vs quality
python scripts/phase2_leaderboard.py results/run_*.json
```

### Workflow 3: Debug Timeout Issues

Investigate why packages are timing out:

```bash
cd benchmark

# Run with extended timeout and verbose logging
SMI_MODEL="anthropic/claude-sonnet-4.5" \
./scripts/run_model.sh --env-file ./.env \
  --phase2-targeted --scan-samples 20 --run-samples 5 \
  --max-planning-calls 1 --per-package-timeout-seconds 300

# Check which packages still timeout
jq '.packages[] | select(.timed_out == true) | .package_id' results/run_*.json

# Run single problematic package with debugging
printf "%s\n" <PROBLEMATIC_PACKAGE_ID> > debug.txt
uv run smi-inhabit \
  --corpus-root ../sui-packages/packages/mainnet_most_used \
  --package-ids-file debug.txt \
  --agent real-openai-compatible \
  --per-package-timeout-seconds 600 \
  --rpc-url https://fullnode.mainnet.sui.io:443
```

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical details on progressive exposure design
- [A2A_EXAMPLES.md](A2A_EXAMPLES.md) - Concrete request/response examples
- [GETTING_STARTED.md](../GETTING_STARTED.md) - Quick start guide
- [../../docs/METHODOLOGY.md](../../docs/METHODOLOGY.md) - Scoring rules and evaluation logic
