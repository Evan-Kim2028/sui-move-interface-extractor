# `benchmark/results/`

This folder is for **small, shareable** benchmark artifacts.

- Commit only small, stable artifacts (examples, manifests, short run JSON).
- Do not commit large per-run logs or caches.
- See `results/README.md` for the general “what to commit” policy.

## Phase I reporting note

Phase I (key-struct discovery) is evaluated under **partial information**:

- the prompt omits struct `abilities`, and
- the prompt may be truncated (bounded by `--max-structs-in-prompt`).

If you commit Phase I outputs (e.g. `phase1_run.json`), include the effective `--max-structs-in-prompt` (and any other relevant prompt limits) in the surrounding writeup / PR description.
