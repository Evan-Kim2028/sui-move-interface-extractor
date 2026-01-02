from __future__ import annotations

import argparse
import json
from pathlib import Path

from smi_bench.inhabit.metrics import compute_phase2_metrics


def main() -> None:
    p = argparse.ArgumentParser(description="Compute aggregate Phase II metrics for a run output JSON")
    p.add_argument("out_json", type=Path)
    args = p.parse_args()

    data = json.loads(args.out_json.read_text())
    rows = data.get("packages")
    if not isinstance(rows, list):
        raise SystemExit("invalid out json: missing packages[]")

    aggregate = data.get("aggregate") if isinstance(data.get("aggregate"), dict) else {}
    m = compute_phase2_metrics(rows=rows, aggregate=aggregate)
    micro = (m.hits / m.targets) if m.targets else 0.0

    # Optional fields (present in newer run outputs).
    schema_violation_rate = aggregate.get("schema_violation_rate")
    schema_violation_attempts = aggregate.get("schema_violation_attempts")
    schema_violation_count = aggregate.get("schema_violation_count")
    semantic_failure_rate = aggregate.get("semantic_failure_rate")
    semantic_failure_attempts = aggregate.get("semantic_failure_attempts")
    semantic_failure_count = aggregate.get("semantic_failure_count")

    print(f"run={args.out_json}")
    print(f"packages={m.packages}")
    print(f"dry_run_ok_rate={(m.dry_run_ok / m.packages) if m.packages else 0.0:.3f} ({m.dry_run_ok}/{m.packages})")
    print(f"any_hit_rate={(m.any_hit / m.packages) if m.packages else 0.0:.3f} ({m.any_hit}/{m.packages})")
    print(f"macro_avg_hit_rate={m.macro_avg_hit_rate:.6f}")
    print(f"micro_hit_rate={micro:.6f} (hits={m.hits} targets={m.targets})")
    print(f"avg_created_distinct={(m.created_distinct_sum / m.packages) if m.packages else 0.0:.3f}")

    if schema_violation_rate is not None:
        print(f"schema_violation_rate={float(schema_violation_rate):.3f}")
    if schema_violation_attempts is not None and schema_violation_count is not None:
        print(f"schema_violations={int(schema_violation_attempts)} pkgs, {int(schema_violation_count)} total")
    if isinstance(aggregate.get("schema_violation_attempts_until_first_valid"), list):
        vals = [int(x) for x in aggregate["schema_violation_attempts_until_first_valid"] if isinstance(x, int)]
        if vals:
            print(f"schema_violation_first_valid_attempt_avg={sum(vals) / len(vals):.2f}")
    if semantic_failure_rate is not None:
        print(f"semantic_failure_rate={float(semantic_failure_rate):.3f}")
    if semantic_failure_attempts is not None and semantic_failure_count is not None:
        print(f"semantic_failures={int(semantic_failure_attempts)} pkgs, {int(semantic_failure_count)} total")
    if isinstance(aggregate.get("semantic_failure_attempts_until_first_success"), list):
        vals = [int(x) for x in aggregate["semantic_failure_attempts_until_first_success"] if isinstance(x, int)]
        if vals:
            print(f"semantic_failure_first_success_attempt_avg={sum(vals) / len(vals):.2f}")


if __name__ == "__main__":
    main()
