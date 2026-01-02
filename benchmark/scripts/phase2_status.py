from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python scripts/phase2_status.py <OUT_JSON>")
        raise SystemExit(0)

    path = Path(sys.argv[1])
    data = json.loads(path.read_text())
    samples = int(data.get("samples", 0))
    agg = data.get("aggregate") or {}
    errors = agg.get("errors")
    avg_hit_rate = agg.get("avg_hit_rate")
    max_hit_rate = agg.get("max_hit_rate")
    schema_violation_rate = agg.get("schema_violation_rate")
    schema_violation_attempts = agg.get("schema_violation_attempts")
    schema_violation_count = agg.get("schema_violation_count")
    semantic_failure_rate = agg.get("semantic_failure_rate")
    semantic_failure_attempts = agg.get("semantic_failure_attempts")
    semantic_failure_count = agg.get("semantic_failure_count")

    last_pkg = None
    last_err = None
    pkgs = data.get("packages")
    if isinstance(pkgs, list) and pkgs:
        last = pkgs[-1]
        if isinstance(last, dict):
            last_pkg = last.get("package_id")
            last_err = last.get("error")

    print(
        " ".join(
            [
                f"samples={samples}",
                f"errors={errors}",
                f"avg_hit_rate={avg_hit_rate}",
                f"max_hit_rate={max_hit_rate}",
                f"schema_violation_rate={schema_violation_rate}",
                f"schema_violation_attempts={schema_violation_attempts}",
                f"schema_violation_count={schema_violation_count}",
                f"semantic_failure_rate={semantic_failure_rate}",
                f"semantic_failure_attempts={semantic_failure_attempts}",
                f"semantic_failure_count={semantic_failure_count}",
                f"last_pkg={last_pkg}",
                f"last_error={last_err}",
            ]
        )
    )


if __name__ == "__main__":
    main()
