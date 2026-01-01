from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from rich.console import Console

from smi_bench.agents.mock_agent import MockAgent
from smi_bench.agents.real_agent import RealAgent, load_real_agent_config
from smi_bench.env import load_dotenv
from smi_bench.inhabit.score import InhabitationScore, extract_created_object_types, score_inhabitation
from smi_bench.runner import _extract_key_types_from_interface_json

console = Console()


def _default_rust_binary() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    exe = "sui_move_interface_extractor.exe" if os.name == "nt" else "sui_move_interface_extractor"
    local = repo_root / "target" / "release" / exe
    if local.exists():
        return local
    return Path("/usr/local/bin") / exe


def _run_rust_emit_bytecode_json(bytecode_package_dir: Path, rust_bin: Path) -> dict:
    out = subprocess.check_output(
        [
            str(rust_bin),
            "--bytecode-package-dir",
            str(bytecode_package_dir),
            "--emit-bytecode-json",
            "-",
        ],
        text=True,
    )
    return json.loads(out)


@dataclass
class InhabitRunResult:
    schema_version: int
    started_at_unix_seconds: int
    finished_at_unix_seconds: int
    agent: str
    package_id: str
    score: InhabitationScore


def run(
    *,
    bytecode_package_dir: Path,
    fixture_dev_inspect_json: Path | None,
    agent_name: str,
    rust_bin: Path,
    env_file: Path | None,
    out_path: Path | None,
) -> InhabitRunResult:
    if not rust_bin.exists():
        raise SystemExit(
            f"rust binary not found: {rust_bin} (run `cargo build --release --locked` at repo root)"
        )

    started = int(time.time())

    iface = _run_rust_emit_bytecode_json(bytecode_package_dir, rust_bin)
    package_id = iface.get("package_id", "<unknown>")
    truth_key_types = _extract_key_types_from_interface_json(iface)

    env_overrides = load_dotenv(env_file) if env_file is not None else {}

    if agent_name.startswith("mock-"):
        agent = MockAgent(behavior=agent_name.replace("mock-", ""), seed=0)
        predicted_key_types = agent.predict_key_types(truth_key_types=truth_key_types)
        ptb_spec = {"key_types": sorted(predicted_key_types)}
    elif agent_name == "real-openai-compatible":
        cfg = load_real_agent_config(env_overrides)
        agent = RealAgent(cfg)
        prompt = (
            "Given the following JSON array of target key types, propose a PTB plan to create as many of them as possible. "
            "Return JSON only.\n"
            + json.dumps({"package_id": package_id, "target_key_types": sorted(truth_key_types)}, indent=2)
        )
        ptb_spec = {"key_types": sorted(agent.complete_type_list(prompt))}
    else:
        raise SystemExit(f"unknown agent: {agent_name}")

    # Phase II scaffold: for now we only support fixture-based devInspect JSON.
    if fixture_dev_inspect_json is None:
        raise SystemExit(
            "Phase II scaffold: provide --fixture-dev-inspect-json for now (real PTB build+devInspect not implemented yet)."
        )

    dev_inspect = json.loads(fixture_dev_inspect_json.read_text())
    created_types = extract_created_object_types(dev_inspect)
    score = score_inhabitation(target_key_types=truth_key_types, created_object_types=created_types)

    finished = int(time.time())
    result = InhabitRunResult(
        schema_version=1,
        started_at_unix_seconds=started,
        finished_at_unix_seconds=finished,
        agent=agent_name,
        package_id=package_id,
        score=score,
    )

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(asdict(result), indent=2, sort_keys=True) + "\n")

    console.print(
        f"inhabitation score: targets={score.targets} created_hits={score.created_hits} missing={score.missing}"
    )
    _ = ptb_spec  # reserved for future: PTB plan serialization
    return result


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Phase II scaffold: PTB inhabitation benchmark")
    p.add_argument("--bytecode-package-dir", type=Path, required=True)
    p.add_argument("--fixture-dev-inspect-json", type=Path)
    p.add_argument(
        "--agent",
        type=str,
        default="mock-empty",
        choices=[
            "mock-perfect",
            "mock-empty",
            "mock-random",
            "mock-noisy",
            "real-openai-compatible",
        ],
    )
    p.add_argument("--rust-bin", type=Path, default=_default_rust_binary())
    p.add_argument("--out", type=Path)
    p.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to a dotenv file (default: .env in the current working directory).",
    )
    args = p.parse_args(argv)

    env_file = args.env_file if args.env_file.exists() else None
    if env_file is None:
        fallback = Path("benchmark/.env")
        if fallback.exists():
            env_file = fallback

    run(
        bytecode_package_dir=args.bytecode_package_dir,
        fixture_dev_inspect_json=args.fixture_dev_inspect_json,
        agent_name=args.agent,
        rust_bin=args.rust_bin,
        env_file=env_file,
        out_path=args.out,
    )


if __name__ == "__main__":
    main()
