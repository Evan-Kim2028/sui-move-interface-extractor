# Getting Started with Phase II Benchmark

This guide is the canonical entrypoint for running the Phase II (Type Inhabitation) benchmark: setup → first run → interpreting results.

## Quick start (5 minutes)

```bash
cd benchmark
uv sync --group dev --frozen
cd .. && cargo build --release --locked && cd benchmark
git clone --depth 1 https://github.com/MystenLabs/sui-packages.git ../sui-packages
cp .env.example .env
```

Then run a small Phase II targeted sample:

```bash
cd benchmark
./scripts/run_model.sh --env-file ./.env --model openai/gpt-5.2 \
  --phase2-targeted --scan-samples 50 --run-samples 10 --per-package-timeout-seconds 60
```

---

## 1) One-time setup

### Dependencies

We use `uv` for Python dependency management and `cargo` for Rust components.

```bash
cd benchmark
uv sync --group dev --frozen

# Build Rust binaries (extractor and transaction simulator)
cd .. && cargo build --release --locked && cd benchmark
```

### Clone the corpus

```bash
git clone --depth 1 https://github.com/MystenLabs/sui-packages.git ../sui-packages
```

### Credentials configuration

Copy `.env.example` to `.env` and set your model credentials.

```bash
cp .env.example .env
```

Recommended (OpenRouter): one key for many models.

```env
OPENROUTER_API_KEY=sk-or-v1-...
SMI_API_BASE_URL=https://openrouter.ai/api/v1
SMI_MODEL=anthropic/claude-sonnet-4.5

# Optional but recommended for "real" dry-runs (see note below)
SMI_SENDER=0xYOUR_FUNDED_MAINNET_ADDRESS
```

### Important: `sender` / inventory expectations

- If you run with an unfunded sender or `sender=0x0`, many packages are effectively "inventory empty".
- In that mode, it is normal to see:
  - `dry_run_ok=true` for harmless/no-op PTBs, while
  - `created_hits=0` because target types require existing objects/caps or init paths.

If your near-term goal is **framework stability**, prioritize `dry_run_ok` and timeout/error rates.

---

## 2) Choose your entrypoint

### A) Fast local run (single model)

Use this when you want to quickly iterate on benchmarking and see a JSON output file.

```bash
cd benchmark
./scripts/run_model.sh --env-file ./.env --model openai/gpt-5.2 \
  --phase2-targeted --scan-samples 50 --run-samples 10 --per-package-timeout-seconds 60
```

Model slug sanity check (avoids "no requests" surprises):

```bash
cd benchmark
./scripts/run_model.sh --help
```

### B) Multi-model comparison

Use this when you want the same workload executed across multiple models.

```bash
cd benchmark
./scripts/run_multi_model.sh --env-file ./.env \
  --models "openai/gpt-5.2,google/gemini-3-flash-preview" \
  --parallel 1 \
  --scan-samples 50 --run-samples 10 --per-package-timeout-seconds 60
```

Notes:
- Start with `--parallel 1` to avoid RPC rate limits; increase gradually.

### C) A2A / AgentBeats integration

Use this when you want the A2A scenario (green/purple agents) and JSON-RPC artifacts.

```bash
cd benchmark
uv run smi-agentbeats-scenario scenario_smi --launch-mode current
uv run smi-a2a-smoke --scenario scenario_smi --corpus-root ../sui-packages/packages/mainnet_most_used --samples 1
```

See `docs/A2A_EXAMPLES.md` for copy-paste request/response examples.

---

## 3) Results-first: what to look at

The Phase II output JSON contains per-package rows and an aggregate summary.

Key fields to watch first:
- `aggregate.errors` and per-package `error` (harness/runtime failures)
- `packages[*].timed_out` (timeouts)
- `packages[*].dry_run_ok` and `packages[*].dry_run_effects_error` (execution success vs failure class)
- `packages[*].score.created_hits` (task success; may be 0 for inventory-constrained packages)

**Key distinction:**
- `dry_run_ok`: Transaction executed without aborting (runtime success)
- `created_hits`: Target types were actually created (task success)

Example: Agent calls `init_wrapper()` instead of `mint_coin()` → transaction succeeds (`dry_run_ok=true`) but creates no coins (`created_hits=0`).

Helpers:

```bash
# View run status
python scripts/phase2_status.py results/my_run.json

# Compare multiple runs (leaderboard)
python scripts/phase2_leaderboard.py results/run_a.json results/run_b.json
```

---

## 4) Troubleshooting

- Rate limits (RPC/OpenRouter): reduce `--parallel` (multi-model) and/or lower `--run-samples`.
- "No requests": confirm you used the exact model id shown in `./scripts/run_model.sh --help`.
- Port conflicts (A2A): check ports 9999 (Green) / 9998 (Purple).

---

## Related documentation

- `../docs/METHODOLOGY.md` - Scoring rules and extraction logic.
- `docs/A2A_COMPLIANCE.md` - Protocol implementation details.
- `docs/A2A_EXAMPLES.md` - Concrete JSON-RPC request/response examples.
