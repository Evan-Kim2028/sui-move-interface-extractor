from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentProvider, AgentSkill, Part, TaskState, TextPart
from a2a.utils import new_agent_text_message, new_task


@dataclass(frozen=True)
class EvalConfig:
    corpus_root: str
    package_ids_file: str
    samples: int
    rpc_url: str
    simulation_mode: str
    per_package_timeout_seconds: float
    max_plan_attempts: int
    continue_on_error: bool
    resume: bool
    run_id: str | None


def _safe_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _safe_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _load_cfg(raw: Any) -> EvalConfig:
    if not isinstance(raw, dict):
        raise ValueError("config must be a JSON object")

    corpus_root = str(raw.get("corpus_root") or "")
    package_ids_file = str(raw.get("package_ids_file") or raw.get("manifest") or "")

    if not corpus_root:
        raise ValueError("missing config.corpus_root")
    if not package_ids_file:
        raise ValueError("missing config.package_ids_file")

    return EvalConfig(
        corpus_root=corpus_root,
        package_ids_file=package_ids_file,
        samples=_safe_int(raw.get("samples"), 0),
        rpc_url=str(raw.get("rpc_url") or "https://fullnode.mainnet.sui.io:443"),
        simulation_mode=str(raw.get("simulation_mode") or "dry-run"),
        per_package_timeout_seconds=_safe_float(raw.get("per_package_timeout_seconds"), 300.0),
        max_plan_attempts=_safe_int(raw.get("max_plan_attempts"), 2),
        continue_on_error=bool(raw.get("continue_on_error", True)),
        resume=bool(raw.get("resume", True)),
        run_id=str(raw.get("run_id")) if raw.get("run_id") else None,
    )


def _extract_payload(context: RequestContext) -> dict[str, Any]:
    raw = context.get_user_input()
    if raw:
        try:
            v = json.loads(raw)
            if isinstance(v, dict):
                return v
        except Exception:
            pass

    params = getattr(context, "_params", None)
    if params is not None:
        meta = getattr(params, "metadata", None)
        if isinstance(meta, dict):
            return meta

    return {}


def _summarize_phase2_results(out_json: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        data = json.loads(out_json.read_text(encoding="utf-8"))
    except Exception:
        return {}, []

    # Return as much as we can even if some fields are missing.
    if not isinstance(data, dict):
        return {}, []

    aggregate = data.get("aggregate")
    packages = data.get("packages")

    metrics: dict[str, Any] = {}
    if isinstance(aggregate, dict):
        metrics["avg_hit_rate"] = aggregate.get("avg_hit_rate")
        metrics["errors"] = aggregate.get("errors")

    error_rows: list[dict[str, Any]] = []
    if isinstance(packages, list):
        for row in packages:
            if not isinstance(row, dict):
                continue
            err = row.get("error")
            timed_out = row.get("timed_out")
            if err or timed_out:
                score = row.get("score") if isinstance(row.get("score"), dict) else {}
                error_rows.append(
                    {
                        "package_id": row.get("package_id"),
                        "error": err,
                        "timed_out": timed_out,
                        "elapsed_seconds": row.get("elapsed_seconds"),
                        "plan_attempts": row.get("plan_attempts"),
                        "sim_attempts": row.get("sim_attempts"),
                        "score": {
                            "targets": score.get("targets"),
                            "created_hits": score.get("created_hits"),
                            "created_distinct": score.get("created_distinct"),
                        },
                    }
                )

    if isinstance(packages, list):
        metrics["packages_total"] = len(packages)
        metrics["packages_with_error"] = len(error_rows)
        metrics["packages_timed_out"] = sum(1 for e in error_rows if e.get("timed_out"))

    return metrics, error_rows


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _card(*, url: str) -> AgentCard:
    skill = AgentSkill(
        id="run_phase2",
        name="Run Phase II",
        description="Run Phase II (PTB inhabitation) over a manifest and return results as artifacts.",
        tags=["benchmark", "sui", "move", "phase2"],
        examples=["Run Phase II on standard manifest"],
        input_modes=["application/json"],
        output_modes=["application/json"],
    )

    return AgentCard(
        name="smi-bench-green",
        description="Green agent wrapper for the Sui Move Interface Extractor benchmark (Phase II).",
        url=url,
        version="0.1.0",
        provider=AgentProvider(organization="sui-move-interface-extractor", url=url),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False, state_transition_history=False),
        skills=[skill],
    )


async def _tail_events(updater: TaskUpdater, events_path: Path, stop: asyncio.Event) -> None:
    last_pos = 0
    while not stop.is_set():
        try:
            if not events_path.exists():
                await asyncio.sleep(0.25)
                continue
            with events_path.open("r", encoding="utf-8") as f:
                f.seek(last_pos)
                lines = f.readlines()
                last_pos = f.tell()
            for line in lines:
                s = line.strip()
                if not s:
                    continue
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(s, updater.context_id, updater.task_id),
                )
        except Exception:
            await asyncio.sleep(0.5)
        await asyncio.sleep(0.25)


class SmiBenchGreenExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            if context.message is None:
                raise ValueError("RequestContext.message is missing")
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        started_at = time.time()
        await updater.update_status(
            TaskState.working,
            new_agent_text_message("starting", task.context_id, task.id),
        )

        try:
            payload = _extract_payload(context)
            cfg = _load_cfg(payload.get("config") if isinstance(payload, dict) else {})

            out_dir = Path(payload.get("out_dir") or "results/a2a")
            out_dir.mkdir(parents=True, exist_ok=True)
            run_id = cfg.run_id or f"a2a_phase2_{int(time.time())}"

            out_json = out_dir / f"{run_id}.json"
            log_dir = Path("logs")
            events_path = log_dir / run_id / "events.jsonl"
            run_metadata_path = log_dir / run_id / "run_metadata.json"

            args = [
                "uv",
                "run",
                "smi-inhabit",
                "--corpus-root",
                cfg.corpus_root,
                "--package-ids-file",
                cfg.package_ids_file,
                "--agent",
                "real-openai-compatible",
                "--rpc-url",
                cfg.rpc_url,
                "--simulation-mode",
                cfg.simulation_mode,
                "--per-package-timeout-seconds",
                str(cfg.per_package_timeout_seconds),
                "--max-plan-attempts",
                str(cfg.max_plan_attempts),
                "--out",
                str(out_json),
                "--run-id",
                run_id,
            ]
            if cfg.samples and cfg.samples > 0:
                args.extend(["--samples", str(cfg.samples)])
            if cfg.continue_on_error:
                args.append("--continue-on-error")
            if cfg.resume:
                args.append("--resume")

            stop = asyncio.Event()
            tail_task = asyncio.create_task(_tail_events(updater, events_path, stop))

            proc = await asyncio.create_subprocess_exec(
                *args,
                cwd=str(Path(__file__).resolve().parents[2]),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout is not None
            async for b in proc.stdout:
                line = b.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(line, updater.context_id, updater.task_id),
                    )
            rc = await proc.wait()

            stop.set()
            try:
                await tail_task
            except Exception:
                pass

            finished_at = time.time()

            metrics: dict[str, Any] = {}
            errors_list: list[dict[str, Any]] = []
            if out_json.exists():
                metrics, errors_list = _summarize_phase2_results(out_json)

            # Defensive: if summary unexpectedly returned empty, re-parse from disk.
            if out_json.exists() and not metrics:
                parsed = _read_json(out_json)
                if parsed is not None:
                    metrics, errors_list = _summarize_phase2_results(out_json)

            if out_json.exists() and not metrics:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        "warning: phase2 results found but summary returned empty metrics",
                        updater.context_id,
                        updater.task_id,
                    ),
                )

            # If the Phase II output is missing aggregate/package details for any reason,
            # fall back to deriving errors/metrics from the JSONL logs.
            if not metrics.get("errors") and run_metadata_path.exists():
                md = _read_json(run_metadata_path) or {}
                metrics.setdefault("run_metadata", md)

            bundle = {
                "schema_version": 1,
                "spec_url": "smi-bench:evaluation_bundle:v1",
                "benchmark": "phase2_inhabit",
                "run_id": run_id,
                "exit_code": rc,
                "timings": {
                    "started_at_unix_seconds": int(started_at),
                    "finished_at_unix_seconds": int(finished_at),
                    "elapsed_seconds": finished_at - started_at,
                },
                "config": {
                    "corpus_root": cfg.corpus_root,
                    "package_ids_file": cfg.package_ids_file,
                    "samples": cfg.samples,
                    "rpc_url": cfg.rpc_url,
                    "simulation_mode": cfg.simulation_mode,
                    "per_package_timeout_seconds": cfg.per_package_timeout_seconds,
                    "max_plan_attempts": cfg.max_plan_attempts,
                    "continue_on_error": cfg.continue_on_error,
                    "resume": cfg.resume,
                },
                "metrics": metrics,
                "errors": errors_list,
                "artifacts": {
                    "results_path": str(out_json),
                    "run_metadata_path": str(run_metadata_path),
                    "events_path": str(events_path),
                },
            }

            await updater.add_artifact(
                [Part(root=TextPart(text=json.dumps(bundle, sort_keys=True)))],
                name="evaluation_bundle",
            )
            if out_json.exists():
                await updater.add_artifact(
                    [Part(root=TextPart(text=out_json.read_text(encoding="utf-8")))],
                    name="phase2_results.json",
                )
            if run_metadata_path.exists():
                await updater.add_artifact(
                    [Part(root=TextPart(text=run_metadata_path.read_text(encoding="utf-8")))],
                    name="run_metadata.json",
                )

            if rc == 0:
                await updater.complete()
            else:
                await updater.failed(
                    new_agent_text_message(
                        f"phase2 failed (exit={rc})",
                        updater.context_id,
                        updater.task_id,
                    )
                )

        except Exception as e:
            await updater.failed(new_agent_text_message(f"error: {e}", task.context_id, task.id))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise RuntimeError("cancel not implemented")


def build_app(*, public_url: str) -> Any:
    card = _card(url=public_url)
    handler = DefaultRequestHandler(
        agent_executor=SmiBenchGreenExecutor(),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(agent_card=card, http_handler=handler).build()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="A2A green agent server for smi-bench Phase II")
    p.add_argument("--host", type=str, default="0.0.0.0")
    p.add_argument("--port", type=int, default=9999)
    p.add_argument("--card-url", type=str, default=None)
    args = p.parse_args(argv)

    url = args.card_url or f"http://{args.host}:{args.port}/"
    app = build_app(public_url=url)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
