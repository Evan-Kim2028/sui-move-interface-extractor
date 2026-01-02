# AgentBeats / “Green Agent” notes

This document explains how this repository maps onto the AgentX AgentBeats “green agent” evaluation workflow:

https://rdi.berkeley.edu/agentx-agentbeats

## What this repo is (for AgentBeats)

This repo is a bytecode-first toolchain for Sui Move packages.

It provides two pieces needed for an AgentBeats-style benchmark:

1) A deterministic, canonical representation of a package interface derived from Move bytecode tables.
2) Verification loops that quantify extraction correctness on a large corpus (`sui-packages`).

This is the substrate needed before we can fairly score an agent’s downstream reasoning (e.g., type inhabitation).

For the first-principles argument and limitations, see `docs/METHODOLOGY.md`.

## Current benchmark status

The `benchmark/` folder contains:

- Phase I: key-struct discovery (LLM predicts which structs have `key`)
- Phase II: inhabitation scaffold (PTB plan → simulate → score created key types)

Phase I is already a mechanically scorable “green agent” style task with no human labeling:

- truth comes from bytecode abilities
- scoring is precision/recall/F1 on the predicted key-type set

Phase II is the start of the “real” type inhabitation benchmark, but it is not yet a full on-chain simulation:

- Phase II prefers dry-run (ground truth) when available and falls back to a deterministic bytecode proxy when it can’t run.
- Dry-run requires a funded sender on the target network and a valid `TransactionData` (gas coin, gas budget, gas price).

To make Phase II dry-run reproducible, configure these in `benchmark/.env` (or pass flags):

- `SMI_SENDER`: address with at least one `Coin<SUI>` on the target network
- `SMI_GAS_COIN` (optional): specific gas coin object id to use

## How an external practitioner gets started

Prereqs:

- Rust toolchain
- Python 3.11+ and `uv`
- a local `sui-packages` checkout (dataset)

Suggested workflow:

1) Validate bytecode extraction on the corpus (Rust CLI):
   - `scripts/reproduce_mainnet_most_used.sh`
2) Run Phase I on a small sample with a real agent:
   - see `benchmark/README.md` (“Smoke test” and “Run 500 packages in batches”)
3) Inspect per-package failures and iterate:
   - `benchmark/scripts/phase1_analyze.py`

Phase I supports “exactly what was tested” tracking via a fixed id manifest and resume:

- generate manifests: `benchmark/scripts/make_mainnet_most_used_halves.py`
- run first 500 in 5-package batches: `benchmark/scripts/run_phase1_manifest_batches.sh`
- compute remaining ids: `benchmark/scripts/manifest_remaining.py`

## What remains to be “full type inhabitation”

To match the “PTB inhabitation” definition directly:

- generate a PTB that tries to create as many distinct `key` types as possible
- dry-run (or dev-inspect) and extract created object types from authoritative transaction outputs
- score by distinct key types created

This repo already provides:

- the target set: key types from bytecode abilities
- the interface substrate: full signature types and constructor candidates

What remains is the “agent runner + transaction executor + scorer” layer, packaged in the AgentBeats expected structure
(agent card, containerized runner, tool interface).

This repo intentionally stops at the benchmark substrate; build the A2A-compatible “green agent” wrapper on top once the benchmark definition stabilizes.
