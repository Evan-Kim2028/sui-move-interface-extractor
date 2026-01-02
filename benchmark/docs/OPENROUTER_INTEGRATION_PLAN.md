# OpenRouter Integration Plan

## Objective
Enable multi-model benchmarking similar to `sui-move-eval` by integrating OpenRouter API support into the sui-move-interface-extractor benchmark system.

## Current State Analysis

### Existing Architecture
The benchmark currently supports:
- **Agent interface**: `real-openai-compatible` (configurable via `.env`)
- **Configuration**: `RealAgentConfig` dataclass in `real_agent.py`
- **Environment variables**:
  ```bash
  SMI_API_KEY=...
  SMI_API_BASE_URL=https://api.openai.com/v1
  SMI_MODEL=gpt-4o-mini
  SMI_TEMPERATURE=0
  SMI_MAX_TOKENS=2048
  SMI_THINKING=enabled  # Provider-specific (Z.AI)
  SMI_RESPONSE_FORMAT=json_object
  ```

### Current Limitations
1. **Single model per run**: Need to change `.env` and restart to test different models
2. **No parallel execution**: Can't run multiple models simultaneously
3. **Manual tracking**: No automated leaderboard generation
4. **Provider-specific config**: Scattered settings for different providers

## Proposed Changes

### 1. Add OpenRouter Support to RealAgent

**File**: `benchmark/src/smi_bench/agents/real_agent.py`

**Changes**:
- Add `OPENROUTER_API_KEY` as fallback env var
- Detect OpenRouter base URL and set sensible defaults
- Support model name format: `provider/model-name` (OpenRouter style)

```python
def load_real_agent_config(env_overrides: dict[str, str] | None = None) -> RealAgentConfig:
    # ... existing code ...
    
    # Check for OpenRouter first (unified API for all models)
    api_key = get("SMI_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", ...)
    
    base_url = get("SMI_API_BASE_URL", "OPENROUTER_BASE_URL") or "https://api.openai.com/v1"
    
    # Auto-detect OpenRouter and set sensible defaults
    is_openrouter = "openrouter.ai" in base_url.lower()
    if is_openrouter:
        # OpenRouter-specific defaults
        if not model:
            model = "anthropic/claude-sonnet-4"  # sensible default
        # OpenRouter supports reasoning models transparently
        # No need for provider-specific thinking flags
```

### 2. Create Multi-Model Runner Script

**New file**: `benchmark/scripts/run_multi_model.sh`

Similar to `sui-move-eval/run_all_models.sh`:

```bash
#!/bin/bash
# Run Phase II benchmark on multiple models via OpenRouter

# Models to benchmark
MODELS=(
    "anthropic/claude-sonnet-4"
    "anthropic/claude-opus-4"
    "openai/gpt-4o"
    "openai/gpt-4o-mini"
    "deepseek/deepseek-v3"
    "z-ai/glm-4.7"
    "google/gemini-2.0-flash-exp"
)

SAMPLES=${1:-10}  # Default 10 packages
PARALLEL=${2:-2}  # Run 2 models at a time
MANIFEST="manifests/standard_phase2_no_framework.txt"
OUTPUT_DIR="results/multi_model_$(date +%Y%m%d_%H%M%S)"

# Function to run single model
run_model() {
    local model="$1"
    local output_dir="$2"
    
    filename=$(echo "$model" | sed 's|/|_|g')
    
    # Set model via env var override
    SMI_MODEL="$model" \
    SMI_API_BASE_URL="https://openrouter.ai/api/v1" \
    uv run smi-inhabit \
        --corpus-root ../sui-packages/packages/mainnet_most_used \
        --package-ids-file "$MANIFEST" \
        --agent real-openai-compatible \
        --samples "$SAMPLES" \
        --rpc-url https://fullnode.mainnet.sui.io:443 \
        --simulation-mode dry-run \
        --continue-on-error \
        --out "$output_dir/${filename}.json" \
        > "$output_dir/${filename}.log" 2>&1
}

# Use GNU parallel or background jobs
export -f run_model
printf '%s\n' "${MODELS[@]}" | parallel --line-buffer -j "$PARALLEL" \
    run_model {} "$OUTPUT_DIR"
```

### 3. Create Leaderboard Script

**New file**: `benchmark/scripts/multi_model_leaderboard.py`

```python
#!/usr/bin/env python3
"""
Generate leaderboard from multi-model Phase II results.

Usage:
    python scripts/multi_model_leaderboard.py results/multi_model_*/
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ModelResult:
    model: str
    total: int
    selection_rate: float
    build_success_rate: float
    dry_run_success_rate: float
    hit_rate: float
    avg_created_types: float
    
def load_results(result_dir: Path) -> dict[str, ModelResult]:
    """Load all model results from a directory."""
    results = {}
    
    for json_file in result_dir.glob("*.json"):
        if json_file.name.startswith("_"):
            continue
            
        model_name = json_file.stem.replace("_", "/")
        
        with open(json_file) as f:
            data = json.load(f)
        
        # Extract aggregate metrics
        agg = data.get("aggregate", {})
        results[model_name] = ModelResult(
            model=model_name,
            total=agg.get("total_packages", 0),
            selection_rate=agg.get("selection_rate", 0.0),
            build_success_rate=agg.get("build_success_rate", 0.0),
            dry_run_success_rate=agg.get("dry_run_success_rate", 0.0),
            hit_rate=agg.get("hit_rate", 0.0),
            avg_created_types=agg.get("avg_created_types_per_package", 0.0),
        )
    
    return results

def print_leaderboard(results: dict[str, ModelResult]):
    """Print sorted leaderboard."""
    # Sort by hit_rate descending
    sorted_results = sorted(results.values(), key=lambda x: x.hit_rate, reverse=True)
    
    print("\n=== PHASE II LEADERBOARD (sorted by hit rate) ===\n")
    print(f"{'Model':<40} {'Hit Rate':>10} {'Dry-run':>10} {'Build':>10} {'Select':>10}")
    print(f"{'-'*40} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    
    for r in sorted_results:
        print(f"{r.model:<40} {r.hit_rate*100:>9.1f}% {r.dry_run_success_rate*100:>9.1f}% "
              f"{r.build_success_rate*100:>9.1f}% {r.selection_rate*100:>9.1f}%")
    
    print(f"\nBaseline (baseline-search): 2.6% hit rate")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python multi_model_leaderboard.py <results_dir>")
        sys.exit(1)
    
    result_dir = Path(sys.argv[1])
    results = load_results(result_dir)
    print_leaderboard(results)
```

### 4. Update .env.example

**File**: `benchmark/.env.example`

Add OpenRouter section:

```bash
# ===================================================================
# OpenRouter (Unified API for All Models)
# ===================================================================
# 
# OpenRouter provides a single API for 150+ models from different providers.
# No need for provider-specific configuration!
#
# Get your API key at: https://openrouter.ai/
#
# OPENROUTER_API_KEY=sk-or-v1-...
# SMI_API_BASE_URL=https://openrouter.ai/api/v1
# SMI_MODEL=anthropic/claude-sonnet-4
#
# Popular models:
#   - anthropic/claude-opus-4
#   - anthropic/claude-sonnet-4
#   - openai/gpt-4o
#   - openai/gpt-4o-mini
#   - deepseek/deepseek-v3
#   - z-ai/glm-4.7
#   - google/gemini-2.0-flash-exp
#
# For multi-model benchmarking, use:
#   ./scripts/run_multi_model.sh 10 2  # 10 samples, 2 parallel
#
# ===================================================================

# Default: OpenAI
SMI_API_KEY=REPLACE_ME
SMI_API_BASE_URL=https://api.openai.com/v1
SMI_MODEL=gpt-4o-mini
```

### 5. Add OpenRouter Detection Logic

**File**: `benchmark/src/smi_bench/agents/real_agent.py`

```python
class RealAgent:
    def __init__(self, cfg: RealAgentConfig, client: httpx.Client | None = None) -> None:
        self.cfg = cfg
        self._client = client or httpx.Client(timeout=60)
        
        # Detect OpenRouter
        self.is_openrouter = "openrouter.ai" in cfg.base_url.lower()
        
        # Auto-adjust token limits for reasoning models
        self.is_reasoning_model = any(
            x in cfg.model.lower() 
            for x in ["deepseek", "o1", "o3", "glm", "qwen"]
        )
        
        # OpenRouter-specific headers
        if self.is_openrouter:
            # OpenRouter requires specific headers for optimal routing
            self._client.headers.update({
                "HTTP-Referer": "https://github.com/MystenLabs/sui-move-interface-extractor",
                "X-Title": "Sui Move Interface Extractor Benchmark"
            })

    def complete_type_list(self, prompt: str, *, timeout_s: float | None = None) -> set[str]:
        # ... existing code ...
        
        # Auto-adjust max_tokens for reasoning models
        if self.cfg.max_tokens is None and self.is_reasoning_model:
            payload["max_tokens"] = 4000  # Reasoning models need more tokens
        elif self.cfg.max_tokens is not None:
            payload["max_tokens"] = self.cfg.max_tokens
        
        # OpenRouter doesn't need provider-specific thinking flags
        # It handles this transparently based on model capabilities
        if not self.is_openrouter:
            if self.cfg.thinking:
                payload["thinking"] = {"type": self.cfg.thinking}
                if self.cfg.clear_thinking is not None:
                    payload["thinking"]["clear_thinking"] = self.cfg.clear_thinking
        
        # ... rest of existing code ...
```

### 6. Create Quick Start Guide

**New file**: `benchmark/docs/OPENROUTER_QUICKSTART.md`

```markdown
# OpenRouter Multi-Model Benchmarking

## Quick Start

### 1. Get OpenRouter API Key

Sign up at [openrouter.ai](https://openrouter.ai/) and get your API key.

### 2. Configure

```bash
cd benchmark
cp .env.example .env
# Edit .env:
# OPENROUTER_API_KEY=sk-or-v1-...
# SMI_API_BASE_URL=https://openrouter.ai/api/v1
```

### 3. Run Multi-Model Benchmark

```bash
# Test 10 packages across 7 models (2 at a time)
./scripts/run_multi_model.sh 10 2

# View leaderboard
python scripts/multi_model_leaderboard.py results/multi_model_*/
```

### 4. Run Single Model

```bash
# Override model via env var
SMI_MODEL="deepseek/deepseek-v3" \
uv run smi-inhabit \
  --corpus-root ../sui-packages/packages/mainnet_most_used \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --agent real-openai-compatible \
  --samples 10 \
  --out results/deepseek_test.json
```

## Supported Models

All OpenRouter models work out-of-the-box. Popular choices:

| Provider | Model | OpenRouter Name |
|----------|-------|-----------------|
| Anthropic | Claude Opus 4 | `anthropic/claude-opus-4` |
| Anthropic | Claude Sonnet 4 | `anthropic/claude-sonnet-4` |
| OpenAI | GPT-4o | `openai/gpt-4o` |
| DeepSeek | DeepSeek V3 | `deepseek/deepseek-v3` |
| Z.AI | GLM-4.7 | `z-ai/glm-4.7` |
| Google | Gemini 2.0 Flash | `google/gemini-2.0-flash-exp` |

Full list: https://openrouter.ai/models
```

## Implementation Steps

### Phase 1: Core Integration (30 min)
1. ✅ Update `real_agent.py` to support `OPENROUTER_API_KEY`
2. ✅ Add OpenRouter auto-detection logic
3. ✅ Update `.env.example` with OpenRouter section

### Phase 2: Multi-Model Scripts (20 min)
4. ✅ Create `run_multi_model.sh`
5. ✅ Create `multi_model_leaderboard.py`
6. ✅ Test with 2-3 models on small sample

### Phase 3: Documentation (10 min)
7. ✅ Create `OPENROUTER_QUICKSTART.md`
8. ✅ Update main `README.md` with OpenRouter section
9. ✅ Add examples to `QUICKSTART.md`

### Phase 4: Testing (15 min)
10. ✅ Test Phase I with OpenRouter
11. ✅ Test Phase II with OpenRouter
12. ✅ Verify leaderboard generation
13. ✅ Test parallel execution

## Benefits

### Before (Current State)
```bash
# Test 5 models = 5 manual runs, update .env each time
vim .env  # Change model
uv run smi-inhabit ... --out model1.json
vim .env  # Change model again
uv run smi-inhabit ... --out model2.json
# ... repeat 5 times ...
# Manually compare results
```

### After (With OpenRouter)
```bash
# Test 5 models = one command
./scripts/run_multi_model.sh 10 2
python scripts/multi_model_leaderboard.py results/multi_model_*/
```

**Time savings**: ~80% reduction (5 manual runs → 1 automated batch)

## Compatibility

- ✅ **Backward compatible**: Existing `.env` configs still work
- ✅ **No code changes**: Current benchmarks run unchanged
- ✅ **Optional feature**: Users can continue using direct provider APIs

## Cost Optimization

OpenRouter charges slightly more than direct APIs (~10-20% markup), but provides:
- ✅ Single API key management
- ✅ Automatic failover to alternative providers
- ✅ Built-in rate limiting
- ✅ Usage analytics dashboard

For large-scale benchmarks (100+ packages), consider using direct APIs with provider-specific config.
