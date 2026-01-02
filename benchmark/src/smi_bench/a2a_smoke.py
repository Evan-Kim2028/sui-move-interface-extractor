from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import httpx


def _default_request(
    *,
    corpus_root: str,
    package_ids_file: str,
    samples: int,
    timeout_s: float,
    rpc_url: str,
    simulation_mode: str,
    sender: str | None,
    max_plan_attempts: int,
    max_planning_calls: int | None,
    continue_on_error: bool,
    resume: bool,
) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "corpus_root": corpus_root,
        "package_ids_file": package_ids_file,
        "samples": samples,
        "rpc_url": rpc_url,
        "simulation_mode": simulation_mode,
        "per_package_timeout_seconds": timeout_s,
        "max_plan_attempts": max(1, int(max_plan_attempts)),
        "continue_on_error": bool(continue_on_error),
        "resume": bool(resume),
    }
    if max_planning_calls is not None:
        cfg["max_planning_calls"] = max(1, int(max_planning_calls))
    if sender:
        cfg["sender"] = sender
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": f"smi_a2a_smoke_{int(time.time())}",
                "role": "user",
                "parts": [{"text": json.dumps({"config": cfg})}],
            }
        },
    }


def _extract_bundle(resp: dict[str, Any]) -> dict[str, Any]:
    result = resp.get("result")
    if not isinstance(result, dict):
        raise ValueError("missing result")
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("missing artifacts")
    for a in artifacts:
        if isinstance(a, dict) and a.get("name") == "evaluation_bundle":
            parts = a.get("parts")
            if isinstance(parts, list) and parts:
                p0 = parts[0]
                if isinstance(p0, dict) and isinstance(p0.get("text"), str):
                    return json.loads(p0["text"])
    raise ValueError("evaluation_bundle not found")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Run local A2A smoke test")
    p.add_argument("--scenario", type=str, default="scenario_smi")
    p.add_argument("--green-url", type=str, default="http://127.0.0.1:9999/")
    p.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Dotenv file to load for scenario-launched agents (process env still wins).",
    )
    p.add_argument("--corpus-root", type=str, required=True)
    p.add_argument("--package-ids-file", type=str, default=None)
    p.add_argument("--samples", type=int, default=1)
    p.add_argument("--rpc-url", type=str, default="https://fullnode.mainnet.sui.io:443")
    p.add_argument("--simulation-mode", type=str, default="dry-run")
    p.add_argument(
        "--sender",
        type=str,
        default=None,
        help="Optional sender address (public). Only needed for some simulation modes.",
    )
    p.add_argument("--per-package-timeout-seconds", type=float, default=90)
    p.add_argument(
        "--max-plan-attempts",
        type=int,
        default=2,
        help="Max PTB replanning attempts per package.",
    )
    p.add_argument(
        "--max-planning-calls",
        type=int,
        default=None,
        help="Maximum progressive-exposure planning calls per package (omit to use default).",
    )
    p.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue even if a package fails.",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Resume an existing output bundle (if supported by server).",
    )
    p.add_argument("--out-response", type=Path, default=Path("results/a2a_smoke_response.json"))
    args = p.parse_args(argv)

    started_pid: int | None = None
    try:
        if args.scenario:
            import subprocess

            args.out_response.parent.mkdir(parents=True, exist_ok=True)
            log_path = args.out_response.parent / "a2a_smoke_scenario.log"
            scenario_root = Path.cwd() / args.scenario
            agentbeats_run = [
                "uv",
                "run",
                "smi-agentbeats-scenario",
                str(scenario_root),
                "--launch-mode",
                "current",
                "--env-file",
                str(args.env_file),
            ]
            proc = subprocess.Popen(
                agentbeats_run,
                cwd=str(Path.cwd()),
                stdout=log_path.open("w"),
                stderr=subprocess.STDOUT,
            )
            started_pid = proc.pid

            # Wait briefly for the green server to come up.
            client = httpx.Client(timeout=2.0)
            deadline = time.time() + 10
            while True:
                try:
                    r = client.get(args.green_url.rstrip("/") + "/.well-known/agent-card.json")
                    if r.status_code == 200:
                        break
                except Exception:
                    pass
                if time.time() > deadline:
                    raise RuntimeError("green agent did not become healthy in time")
                time.sleep(0.5)

        req = _default_request(
            corpus_root=args.corpus_root,
            package_ids_file=args.package_ids_file,
            samples=args.samples,
            timeout_s=args.per_package_timeout_seconds,
            rpc_url=args.rpc_url,
            simulation_mode=args.simulation_mode,
            sender=args.sender,
            max_plan_attempts=args.max_plan_attempts,
            max_planning_calls=args.max_planning_calls,
            continue_on_error=args.continue_on_error,
            resume=args.resume,
        )
        with httpx.Client(timeout=None) as client:
            r = client.post(args.green_url, json=req)
            r.raise_for_status()
            resp = r.json()

        args.out_response.parent.mkdir(parents=True, exist_ok=True)
        args.out_response.write_text(json.dumps(resp, indent=2, sort_keys=True), encoding="utf-8")

        bundle = _extract_bundle(resp)
        metrics = bundle.get("metrics")
        errors = bundle.get("errors")
        artifacts = bundle.get("artifacts")

        print(f"run_id={bundle.get('run_id')} exit_code={bundle.get('exit_code')}")
        print(f"metrics={json.dumps(metrics, sort_keys=True)}")
        print(f"errors_len={len(errors) if isinstance(errors, list) else 'unknown'}")
        if isinstance(artifacts, dict):
            print(f"results_path={artifacts.get('results_path')}")
            print(f"events_path={artifacts.get('events_path')}")
        print(f"response_path={args.out_response}")
    finally:
        if started_pid is not None:
            try:
                import os
                import signal

                os.kill(started_pid, signal.SIGTERM)
            except Exception:
                pass


if __name__ == "__main__":
    main()
