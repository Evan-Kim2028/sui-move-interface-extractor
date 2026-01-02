from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Scan then run Phase II only on signal packages (targets >= N / hits >= N)")
    p.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Dotenv file for OpenRouter/API keys and defaults (process env still wins).",
    )
    p.add_argument("--corpus-root", type=Path, required=True)
    p.add_argument(
        "--base-manifest",
        type=Path,
        default=Path("manifests/standard_phase2_no_framework.txt"),
        help="Base manifest to scan/filter",
    )
    # Default to signal-only packages: targets>=2.
    p.add_argument("--min-targets", type=int, default=2)
    p.add_argument("--min-hits", type=int, default=1, help="Keep packages with created_hits >= N")
    p.add_argument("--scan-samples", type=int, default=500)
    p.add_argument("--run-samples", type=int, default=50)
    p.add_argument("--rpc-url", type=str, default="https://fullnode.mainnet.sui.io:443")
    p.add_argument("--per-package-timeout-seconds", type=float, default=90)
    p.add_argument("--max-plan-attempts", type=int, default=2)
    p.add_argument(
        "--signal-out",
        type=Path,
        default=Path("results/signal_ids_hit_ge_1.txt"),
        help="Persist the curated signal ids list to this path.",
    )
    p.add_argument("--resume", action="store_true")
    p.add_argument("--out-dir", type=Path, default=Path("results"))
    args = p.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    scan_out = args.out_dir / f"phase2_targets_scan_{stamp}.json"
    manifest_out = args.out_dir / f"manifest_targets_ge{args.min_targets}_{stamp}.txt"
    run_out = args.out_dir / f"phase2_targeted_run_{stamp}.json"

    subprocess.run(
        [
            "uv",
            "run",
            "smi-inhabit",
            "--corpus-root",
            str(args.corpus_root),
            "--package-ids-file",
            str(args.base_manifest),
            "--samples",
            str(args.scan_samples),
            "--agent",
            "baseline-search",
            "--simulation-mode",
            "build-only",
            "--continue-on-error",
            "--out",
            str(scan_out),
        ],
        check=True,
    )

    subprocess.run(
        [
            "uv",
            "run",
            "smi-phase2-filter-manifest",
            str(scan_out),
            "--min-targets",
            str(args.min_targets),
            "--out-manifest",
            str(manifest_out),
        ],
        check=True,
    )

    # Quick preflight run to find packages that actually produce hits (signal).
    subprocess.run(
        [
            "uv",
            "run",
            "smi-inhabit",
            "--env-file",
            str(args.env_file),
            "--corpus-root",
            str(args.corpus_root),
            "--package-ids-file",
            str(manifest_out),
            "--samples",
            str(args.run_samples),
            "--agent",
            "real-openai-compatible",
            "--rpc-url",
            args.rpc_url,
            "--simulation-mode",
            "dry-run",
            "--continue-on-error",
            "--per-package-timeout-seconds",
            str(args.per_package_timeout_seconds),
            "--max-plan-attempts",
            str(args.max_plan_attempts),
            "--max-planning-calls",
            "25",
            "--no-log",
            "--out",
            str(run_out),
        ],
        check=True,
    )

    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/filter_packages_by_hit_rate.py",
            str(run_out),
            "--min-hits",
            str(args.min_hits),
            "--out",
            str(args.signal_out),
        ],
        check=True,
    )

    print(f"scan_out={scan_out}")
    print(f"manifest_out={manifest_out}")
    print(f"signal_out={args.signal_out}")
    print(f"run_out={run_out}")


if __name__ == "__main__":
    main()
