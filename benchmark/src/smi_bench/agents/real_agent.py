from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx

from smi_bench.json_extract import extract_type_list


@dataclass(frozen=True)
class RealAgentConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    thinking: str | None


def _env_get(*keys: str) -> str | None:
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None


def load_real_agent_config(env_overrides: dict[str, str] | None = None) -> RealAgentConfig:
    env_overrides = env_overrides or {}

    def get(k: str, *fallbacks: str) -> str | None:
        # Precedence: real environment > .env file > fallbacks
        for kk in (k, *fallbacks):
            v = _env_get(kk)
            if v:
                return v
        for kk in (k, *fallbacks):
            v = env_overrides.get(kk)
            if v:
                return v
        return None

    provider = get("SMI_PROVIDER") or "openai_compatible"

    api_key = get("SMI_API_KEY", "OPENAI_API_KEY", "ZAI_API_KEY", "ZHIPUAI_API_KEY")
    if not api_key:
        raise ValueError("missing API key (set SMI_API_KEY or OPENAI_API_KEY)")

    base_url = (
        get("SMI_API_BASE_URL", "OPENAI_BASE_URL", "OPENAI_API_BASE")
        or "https://api.openai.com/v1"
    )
    model = get("SMI_MODEL", "OPENAI_MODEL") or "gpt-4o-mini"

    temperature_s = get("SMI_TEMPERATURE") or "0"
    max_tokens_s = get("SMI_MAX_TOKENS") or "800"
    thinking_s = get("SMI_THINKING")

    try:
        temperature = float(temperature_s)
    except Exception as e:
        raise ValueError(f"invalid SMI_TEMPERATURE={temperature_s}") from e
    try:
        max_tokens = int(max_tokens_s)
    except Exception as e:
        raise ValueError(f"invalid SMI_MAX_TOKENS={max_tokens_s}") from e

    return RealAgentConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        thinking=thinking_s,
    )


class RealAgent:
    """
    Real LLM agent.

    Currently supports OpenAI-compatible chat completions via:
      POST {base_url}/chat/completions
    """

    def __init__(self, cfg: RealAgentConfig, client: httpx.Client | None = None) -> None:
        self.cfg = cfg
        self._client = client or httpx.Client(timeout=60)

        if cfg.provider != "openai_compatible":
            raise ValueError(f"unsupported provider: {cfg.provider}")

    def smoke(self) -> set[str]:
        """
        Minimal connectivity + parsing check. Returns a set (likely empty).
        """
        prompt = (
            "Return a JSON array of strings. For smoke testing, return an empty array: []"
        )
        return self.complete_type_list(prompt)

    def complete_type_list(self, prompt: str) -> set[str]:
        url = f"{self.cfg.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.cfg.api_key}"}
        payload = {
            "model": self.cfg.model,
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a careful assistant. Output only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        if self.cfg.thinking:
            payload["thinking"] = {"type": self.cfg.thinking}

        backoff_s = 1.0
        last_exc: Exception | None = None
        last_status: int | None = None
        last_body_prefix: str | None = None

        def body_prefix(r: httpx.Response) -> str:
            try:
                t = r.text
            except Exception:
                return "<unavailable>"
            t = t.replace("\n", " ").replace("\r", " ")
            return t[:400]

        def extract_api_error(r: httpx.Response) -> str | None:
            try:
                data = r.json()
            except Exception:
                return None
            if isinstance(data, dict):
                err = data.get("error")
                if isinstance(err, dict):
                    code = err.get("code")
                    msg = err.get("message")
                    if isinstance(code, str) and isinstance(msg, str):
                        return f"{code}: {msg}"
                    if isinstance(msg, str):
                        return msg
            return None

        for attempt in range(6):
            try:
                r = self._client.post(url, headers=headers, json=payload)
                last_status = r.status_code
                last_body_prefix = body_prefix(r)

                if r.status_code == 404:
                    raise RuntimeError(f"endpoint not found (404): {url}")

                if r.status_code in (401, 403):
                    api_err = extract_api_error(r)
                    msg = api_err or last_body_prefix or "<no body>"
                    raise RuntimeError(f"auth failed ({r.status_code}): {msg}")

                if r.status_code in (429, 500, 502, 503, 504):
                    if r.status_code == 429:
                        api_err = extract_api_error(r)
                        # Some providers use 429 for non-rate-limit errors (e.g., quota/billing).
                        if api_err and (
                            "Insufficient balance" in api_err
                            or "no resource package" in api_err
                            or api_err.startswith("1113:")
                        ):
                            hint = ""
                            if "api.z.ai/api/paas/v4" in self.cfg.base_url:
                                hint = " (if you are on the Z.AI GLM Coding Plan, try base_url=https://api.z.ai/api/coding/paas/v4)"
                            raise RuntimeError(f"provider quota/billing error: {api_err}{hint}")

                    retry_after = r.headers.get("retry-after")
                    if retry_after:
                        try:
                            sleep_s = float(retry_after)
                        except Exception:
                            sleep_s = backoff_s
                    else:
                        sleep_s = backoff_s
                    time.sleep(sleep_s)
                    backoff_s = min(backoff_s * 2, 8.0)
                    continue
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                last_exc = e
                time.sleep(backoff_s)
                backoff_s = min(backoff_s * 2, 8.0)
        else:
            extra = ""
            if last_status is not None:
                extra = f" last_status={last_status}"
            if last_body_prefix:
                extra += f" body={last_body_prefix}"
            raise RuntimeError(f"request failed after retries.{extra}") from last_exc

        content = None
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception:
            try:
                content = data["choices"][0]["text"]
            except Exception as e:
                raise ValueError(f"unexpected response shape: {data}") from e

        if not isinstance(content, str):
            raise ValueError("unexpected response content type")

        return extract_type_list(content)
