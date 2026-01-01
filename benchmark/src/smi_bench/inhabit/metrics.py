from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Phase2Metrics:
    packages: int
    dry_run_ok: int
    any_hit: int
    hits: int
    targets: int
    created_distinct_sum: int
    macro_avg_hit_rate: float


def compute_phase2_metrics(*, rows: list[dict], aggregate: dict | None = None) -> Phase2Metrics:
    """
    Compute Phase II aggregate metrics from a run JSON's `packages[]` rows.
    """
    n = 0
    dry_run_ok = 0
    any_hit = 0
    hits = 0
    targets = 0
    created_distinct_sum = 0
    macro_sum = 0.0

    for r in rows:
        if not isinstance(r, dict):
            continue
        score = r.get("score")
        if not isinstance(score, dict):
            continue
        n += 1
        if r.get("dry_run_ok") is True:
            dry_run_ok += 1
        h = int(score.get("created_hits", 0) or 0)
        t = int(score.get("targets", 0) or 0)
        cd = int(score.get("created_distinct", 0) or 0)
        hits += h
        targets += t
        created_distinct_sum += cd
        if h > 0:
            any_hit += 1
        macro_sum += (h / t) if t else 0.0

    macro = (macro_sum / n) if n else 0.0
    # Prefer recorded macro if present (should match our computed macro).
    if isinstance(aggregate, dict):
        m = aggregate.get("avg_hit_rate")
        if isinstance(m, (int, float)):
            macro = float(m)

    return Phase2Metrics(
        packages=n,
        dry_run_ok=dry_run_ok,
        any_hit=any_hit,
        hits=hits,
        targets=targets,
        created_distinct_sum=created_distinct_sum,
        macro_avg_hit_rate=macro,
    )
