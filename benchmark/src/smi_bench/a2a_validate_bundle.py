from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _get_bundle(doc: Any) -> dict[str, Any]:
    if isinstance(doc, dict) and "schema_version" in doc and "benchmark" in doc:
        return doc

    if isinstance(doc, dict):
        result = doc.get("result")
        if isinstance(result, dict):
            artifacts = result.get("artifacts")
            if isinstance(artifacts, list):
                for a in artifacts:
                    if isinstance(a, dict) and a.get("name") == "evaluation_bundle":
                        parts = a.get("parts")
                        if isinstance(parts, list) and parts:
                            p0 = parts[0]
                            if isinstance(p0, dict) and isinstance(p0.get("text"), str):
                                bundle = json.loads(p0["text"])
                                if isinstance(bundle, dict):
                                    return bundle

    raise ValueError("input is neither an evaluation_bundle nor a JSON-RPC response containing one")


def _validate_required(bundle: dict[str, Any], required: list[str]) -> list[str]:
    missing: list[str] = []
    for k in required:
        if k not in bundle:
            missing.append(k)
    return missing


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Validate an evaluation_bundle against the repo schema")
    p.add_argument("path", type=Path, help="Path to evaluation_bundle JSON or JSON-RPC response JSON")
    p.add_argument(
        "--schema",
        type=Path,
        default=Path("docs/evaluation_bundle.schema.json"),
        help="Path to schema JSON (relative to benchmark/)",
    )
    args = p.parse_args(argv)

    doc = _load_json(args.path)
    bundle = _get_bundle(doc)

    schema = _load_json(args.schema)
    if not isinstance(schema, dict):
        raise SystemExit("schema is not a JSON object")

    required = schema.get("required")
    if not isinstance(required, list) or not all(isinstance(x, str) for x in required):
        raise SystemExit("schema.required must be a list of strings")

    missing = _validate_required(bundle, required)
    if missing:
        raise SystemExit(f"invalid: missing keys: {', '.join(missing)}")

    spec = bundle.get("spec_url")
    schema_id = schema.get("$id")
    if schema_id and spec and spec != schema_id:
        raise SystemExit(f"invalid: spec_url={spec!r} does not match schema $id={schema_id!r}")

    print("valid")


if __name__ == "__main__":
    main()
