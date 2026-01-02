from __future__ import annotations

import json

from smi_bench.a2a_smoke import _default_request


def _extract_cfg(req: dict) -> dict:
    parts = req["params"]["message"]["parts"]
    payload = json.loads(parts[0]["text"])
    return payload["config"]


def test_a2a_smoke_default_request_serializes_all_parameters() -> None:
    req = _default_request(
        corpus_root="/corpus",
        package_ids_file="/manifest.txt",
        samples=20,
        timeout_s=123.0,
        rpc_url="https://rpc",
        simulation_mode="dry-run",
        sender="0xabc",
        max_plan_attempts=5,
        max_planning_calls=50,
        continue_on_error=True,
        resume=True,
    )
    cfg = _extract_cfg(req)
    assert cfg["corpus_root"] == "/corpus"
    assert cfg["package_ids_file"] == "/manifest.txt"
    assert cfg["samples"] == 20
    assert cfg["per_package_timeout_seconds"] == 123.0
    assert cfg["rpc_url"] == "https://rpc"
    assert cfg["simulation_mode"] == "dry-run"
    assert cfg["sender"] == "0xabc"
    assert cfg["max_plan_attempts"] == 5
    assert cfg["max_planning_calls"] == 50
    assert cfg["continue_on_error"] is True
    assert cfg["resume"] is True


def test_a2a_smoke_default_request_omits_max_planning_calls_when_none() -> None:
    req = _default_request(
        corpus_root="/corpus",
        package_ids_file="/manifest.txt",
        samples=1,
        timeout_s=1.0,
        rpc_url="https://rpc",
        simulation_mode="dry-run",
        sender=None,
        max_plan_attempts=1,
        max_planning_calls=None,
        continue_on_error=False,
        resume=False,
    )
    cfg = _extract_cfg(req)
    assert "max_planning_calls" not in cfg
    assert "sender" not in cfg
    assert cfg["max_plan_attempts"] == 1
    assert cfg["continue_on_error"] is False
    assert cfg["resume"] is False


def test_a2a_smoke_default_request_clamps_attempt_budgets_to_at_least_one() -> None:
    req = _default_request(
        corpus_root="/corpus",
        package_ids_file="/manifest.txt",
        samples=1,
        timeout_s=1.0,
        rpc_url="https://rpc",
        simulation_mode="dry-run",
        sender=None,
        max_plan_attempts=0,
        max_planning_calls=0,
        continue_on_error=True,
        resume=False,
    )
    cfg = _extract_cfg(req)
    assert cfg["max_plan_attempts"] == 1
    assert cfg["max_planning_calls"] == 1
