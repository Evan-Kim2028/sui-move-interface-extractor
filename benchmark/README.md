## `benchmark/` (key struct target discovery)

This benchmark scores an agent on discovering **which structs have `key`** in a Sui Move package.

It uses `sui-move-interface-extractor` as the ground-truth parser for `.mv` bytecode artifacts.

### Setup

```bash
cd benchmark
uv sync --group dev --frozen
```

### Configure a real agent (optional)

Copy `benchmark/.env.example` to `benchmark/.env` and fill in:

- `SMI_API_KEY`
- `SMI_MODEL`
- `SMI_API_BASE_URL` (OpenAI-compatible base; for non-OpenAI providers)

Z.AI GLM-4.7 example:

```bash
cp .env.example .env
# set:
# If you’re on the GLM Coding Plan, use:
# SMI_API_BASE_URL=https://api.z.ai/api/coding/paas/v4
# (If you’re on Model API instead, use https://api.z.ai/api/paas/v4)
# SMI_MODEL=glm-4.7
# SMI_THINKING=enabled
# SMI_CLEAR_THINKING=true
# SMI_RESPONSE_FORMAT=json_object
# SMI_MAX_TOKENS=2048
```

Smoke test (does a single tiny API call and expects `{ "key_types": [] }` JSON):

```bash
uv run smi-bench --corpus-root <sui-packages-checkout>/packages/mainnet_most_used --smoke-agent --agent real-openai-compatible
```

Diagnostics (prints redacted config and probes `GET /models` + `POST /chat/completions`):

```bash
uv run smi-bench --corpus-root <sui-packages-checkout>/packages/mainnet_most_used --doctor-agent --agent real-openai-compatible
```

### Run (mock agents)

You need a local `sui-packages` checkout and a corpus root like `<sui-packages-checkout>/packages/mainnet_most_used`.

```bash
uv run smi-bench \
  --corpus-root <sui-packages-checkout>/packages/mainnet_most_used \
  --samples 25 --seed 1 \
  --agent mock-empty
```

### Output

The runner writes a small JSON report with per-package metrics and an aggregate summary.

### Phase II scaffold (type inhabitation)

`smi-inhabit` is a scaffold for the future “PTB type inhabitation” benchmark (build PTB → devInspect → score by created key types).

For now it supports only a fixture-based devInspect JSON (to validate scoring and wiring):

```bash
uv run smi-inhabit \
  --bytecode-package-dir /path/to/sui-packages/packages/mainnet/0x00/00000000000000000000000000000000000000000000000000000000000002 \
  --fixture-dev-inspect-json fixtures/dev_inspect_example.json \
  --agent mock-empty
```
