# AGENTS.md — sui-move-interface-extractor

## Project Overview

**Purpose**: Standalone Rust CLI for bytecode-first analysis of Sui Move packages.

**Core outputs**:
- Deterministic, canonical bytecode-derived interface JSON (`--emit-bytecode-json`)
- Deterministic corpus reports (`corpus_report.jsonl`, `problems.jsonl`, `corpus_summary.json`)
- Rigorous comparator vs Sui RPC normalized interfaces (mismatch counts + sampled mismatch paths)

**Design goals**:
- Prefer **bytecode ground truth** (Move binary format) over source/decompilation.
- Produce **diff-friendly** outputs (stable ordering and canonical formatting).
- Provide **verification loops** (RPC cross-check, corpus integrity checks, run attribution metadata).

## Repo Structure

```
.
├── AGENTS.md
├── Cargo.toml
├── docs/
├── src/
│   └── main.rs
├── scripts/
└── results/
```

## Key Guardrails

- Keep output deterministic: maintain stable sorting and JSON canonicalization.
- Any breaking schema change must bump `schema_version` and update `docs/SCHEMA.md`.
- Corpus runs should always remain attributable:
  - keep writing `run_metadata.json` (argv, rpc_url, timestamps, dataset git HEAD when available).
- Avoid hard-coding local workspace paths in docs or code; show examples as placeholders.

## Development Workflow

### Commands

```bash
cargo fmt
cargo clippy
cargo test
```

### Testing philosophy

- Prefer unit tests for:
  - type normalization
  - comparator behavior (match/mismatch)
  - address normalization/stability rules
- Avoid “network tests” in CI by default. If a networked integration test is added, gate it behind an env var.

## Style

- Rust: keep functions small, avoid panics in library-like code paths; return `anyhow::Result` with context.
- Prefer explicit structs for JSON schemas (and canonicalize output before writing).
- Keep docs current when adding new flags or outputs.

## Documentation Testing Standards

All documentation must be executable, verifiable, and maintainable.

### Executable Examples

**Every code example must:**
- Be copy-paste executable from the repository root
- Use clearly marked placeholders: `<CORPUS_ROOT>`, `<PACKAGE_ID>`
- Work on supported platforms (macOS, Linux)
- Specify expected exit codes and outputs

**Validation:**
```bash
# Test A2A documentation examples
python benchmark/scripts/test_doc_examples.py benchmark/A2A_GETTING_STARTED.md benchmark/docs/A2A_EXAMPLES.md
```

### Cross-Reference Validation

**Internal links:**
- All `[text](path.md)` links must resolve to existing files
- All `[text](#section)` anchors must exist
- Use relative paths over absolute

**Validation:**
```bash
# Validate Markdown links (offline)
python benchmark/scripts/validate_crossrefs.py --skip-external

# Validate including external links (slower)
python benchmark/scripts/validate_crossrefs.py
```

### Schema Synchronization

When `benchmark/docs/evaluation_bundle.schema.json` changes:
1. Update all documentation examples
2. Update `benchmark/docs/A2A_EXAMPLES.md` reference payloads
3. Update `benchmark/docs/ARCHITECTURE.md` invariants section
4. Add migration notes if breaking changes

**Reference:** See `benchmark/docs/TESTING.md` for complete testing procedures.

### Documentation Review Checklist

Before merging any doc changes:

- [ ] All code examples are tested and verified
- [ ] All links resolve (internal + external)
- [ ] Mermaid diagrams render correctly
- [ ] Placeholders are clearly marked
- [ ] Schema examples match current `.json` files
- [ ] Cross-references are bidirectional where appropriate
- [ ] Version-specific notes are clearly dated
- [ ] Commands use correct flag names and defaults

**Automated checks** (run in CI):
- `benchmark/scripts/test_doc_examples.py` - Validates command executability
- `benchmark/scripts/validate_crossrefs.py` - Validates Markdown links
- Schema validation - Ensures examples match current schema definition

**Related documentation:**
- `benchmark/docs/TESTING.md` - Complete testing guide
- `benchmark/docs/A2A_EXAMPLES.md` - Request/response examples
- `benchmark/A2A_GETTING_STARTED.md` - Quick start guide
