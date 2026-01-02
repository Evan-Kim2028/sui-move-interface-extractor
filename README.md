# `sui-move-interface-extractor`

Standalone bytecode-first Rust CLI for parsing Sui Move `.mv` modules and producing deterministic, diff-friendly JSON interfaces.

It parses compiled `.mv` modules directly and emits canonical JSON for:

- corpus-level scanning/verification (index + counts + diff stability)
- bytecode-derived interfaces (`--emit-bytecode-json`) including private functions and full signature types
- rigorous comparison against RPC normalized interfaces (`--compare-bytecode-rpc`)

## Docs

- Start here: `docs/README.md`
- Schema: `docs/SCHEMA.md`
- Run commands: `docs/RUNBOOK.md`
- Methodology/limits: `docs/METHODOLOGY.md`

## Dataset (bytecode corpus) location

Pass an explicit corpus root via `--bytecode-corpus-root`.

If you use the `sui-packages` dataset (a local artifact corpus), point at a corpus root like:

- `<sui-packages-checkout>/packages/mainnet_most_used`
- `<sui-packages-checkout>/packages/mainnet`

Each package dir is expected to contain `bytecode_modules/*.mv` and typically includes `metadata.json` and `bcs.json`.

## Quickstart

Prereqs:

- Rust toolchain (stable): https://rustup.rs
- `git`

Dataset:

```bash
git clone https://github.com/MystenLabs/sui-packages.git
```

Emit a canonical interface JSON from a local artifact dir:

```bash
mkdir -p out
cargo run --release -- \
  --bytecode-package-dir ../sui-packages/packages/mainnet_most_used/0x00/00000000000000000000000000000000000000000000000000000000000002 \
  --emit-bytecode-json out/0x2_interface.json \
  --sanity
```

Notes:

- `out/` is a scratch directory for large outputs (gitignored).
- `results/` is intended for small, shareable summary JSONs only.

For corpus runs and reproducible validation loops, use `docs/RUNBOOK.md` or:

- `scripts/reproduce_mainnet_most_used.sh`

## Benchmarks

The Python benchmark harness lives in `benchmark/`:

- `benchmark/README.md`

## AgentBeats / Berkeley “Green Agent” (AgentX)

This repo is designed to be a clean substrate for building AgentBeats-style evaluations on Sui Move bytecode.

- Competition/homepage: https://rdi.berkeley.edu/agentx-agentbeats
- This repo provides:
  - bytecode-first interface extraction (canonical JSON; includes private functions)
  - verification loops against RPC normalized interfaces (corpus reports + mismatch samples)
  - benchmark scaffolding in `benchmark/` (Phase I + Phase II)
- See `docs/AGENTBEATS.md` for how Phase I/II map to an AgentBeats “green agent” workflow and what remains to implement.

## Docker

Build:

```bash
docker build -t sui-move-interface-extractor .
```

Run the Rust CLI:

```bash
docker run --rm sui-move-interface-extractor sui_move_interface_extractor --help
```

Run the benchmark (mount a local `sui-packages` checkout):

```bash
docker run --rm -v "$(pwd)/../sui-packages:/data/sui-packages" sui-move-interface-extractor \
  smi-bench --corpus-root /data/sui-packages/packages/mainnet_most_used --samples 25 --seed 1 --agent mock-empty
```

For more commands (single-package RPC compare, full corpus runs, sampling, and how to interpret outputs), see `docs/RUNBOOK.md`.
