from __future__ import annotations

import httpx

from smi_bench.agents.real_agent import RealAgent, RealAgentConfig


def test_real_agent_openai_compatible_parses_json_array() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == httpx.URL("https://api.z.ai/v1/chat/completions")
        assert request.headers.get("authorization", "").startswith("Bearer ")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '["0x1::m::S","0x2::n::T"]',
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    cfg = RealAgentConfig(
        provider="openai_compatible",
        api_key="test",
        base_url="https://api.z.ai/v1",
        model="glm-4.7",
        temperature=0.0,
        max_tokens=16,
    )
    agent = RealAgent(cfg, client=client)
    out = agent.complete_type_list("return []")
    assert out == {"0x1::m::S", "0x2::n::T"}

