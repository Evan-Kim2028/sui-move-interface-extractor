# `results/`

This folder is intended for **small, shareable artifacts**.

Recommended policy:

- Commit only `*_submission_summary.json` files produced by `--emit-submission-summary`.
- Do not commit large corpus outputs (`corpus_report.jsonl`, `problems.jsonl`, etc.). Those belong in `out/` (gitignored).
- For benchmark runs, prefer committing only small, stable example outputs and manifests (not per-run logs).

## Benchmark reporting note (Phase I)

If you share Phase I (key-struct discovery) benchmark outputs, note that Phase I is evaluated under **partial information**:
the prompt omits struct `abilities` and may be truncated (bounded by `--max-structs-in-prompt`).

Included:

- `results/example_mainnet_most_used_submission_summary.json`: an example snapshot from one local run.
