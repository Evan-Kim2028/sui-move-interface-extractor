from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DryRunFailure:
    status: str | None
    error: str | None
    abort_code: int | None
    abort_location: str | None


_ABORT_CODE_RE = re.compile(r"\b([Aa]bort|MoveAbort)\b.*?\bcode\b[^0-9]*([0-9]+)")
_ABORT_CODE_RE2 = re.compile(r"\bMoveAbort\b.*?[, ]\s*([0-9]+)\b")
_ABORT_LOC_RE = re.compile(r"\b0x[0-9a-fA-F]{1,64}::[A-Za-z_][A-Za-z0-9_]*::[A-Za-z_][A-Za-z0-9_]*\b")


def _parse_abort_code(error: str) -> int | None:
    m = _ABORT_CODE_RE.search(error)
    if m:
        try:
            return int(m.group(2))
        except Exception:
            return None
    m = _ABORT_CODE_RE2.search(error)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def _parse_abort_location(error: str) -> str | None:
    m = _ABORT_LOC_RE.search(error)
    if m:
        return m.group(0)
    return None


def classify_dry_run_response(dry_run: dict) -> tuple[bool, DryRunFailure | None]:
    """
    Classify a DryRunTransactionBlockResponse JSON (as emitted by `smi_tx_sim`).

    Returns:
    - (exec_ok, None) for success
    - (False, DryRunFailure) for failure (best-effort parsing)
    """
    effects = dry_run.get("effects")
    if not isinstance(effects, dict):
        # If effects are missing, treat as non-exec-ok (unexpected shape).
        return False, DryRunFailure(status=None, error="missing effects", abort_code=None, abort_location=None)

    status = effects.get("status")
    if not isinstance(status, dict):
        return False, DryRunFailure(status=None, error="missing effects.status", abort_code=None, abort_location=None)

    st = status.get("status")
    st_s = str(st) if isinstance(st, str) else None
    if st_s == "success":
        return True, None

    # Failure: try to extract a useful error string.
    err = status.get("error")
    err_s = str(err) if isinstance(err, str) else None

    # Some responses include `executionErrorSource` (top-level).
    if not err_s:
        ees = dry_run.get("executionErrorSource")
        if isinstance(ees, str) and ees:
            err_s = ees

    abort_code = _parse_abort_code(err_s) if err_s else None
    abort_loc = _parse_abort_location(err_s) if err_s else None

    return False, DryRunFailure(status=st_s, error=err_s, abort_code=abort_code, abort_location=abort_loc)
