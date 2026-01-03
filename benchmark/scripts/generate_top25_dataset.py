#!/usr/bin/env python3
"""Generate top-25 Type Inhabitation benchmark dataset.

This script scores packages from the corpus report and selects the top 25 most
interesting packages for Type Inhabitation benchmark evaluation, applying diversity
constraints to avoid clustering.

Usage:
    cd benchmark
    python scripts/generate_top25_dataset.py

Outputs:
    - manifests/datasets/type_inhabitation_top25.txt (dataset file)
    - results/dataset_top25_scoring.json (detailed scores)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, order=True)
class PackageScore:
    package_id: str
    key_structs: int
    entry_functions: int
    modules: int
    functions_total: int
    composite_score: float = field(compare=False)
    rank: int = field(compare=False)
    entry_key_ratio: float = field(compare=False)
    diversity_score: float = field(compare=False)


def normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to [0, 1] range."""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def load_corpus_report(path: Path) -> dict[str, dict[str, Any]]:
    """Load corpus report JSONL into package_id -> data mapping."""
    packages: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if not line:
            continue
        try:
            data = json.loads(line)
            pkg_id = data.get("package_id")
            if isinstance(pkg_id, str) and pkg_id:
                packages[pkg_id] = data
        except json.JSONDecodeError:
            continue
    return packages


def load_phase2_benchmark(path: Path) -> set[str]:
    """Load Phase II benchmark package IDs into a set."""
    ids = set()
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(line)
    return ids


def compute_scores(
    corpus_packages: dict[str, dict[str, Any]],
    phase2_ids: set[str],
) -> list[PackageScore]:
    """Compute composite scores for all Phase II packages."""
    scored: list[PackageScore] = []

    # First pass: collect metrics
    metrics: list[dict[str, Any]] = []
    for pkg_id in phase2_ids:
        if pkg_id not in corpus_packages:
            continue
        data = corpus_packages[pkg_id]
        local = data.get("local", {})
        metrics.append(
            {
                "package_id": pkg_id,
                "key_structs": local.get("key_structs", 0),
                "entry_functions": local.get("entry_functions", 0),
                "modules": local.get("modules", 0),
                "functions_total": local.get("functions_total", 0),
            }
        )

    if not metrics:
        print("[yellow]No Phase II packages found in corpus report[/yellow]")
        return []

    # Compute min/max for normalization
    key_structs_vals = [m["key_structs"] for m in metrics]
    entry_funcs_vals = [m["entry_functions"] for m in metrics]

    ks_min, ks_max = min(key_structs_vals), max(key_structs_vals)
    ef_min, ef_max = min(entry_funcs_vals), max(entry_funcs_vals)

    # Compute entry/key ratios for normalization
    ratios = []
    for m in metrics:
        ks = m["key_structs"]
        ef = m["entry_functions"]
        if ks > 0:
            ratios.append(ef / ks)
        else:
            ratios.append(0)

    ratio_min, ratio_max = min(ratios) if ratios else 0, max(ratios) if ratios else 1

    # Compute diversity scores for normalization
    diversities = []
    for m in metrics:
        mods = m["modules"]
        funcs = m["functions_total"]
        if mods > 0:
            diversities.append(funcs / mods)
        else:
            diversities.append(0)

    div_min, div_max = min(diversities) if diversities else 0, max(diversities) if diversities else 1

    # Second pass: compute composite scores
    for m in metrics:
        pkg_id = m["package_id"]
        ks = m["key_structs"]
        ef = m["entry_functions"]
        mods = m["modules"]
        funcs = m["functions_total"]

        # Entry/key ratio (planning efficiency)
        ratio = ef / ks if ks > 0 else 0

        # Function/struct diversity (signature complexity)
        diversity = funcs / mods if mods > 0 else 0

        # Normalize each component to [0, 1]
        ks_norm = normalize(ks, ks_min, ks_max)
        ef_norm = normalize(ef, ef_min, ef_max)
        ratio_norm = normalize(ratio, ratio_min, ratio_max)
        div_norm = normalize(diversity, div_min, div_max)

        # Composite score (weighted)
        # - Key structs: 40% (more targets)
        # - Entry functions: 30% (more planning paths)
        # - Entry/key ratio: 15% (planning efficiency)
        # - Function/struct diversity: 15% (signature complexity)
        composite = 0.40 * ks_norm + 0.30 * ef_norm + 0.15 * ratio_norm + 0.15 * div_norm

        scored.append(
            PackageScore(
                package_id=pkg_id,
                key_structs=ks,
                entry_functions=ef,
                modules=mods,
                functions_total=funcs,
                composite_score=composite,
                rank=0,  # Will be set after sorting
                entry_key_ratio=ratio,
                diversity_score=diversity,
            )
        )

    # Sort by composite score
    scored.sort(reverse=True, key=lambda ps: ps.composite_score)

    # Assign ranks
    for i, ps in enumerate(scored, start=1):
        object.__setattr__(ps, "rank", i)

    return scored


def apply_diversity_constraints(
    scored: list[PackageScore],
    n: int = 25,
) -> list[PackageScore]:
    """Apply diversity constraints to avoid clustering.

    Constraints:
    - Max 5 packages with same key_structs count
    - Ensure small packages included (<30% from top 50% by key_structs)
    """
    if not scored:
        return []

    selected: list[PackageScore] = []
    ks_counts: dict[int, int] = {}

    # Determine threshold for "large" packages (top 50% by key_structs)
    ks_values = [ps.key_structs for ps in scored]
    ks_sorted = sorted(ks_values)
    threshold_idx = len(ks_sorted) // 2
    large_threshold = ks_sorted[threshold_idx] if threshold_idx < len(ks_sorted) else 0

    large_selected = 0
    max_large_ratio = 0.30  # Max 30% from large packages

    for ps in scored:
        if len(selected) >= n:
            break

        # Check key_structs constraint (max 5 per value)
        ks = ps.key_structs
        ks_count = ks_counts.get(ks, 0)
        if ks_count >= 5:
            continue

        # Check large package constraint
        if ks >= large_threshold:
            large_ratio = large_selected / len(selected) if selected else 0
            if large_ratio >= max_large_ratio:
                continue

        selected.append(ps)
        ks_counts[ks] = ks_counts.get(ks, 0) + 1

        if ks >= large_threshold:
            large_selected += 1

    return selected


def write_dataset(
    selected: list[PackageScore],
    output_path: Path,
    scores_path: Path,
) -> None:
    """Write dataset file and detailed scores JSON."""
    timestamp = datetime.now().isoformat(timespec="seconds")

    # Write dataset file
    header = f"# Top-25 Type Inhabitation Benchmark Dataset\n# Generated: {timestamp}\n"
    content = header + "\n".join(ps.package_id for ps in selected) + "\n"
    output_path.write_text(content, encoding="utf-8")
    print(f"[green]Wrote dataset:[/green] {output_path}")
    print(f"[green]  Selected {len(selected)} packages[/green]")

    # Write detailed scores JSON
    scores_data = {
        "generated_at": timestamp,
        "total_packages_scored": len(selected) + (0 if not selected else 0),
        "selected_count": len(selected),
        "selection_criteria": {
            "key_structs_weight": 0.40,
            "entry_functions_weight": 0.30,
            "entry_key_ratio_weight": 0.15,
            "diversity_score_weight": 0.15,
        },
        "diversity_constraints": {
            "max_per_key_structs": 5,
            "max_large_package_ratio": 0.30,
        },
        "packages": [
            {
                "rank": ps.rank,
                "package_id": ps.package_id,
                "key_structs": ps.key_structs,
                "entry_functions": ps.entry_functions,
                "modules": ps.modules,
                "functions_total": ps.functions_total,
                "entry_key_ratio": round(ps.entry_key_ratio, 3),
                "diversity_score": round(ps.diversity_score, 3),
                "composite_score": round(ps.composite_score, 6),
            }
            for ps in selected
        ],
    }
    scores_path.write_text(json.dumps(scores_data, indent=2) + "\n", encoding="utf-8")
    print(f"[green]Wrote scores:[/green] {scores_path}")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate top-25 Type Inhabitation benchmark dataset from corpus report")
    p.add_argument(
        "--corpus-report",
        type=Path,
        default=Path("../results/corpus_mainnet_most_used_2026-01-01/corpus_report.jsonl"),
        help="Path to corpus_report.jsonl file",
    )
    p.add_argument(
        "--phase2-benchmark",
        type=Path,
        default=Path("manifests/standard_phase2_benchmark.txt"),
        help="Path to Phase II benchmark manifest",
    )
    p.add_argument(
        "--output-dataset",
        type=Path,
        default=Path("manifests/datasets/type_inhabitation_top25.txt"),
        help="Output path for dataset file",
    )
    p.add_argument(
        "--output-scores",
        type=Path,
        default=Path("../results/dataset_top25_scoring.json"),
        help="Output path for detailed scores JSON",
    )
    p.add_argument(
        "--count",
        type=int,
        default=25,
        help="Number of packages to select (default: 25)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    print("[blue]Loading corpus report...[/blue]")
    corpus_packages = load_corpus_report(args.corpus_report)
    print(f"[blue]  Loaded {len(corpus_packages)} packages[/blue]")

    print("[blue]Loading Phase II benchmark...[/blue]")
    phase2_ids = load_phase2_benchmark(args.phase2_benchmark)
    print(f"[blue]  Found {len(phase2_ids)} Phase II packages[/blue]")

    print("[blue]Computing composite scores...[/blue]")
    scored = compute_scores(corpus_packages, phase2_ids)
    if not scored:
        print("[red]Error: No packages to score[/red]")
        return
    print(f"[blue]  Scored {len(scored)} packages[/blue]")

    print("[blue]Applying diversity constraints...[/blue]")
    selected = apply_diversity_constraints(scored, n=args.count)
    print(f"[blue]  Selected {len(selected)} packages[/blue]")

    # Create output directories if needed
    args.output_dataset.parent.mkdir(parents=True, exist_ok=True)
    args.output_scores.parent.mkdir(parents=True, exist_ok=True)

    print("[blue]Writing outputs...[/blue]")
    write_dataset(selected, args.output_dataset, args.output_scores)

    # Show top 5 selected
    print("\n[green]Top 5 selected packages:[/green]")
    for ps in selected[:5]:
        print(f"  {ps.rank}. {ps.package_id}")
        print(f"     Key structs: {ps.key_structs}, Entry funcs: {ps.entry_functions}")
        print(f"     Composite score: {ps.composite_score:.6f}")


if __name__ == "__main__":
    main()
