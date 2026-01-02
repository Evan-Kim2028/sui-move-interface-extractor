from __future__ import annotations

import re
from typing import Any, cast

from smi_bench.utils import safe_json_loads


class JsonExtractError(ValueError):
    pass


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def extract_json_value(text: str) -> object:
    """
    Best-effort JSON extraction from a model response.
    Handles Raw JSON, Markdown fences, and prose-embedded JSON.
    """
    s = _strip_code_fences(text)
    try:
        return safe_json_loads(s, context="model response extraction")
    except ValueError as e:
        raise JsonExtractError(f"no JSON found: {e}") from e


def extract_type_list(text: str) -> set[str]:
    """
    Accepts either:
      - JSON array of strings: ["0x..::m::S", ...]
      - JSON object with key_types: {"key_types":[...]}
    """
    v = extract_json_value(text)
    if isinstance(v, list):
        return {x for x in v if isinstance(x, str)}
    if isinstance(v, dict):
        key_types = cast(dict[Any, Any], v).get("key_types")
        if isinstance(key_types, list):
            return {x for x in key_types if isinstance(x, str)}
    raise JsonExtractError("unexpected JSON shape (expected array or {key_types:[...]})")
