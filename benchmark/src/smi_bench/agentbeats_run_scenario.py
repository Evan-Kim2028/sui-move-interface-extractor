from __future__ import annotations

import argparse
from pathlib import Path

from smi_bench.env import load_dotenv


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Run an AgentBeats scenario from the local repo")
    p.add_argument("scenario_root", type=Path, help="Path to scenario directory (containing scenario.toml)")
    p.add_argument("--launch-mode", choices=["tmux", "separate", "current"], default="current")
    p.add_argument("--backend", type=str, default=None, help="Backend URL (optional; starts battle if set)")
    p.add_argument("--frontend", type=str, default=None, help="Frontend URL (optional; starts battle if set)")
    p.add_argument(
        "--status",
        action="store_true",
        help="Print whether the scenario's agent ports are listening and exit",
    )
    p.add_argument(
        "--kill",
        action="store_true",
        help="Kill the scenario manager process for this scenario (best-effort).",
    )
    p.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Dotenv file to load for agent subprocesses (process env still wins).",
    )
    args = p.parse_args(argv)

    scenario_root = args.scenario_root.resolve()
    if not (scenario_root / "scenario.toml").exists():
        raise SystemExit(f"scenario.toml not found: {scenario_root / 'scenario.toml'}")

    pid_file = scenario_root / ".scenario_pids.json"

    if args.status:
        import socket

        def is_listening(host: str, port: int) -> bool:
            try:
                with socket.create_connection((host, port), timeout=0.5):
                    return True
            except Exception:
                return False

        # Default ports for scenario_smi
        green_ok = is_listening("127.0.0.1", 9999)
        purple_ok = is_listening("127.0.0.1", 9998)
        print(f"green_9999_listening={green_ok}")
        print(f"purple_9998_listening={purple_ok}")
        return

    if args.kill:
        if not pid_file.exists():
            print(f"pid_file_missing={pid_file}")
            return

        import json
        import os
        import signal

        try:
            data = json.loads(pid_file.read_text(encoding="utf-8"))
        except Exception:
            print(f"pid_file_unreadable={pid_file}")
            return

        # ScenarioManager does not expose child process handles; kill is best-effort.
        # We at least stop the scenario manager process (which in turn should stop children).
        pids = [data.get("scenario_manager_pid")]
        for pid in [p for p in pids if isinstance(p, int) and p > 0]:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        return

    # The upstream `agentbeats load_scenario` CLI resolves scenario_root relative to its
    # own installed location (site-packages). To run local scenarios, we must bypass
    # that and use ScenarioManager directly.
    from agentbeats.utils.deploy.scenario_manager import ScenarioManager

    # Ensure common provider keys (e.g. OPENROUTER_API_KEY) are available to subprocesses.
    # ScenarioManager launches agents via `subprocess.Popen(..., shell=True)`.
    # Ensure we load `.env` from the benchmark project dir so the launched agents
    # inherit keys (OPENROUTER_API_KEY, etc.).
    env = load_dotenv(args.env_file)
    for k, v in env.items():
        if k.endswith("_API_KEY") or k.startswith("SMI_"):
            import os

            os.environ.setdefault(k, v)

    manager = ScenarioManager(scenario_root=scenario_root, project_dir=Path.cwd())

    # Patch the loaded agent commands to launch the repo's A2A servers instead of
    # `agentbeats run_agent ...`.
    for agent in manager.agents:
        if agent.name == "smi-bench-green":
            agent.get_command = lambda a=agent: (
                "cd {cwd} && uv run smi-a2a-green --host {host} --port {port} --card-url http://{host}:{port}/".format(
                    cwd=Path.cwd(),
                    host=a.agent_host,
                    port=a.agent_port,
                )
            )
        elif agent.name == "smi-bench-purple":
            agent.get_command = lambda a=agent: (
                "cd {cwd} && uv run smi-a2a-purple --host {host} --port {port} --card-url http://{host}:{port}/".format(
                    cwd=Path.cwd(),
                    host=a.agent_host,
                    port=a.agent_port,
                )
            )

    manager.load_scenario(mode=args.launch_mode)

    # Best-effort: persist PID for later --kill.
    try:
        import json
        import os

        pids = {
            "scenario_manager_pid": os.getpid(),
        }
        pid_file.write_text(json.dumps(pids, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass

    if args.backend and args.frontend:
        manager.start_battle(backend_url=args.backend, frontend_url=args.frontend)


if __name__ == "__main__":
    main()
