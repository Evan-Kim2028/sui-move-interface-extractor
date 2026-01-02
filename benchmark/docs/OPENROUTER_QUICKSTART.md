# OpenRouter Multi-Model Benchmarking - Quick Start

## Overview

OpenRouter provides a **unified API** for 150+ language models from different providers (Anthropic, OpenAI, DeepSeek, Google, etc.) using a single API key. This makes it ideal for benchmarking multiple models efficiently.

## Benefits

✅ **Single API key** for all models  
✅ **Parallel execution** (test 3-5 models simultaneously)  
✅ **Automatic model routing** and fallbacks  
✅ **No provider-specific configuration** needed  
✅ **Built-in rate limiting** and usage analytics  

## Quick Start

### 1. Get OpenRouter API Key

Sign up at [openrouter.ai](https://openrouter.ai/) and get your API key.

### 2. Configure Environment

```bash
cd benchmark
cp .env.example .env
```

Edit `.env` and set:
```bash
OPENROUTER_API_KEY=sk-or-v1-your_key_here
SMI_API_BASE_URL=https://openrouter.ai/api/v1
SMI_MODEL=anthropic/claude-sonnet-4.5  # default model
SMI_SENDER=0xYOUR_FUNDED_MAINNET_ADDRESS  # for dry-run
```

### 3. Test Single Model

```bash
# Quick test with OpenRouter
uv run smi-inhabit \
  --corpus-root ../sui-packages/packages/mainnet_most_used \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --agent real-openai-compatible \
  --samples 3 \
  --out results/openrouter_test.json
```

### 4. Run Multi-Model Benchmark

Test 10 models in parallel (matches sui-move-eval models):

```bash
./scripts/run_multi_model.sh 10 3
```

This runs:
- **10 packages** per model
- **3 models in parallel** (adjust based on API rate limits)
- **~30-60 minutes** total runtime

Full benchmark (290 packages):
```bash
./scripts/run_multi_model.sh 290 2
```

### 5. View Results

```bash
# Results are automatically summarized
cat results/multi_model_*/summary.txt

# Detailed per-model analysis
python scripts/phase2_status.py results/multi_model_*/anthropic_claude-sonnet-4.5.json
```

## Supported Models

The `run_multi_model.sh` script tests the same models as `sui-move-eval`:

| Provider | Model | OpenRouter Name |
|----------|-------|-----------------|
| Z.AI | GLM-4.7 | `z-ai/glm-4.7` |
| MiniMax | MiniMax M2.1 | `minimax/minimax-m2.1` |
| OpenAI | GPT-5.2 | `openai/gpt-5.2` |
| OpenAI | GPT-4o Mini | `openai/gpt-4o-mini` |
| X.AI | Grok Code Fast 1 | `x-ai/grok-code-fast-1` |
| Anthropic | Claude Sonnet 4.5 | `anthropic/claude-sonnet-4.5` |
| Anthropic | Claude Opus 4.5 | `anthropic/claude-opus-4.5` |
| Google | Gemini 3 Flash | `google/gemini-3-flash-preview` |
| DeepSeek | DeepSeek V3.2 | `deepseek/deepseek-v3.2` |
| KwaiPilot | KAT Coder Pro | `kwaipilot/kat-coder-pro:free` |

**Full model list**: https://openrouter.ai/models

## Advanced Usage

### Override Model Per Run

```bash
# Test a specific model without changing .env
SMI_MODEL="deepseek/deepseek-v3.2" \
uv run smi-inhabit \
  --corpus-root ../sui-packages/packages/mainnet_most_used \
  --package-ids-file manifests/standard_phase2_no_framework.txt \
  --agent real-openai-compatible \
  --samples 10 \
  --out results/deepseek_test.json
```

### Custom Model List

Edit `scripts/run_multi_model.sh` and modify the `MODELS` array:

```bash
MODELS=(
    "anthropic/claude-sonnet-4.5"
    "openai/gpt-4o"
    "your/custom-model"
)
```

### Adjust Parallelism

```bash
# Run 5 models at once (requires higher rate limits)
./scripts/run_multi_model.sh 10 5

# Sequential execution (1 at a time)
./scripts/run_multi_model.sh 10 1
```

## Cost Optimization

OpenRouter charges a small markup (~10-20%) over direct provider APIs, but provides:

- ✅ Single API key management
- ✅ Automatic failover
- ✅ Usage analytics dashboard
- ✅ No need to manage multiple provider accounts

**For large-scale benchmarks** (1000+ packages), consider:
- Using direct provider APIs with provider-specific config
- Running models sequentially to avoid rate limits
- Testing on a small sample first (10-50 packages)

## Troubleshooting

### Rate Limit Errors

```bash
# Reduce parallelism
./scripts/run_multi_model.sh 10 1

# Or add delays between runs (edit run_multi_model.sh)
```

### Authentication Errors

```bash
# Verify API key is set
echo $OPENROUTER_API_KEY

# Check .env file
cat .env | grep OPENROUTER
```

### Model Not Available

Some models require specific plans or permissions. Check:
- https://openrouter.ai/models for availability
- Your OpenRouter account credits/limits

## Comparison: OpenRouter vs Direct APIs

| Feature | OpenRouter | Direct APIs |
|---------|-----------|-------------|
| API Keys | 1 | 3-5 (per provider) |
| Setup | Minimal | Provider-specific |
| Cost | +10-20% markup | Direct pricing |
| Rate Limits | Unified | Per-provider |
| Failover | Automatic | Manual |
| Best For | Multi-model testing | Production use at scale |

## Next Steps

1. **Run quick test**: `./scripts/run_multi_model.sh 3 1`
2. **Review results**: Check `results/multi_model_*/` directory
3. **Full benchmark**: `./scripts/run_multi_model.sh 290 2`
4. **Compare runs**: Use `scripts/phase2_leaderboard.py`

For more details, see:
- `benchmark/README.md` - Full benchmark documentation
- `benchmark/QUICKSTART.md` - Phase II quick start
- `benchmark/docs/METHODOLOGY.md` - Scoring methodology
