# `results/`

This folder is intended for **small, shareable artifacts**.

Recommended policy:

- Commit only `*_submission_summary.json` files produced by `--emit-submission-summary`.
- Do not commit large corpus outputs (`corpus_report.jsonl`, `problems.jsonl`, etc.). Those belong in `out/` (gitignored).
- For benchmark runs, prefer committing only small, stable example outputs and manifests (not per-run logs).

Included:

- `results/example_mainnet_most_used_submission_summary.json`: an example snapshot from one local run.
