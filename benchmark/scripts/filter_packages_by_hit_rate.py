from __future__ import annotations

import argparse
import json
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Filter Phase II packages by created_hits >= min_hits")
    p.add_argument("out_json", type=Path, help="Phase II output JSON (the --out file)")
    p.add_argument("--min-hits", type=int, default=1, help="Minimum created_hits required (default: 1)")
    p.add_argument("--out", type=Path, default=None, help="Write package ids to this file (default: stdout)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    data = json.loads(args.out_json.read_text())
    pkgs = data.get("packages")
    if not isinstance(pkgs, list):
        raise SystemExit("Invalid results JSON: missing 'packages' list")

    out_ids: list[str] = []
    for row in pkgs:
        if not isinstance(row, dict):
            continue
        pkg_id = row.get("package_id")
        score = row.get("score")
        if not isinstance(pkg_id, str) or not pkg_id:
            continue
        if not isinstance(score, dict):
            continue
        hits = score.get("created_hits")
        if isinstance(hits, int) and hits >= args.min_hits:
            out_ids.append(pkg_id)

    content = "".join(f"{pid}\n" for pid in out_ids)
    if args.out is None:
        print(content, end="")
    else:
        args.out.write_text(content)


if __name__ == "__main__":
    main()
