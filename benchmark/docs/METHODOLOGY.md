# Benchmark Methodology — Phase II (Type Inhabitation)

This document describes the technical implementation and scoring rules for the Phase II inhabitation benchmark.

## Core Objective
The goal of Phase II is to measure an agent's ability to **construct valid transactions** that result in the creation of specific Move `key` structs (objects) defined in a package.

## Scoring definition (Phase II)

### Targets (truth)

- Targets are derived from bytecode-derived interfaces: all structs in the package whose abilities include `key`.
- Targets are represented as Sui type strings like `0xADDR::module::Struct`.

### Created types (evidence)

- In strict mode (`--simulation-mode dry-run --require-dry-run`), created types come from the transaction simulation result (dry-run), which includes created object type strings.
- The harness may optionally fall back to dev-inspect (depending on flags); this is weaker evidence and is not recommended for “official” scoring.

### Primary metric: base-type hit rate

We score by matching **base types**:

- normalize addresses in type strings (pad `0x...` to 32 bytes), and
- ignore type arguments when comparing (e.g., `Coin<SUI>` and `Coin<FOO>` share base type `Coin`).

Per package:

- `targets`: number of distinct target key base types
- `created_hits`: number of target key base types created at least once
- `hit_rate`: `created_hits / targets`

## The Mechanical Baseline (`baseline-search`)
We use a deterministic, non-LLM baseline to establish the "floor" of the benchmark. This agent follows these rules:

### 1. Candidate Selection
The agent identifies all "runnable" functions in a package. A function is runnable if:
- It is `public entry`.
- All its parameters can be constructed (see below).
- Generic type parameters are present (it automatically fills them with `0x2::sui::SUI`).

### 2. Recursive Constructor Discovery
If a function requires a struct type `T` that is not a supported primitive, the agent scans the package for a **Constructor**:
- A `public` function that returns exactly one value of type `T`.
- The agent recursively attempts to construct the parameters of this constructor.
- **Search Depth**: Limited to **3 levels** to prevent infinite recursion and excessively long transactions.

### 3. PTB Chaining
The baseline agent uses the **Programmable Transaction Block (PTB)** features of Sui to chain these calls:
1. Calls the Constructor(s).
2. Uses the `Result(i)` of the constructor as an argument for the next step.
3. Finally calls the Target function.

## Type Construction Rules
The following types have specialized construction logic:
- **`0x1::string::String`**: Constructed via `0x1::string::utf8(vector<u8>)`.
- **`0x1::ascii::String`**: Constructed via `0x1::ascii::string(vector<u8>)`.
- **`0x2::url::Url`**: Constructed via `0x2::url::new_unsafe_from_bytes(vector<u8>)`.
- **`0x1::option::Option<T>`**: Constructed via `0x1::option::none<T>()`.

## Tiered Metrics
We distinguish between the ability to *plan* a transaction and the ability to *execute* it:

| Tier | Metric | Meaning |
| :--- | :--- | :--- |
| **Selection** | `n` packages | The logic found at least one sequence of calls that *should* work. |
| **Build** | `tx_build_ok` | The binary successfully generated valid BCS bytes for the transaction. |
| **Execution** | `dry_run_ok` | The transaction successfully simulated on-chain without aborting. |
| **Score** | `hit_rate` | The percentage of target key-types actually created during execution. |

## Known Limitations
- **Inventory Dependency**: Many functions require existing objects (e.g. `&mut Pool`). The baseline currently uses a "Placeholder" system that only works if the runner has a matching object in its inventory.
- **Semantic Data**: The baseline uses "dumb" defaults (`u64: 1`, `string: "sui"`). AI agents are expected to beat the baseline by inferring more appropriate values.
- **Generic type args in baselines**: The baseline’s heuristic of filling type params with `0x2::sui::SUI` is pragmatic but may not reflect “correct” instantiations for a package; it can reduce baseline performance on heavily generic APIs.
- **Simulation strictness**: By default, the harness may fall back to dev-inspect when dry-run fails (depending on flags). For “official” evaluations, prefer **strict dry-run-only** runs using `--simulation-mode dry-run --require-dry-run` so created types come from transaction-ground-truth.
- **Sender standardization**: Results depend on the sender’s on-chain inventory (owned objects) because many entry functions require existing objects. Using a consistent, shared funded sender address improves comparability across runs, but it is still a meaningful limitation and should be treated as part of the benchmark setup.

---

## Note on Phase I (Key-Struct Discovery)

Phase I uses the same bytecode-derived interface JSON as the source of truth for which structs have the `key` ability.
However, to avoid trivial leakage, the model prompt intentionally:

- **omits struct `abilities`**, and
- may include only a **truncated subset** of structs (bounded by `--max-structs-in-prompt`).

As a result, Phase I measures “key-struct discovery under partial information,” and results should be reported alongside the effective `--max-structs-in-prompt` (and any other prompt-shaping limits).
