from __future__ import annotations

import argparse
import json
from typing import Any

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentProvider, AgentSkill, Part, TaskState, TextPart
from a2a.utils import new_agent_text_message, new_task


def _card(*, url: str) -> AgentCard:
    skill = AgentSkill(
        id="baseline",
        name="Baseline",
        description="Baseline purple agent (stub) for AgentBeats wiring tests.",
        tags=["baseline"],
        examples=["ping"],
        input_modes=["text/plain", "application/json"],
        output_modes=["text/plain", "application/json"],
    )
    return AgentCard(
        name="smi-bench-purple",
        description="Baseline purple agent for AgentBeats (stub).",
        url=url,
        version="0.1.0",
        provider=AgentProvider(organization="sui-move-interface-extractor", url=url),
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False, state_transition_history=False),
        skills=[skill],
    )


class PurpleExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            if context.message is None:
                raise ValueError("RequestContext.message is missing")
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        await updater.update_status(TaskState.working, new_agent_text_message("ready", task.context_id, task.id))

        raw = context.get_user_input()
        payload: Any
        try:
            payload = json.loads(raw) if raw else raw
        except Exception:
            payload = raw

        reply = {"ok": True, "echo": payload}
        await updater.add_artifact([Part(root=TextPart(text=json.dumps(reply, sort_keys=True)))], name="response")
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise RuntimeError("cancel not implemented")


def build_app(*, public_url: str) -> Any:
    handler = DefaultRequestHandler(agent_executor=PurpleExecutor(), task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=_card(url=public_url), http_handler=handler).build()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="A2A baseline purple agent (stub)")
    p.add_argument("--host", type=str, default="0.0.0.0")
    p.add_argument("--port", type=int, default=9998)
    p.add_argument("--card-url", type=str, default=None)
    args = p.parse_args(argv)

    url = args.card_url or f"http://{args.host}:{args.port}/"
    app = build_app(public_url=url)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
