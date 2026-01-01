from __future__ import annotations

from dataclasses import dataclass


def normalize_address(addr: str) -> str:
    """
    Canonicalize an address as 32-byte (64 hex) lowercase with 0x prefix.
    """
    s = addr.strip().lower()
    if not s.startswith("0x"):
        return addr
    h = s[2:]
    if not h:
        return "0x" + "0" * 64
    if len(h) > 64:
        # If it's longer than 32 bytes, keep it as-is; this is unexpected for Sui Move types.
        return s
    return "0x" + h.rjust(64, "0")


def canonical_base_type(type_str: str) -> str:
    """
    Normalize a Sui type string to its canonical base type (no type args, canonical address).

    Examples:
      - "0x2::coin::Coin<0x2::sui::SUI>" -> "0x000...0002::coin::Coin"
      - "0x2::object::UID" -> "0x000...0002::object::UID"
    """
    s = type_str.strip()
    i = s.find("<")
    base = s[:i] if i != -1 else s
    parts = base.split("::")
    if len(parts) < 3:
        return base
    addr = normalize_address(parts[0])
    return "::".join([addr, parts[1], parts[2]])


def extract_created_object_types(dev_inspect: dict) -> set[str]:
    """
    Best-effort extraction of created object types from a devInspect-like response.

    We prefer `objectChanges` because it contains `objectType` strings. Some responses
    may not include types in effects, in which case this returns an empty set.
    """
    out: set[str] = set()

    # Some RPC responses nest as { effects: { objectChanges: [...] } }
    effects = dev_inspect.get("effects")
    if isinstance(effects, dict):
        dev_inspect = effects

    obj_changes = dev_inspect.get("objectChanges")
    if isinstance(obj_changes, list):
        for ch in obj_changes:
            if not isinstance(ch, dict):
                continue
            if ch.get("type") != "created":
                continue
            ot = ch.get("objectType")
            if isinstance(ot, str) and ot:
                out.add(ot)
    return out


@dataclass(frozen=True)
class InhabitationScore:
    targets: int
    created_distinct: int
    created_hits: int
    missing: int


def score_inhabitation(*, target_key_types: set[str], created_object_types: set[str]) -> InhabitationScore:
    """
    Scores inhabitation as: number of target key types successfully created at least once.

    Matching is done on base types (ignoring type arguments).
    """
    target_base = {canonical_base_type(t) for t in target_key_types}
    created_base = {canonical_base_type(t) for t in created_object_types}

    hits = target_base & created_base
    missing = target_base - hits

    return InhabitationScore(
        targets=len(target_base),
        created_distinct=len(created_base),
        created_hits=len(hits),
        missing=len(missing),
    )
