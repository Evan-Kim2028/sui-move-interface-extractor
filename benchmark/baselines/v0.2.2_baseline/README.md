# Baseline v0.2.2 - Phase II Inhabitation

This baseline represents the **"Zero-Intelligence Floor"** for the Phase II (Type Inhabitation) benchmark.

## Configuration
- **Date**: January 1, 2026
- **Corpus**: `mainnet_most_used` (~1000 packages)
- **Agent**: `baseline-search` (Mechanical loop over candidates)
- **Search Depth**: 3 (Recursive constructor discovery enabled)
- **Max Candidates**: 20 per package
- **Heuristic Variants**: 4 (Default)
- **Judge**: Sui Mainnet `dry-run`
- **Sender**: Funded wallet with real SUI coins

## Summary Metrics
- **Selected Packages**: 292 (29.2% of corpus)
- **Avg Hit Rate**: **0.026** (2.6% of target key-types created)
- **Errors**: 0

## Analysis
The search successfully unlocked construction for `String`, `Option`, and custom local structs via recursive chaining. However, most executions (97.4%) still fail or produce no key types because they require:
1. **Specific Object IDs**: Many functions need a precise object ID (e.g. a specific Pool or AdminCap) which mechanical search cannot guess.
2. **Semantic Parameters**: Functions often abort if passed default values like `1` or `true` when a specific logic condition is expected.

Any AI agent must outperform this **2.6%** floor to demonstrate semantic reasoning capabilities.
