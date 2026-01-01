from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_ADDRESS = "0x" + ("1" * 64)
SUI_FRAMEWORK_ADDRESS = "0x" + ("0" * 63) + "2"
SUI_SYSTEM_STATE_OBJECT_ID = "0x5"
SUI_CLOCK_OBJECT_ID = "0x6"
SUI_AUTHENTICATOR_STATE_OBJECT_ID = "0x7"
SUI_RANDOM_OBJECT_ID = "0x8"
SUI_DENY_LIST_OBJECT_ID = "0x403"
SUI_COIN_REGISTRY_OBJECT_ID = "0xc"
SUI_MODULE = "sui"
SUI_STRUCT = "SUI"
COIN_MODULE = "coin"
COIN_STRUCT = "Coin"


class ExclusionReason:
    NOT_PUBLIC_ENTRY = "not_public_entry"
    HAS_TYPE_PARAMS = "has_type_params"
    UNSUPPORTED_PARAM_TYPE = "unsupported_param_type"
    NO_CANDIDATES = "no_candidates"
    INTERFACE_INVALID = "interface_missing_or_invalid"


@dataclass(frozen=True)
class SelectStats:
    packages_total: int = 0
    packages_selected: int = 0
    packages_failed_interface: int = 0
    packages_no_candidates: int = 0
    candidate_functions_total: int = 0
    rejection_reasons_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class PackageViability:
    public_entry_total: int
    public_entry_no_type_params_total: int
    public_entry_no_type_params_supported_args_total: int


@dataclass
class FunctionAnalysis:
    is_runnable: bool
    reasons: list[str]
    ptb_args: list[dict] = field(default_factory=list)
    ptb_type_args: list[str] = field(default_factory=list)


@dataclass
class PackageAnalysis:
    package_id: str
    candidates_ok: list[dict]  # list of {"target": "...", "args": [...]}
    candidates_rejected: list[dict]  # list of {"target": "...", "reasons": [...]}
    reasons_summary: dict[str, int]


def _is_tx_context_ref_param(t: dict) -> bool:
    """
    True if `t` is `&TxContext` or `&mut TxContext`.

    Canonical Type (from docs/SCHEMA.md):

      {"kind":"ref","mutable":bool,"to":{"kind":"datatype","address":"0x..","module":"tx_context","name":"TxContext",...}}
    """
    if not isinstance(t, dict):
        return False
    if t.get("kind") != "ref":
        return False
    to = t.get("to")
    if not isinstance(to, dict) or to.get("kind") != "datatype":
        return False
    if to.get("module") != "tx_context" or to.get("name") != "TxContext":
        return False
    addr = to.get("address")
    if not isinstance(addr, str):
        return False
    addr = addr.lower()
    return addr.startswith("0x") and len(addr) == 66 and addr.endswith("02")


def _is_sui_type(t: dict) -> bool:
    return (
        isinstance(t, dict)
        and t.get("kind") == "datatype"
        and t.get("address") == SUI_FRAMEWORK_ADDRESS
        and t.get("module") == SUI_MODULE
        and t.get("name") == SUI_STRUCT
        and t.get("type_args") == []
    )


def _is_coin_sui_type(t: dict) -> bool:
    return (
        isinstance(t, dict)
        and t.get("kind") == "datatype"
        and t.get("address") == SUI_FRAMEWORK_ADDRESS
        and t.get("module") == COIN_MODULE
        and t.get("name") == COIN_STRUCT
        and isinstance(t.get("type_args"), list)
        and len(t.get("type_args")) == 1
        and _is_sui_type(t.get("type_args")[0])
    )


def strip_implicit_tx_context_params(params: list[dict]) -> list[dict]:
    if not params:
        return []
    last = params[-1]
    if _is_tx_context_ref_param(last):
        return list(params[:-1])
    return list(params)


def type_to_default_ptb_arg(t: dict) -> dict | None:
    """
    Convert a canonical `Type` (docs/SCHEMA.md) into a default PTB arg spec
    supported by `smi_tx_sim` (Rust).
    """
    kind = t.get("kind") if isinstance(t, dict) else None
    if kind == "ref":
        to = t.get("to")
        if isinstance(to, dict) and to.get("kind") == "datatype":
            addr = to.get("address")
            mod = to.get("module")
            name = to.get("name")
            if (
                addr == SUI_FRAMEWORK_ADDRESS
                and mod == "clock"
                and name == "Clock"
                and isinstance(t.get("mutable"), bool)
            ):
                # Clock is a shared system object at 0x6.
                return {"shared_object": {"id": SUI_CLOCK_OBJECT_ID, "mutable": bool(t["mutable"])}}
            
            if (
                addr == SUI_FRAMEWORK_ADDRESS
                and mod == "random"
                and name == "Random"
                and isinstance(t.get("mutable"), bool)
            ):
                # Random is a shared system object at 0x8.
                return {"shared_object": {"id": SUI_RANDOM_OBJECT_ID, "mutable": bool(t["mutable"])}}

            if (
                addr == SUI_FRAMEWORK_ADDRESS
                and mod == "deny_list"
                and name == "DenyList"
                and isinstance(t.get("mutable"), bool)
            ):
                # DenyList is a shared system object at 0x403.
                return {"shared_object": {"id": SUI_DENY_LIST_OBJECT_ID, "mutable": bool(t["mutable"])}}

            if _is_coin_sui_type(to):
                # Coin<SUI> is owned by sender; resolve via RPC selection.
                return {"sender_sui_coin": {"index": 0, "exclude_gas": True}}
        return None
    if kind == "datatype" and _is_coin_sui_type(t):
        return {"sender_sui_coin": {"index": 0, "exclude_gas": True}}
    if kind == "bool":
        return {"bool": False}
    if kind == "u8":
        return {"u8": 1}
    if kind == "u16":
        return {"u16": 1}
    if kind == "u32":
        return {"u32": 1}
    if kind == "u64":
        return {"u64": 1}
    if kind == "address":
        return {"address": DEFAULT_ADDRESS}
    if kind == "vector":
        inner = t.get("type")
        if isinstance(inner, dict) and inner.get("kind") == "u8":
            return {"vector_u8_hex": "0x01"}
        if isinstance(inner, dict) and inner.get("kind") == "bool":
            return {"vector_bool": [False]}
        if isinstance(inner, dict) and inner.get("kind") == "u16":
            return {"vector_u16": [1]}
        if isinstance(inner, dict) and inner.get("kind") == "u32":
            return {"vector_u32": [1]}
        if isinstance(inner, dict) and inner.get("kind") == "u64":
            return {"vector_u64": [1]}
        if isinstance(inner, dict) and inner.get("kind") == "address":
            return {"vector_address": [DEFAULT_ADDRESS]}
        return None
    return None


def analyze_function(f: dict) -> FunctionAnalysis:
    reasons = []

    if f.get("visibility") != "public" or f.get("is_entry") is not True:
        reasons.append(ExclusionReason.NOT_PUBLIC_ENTRY)

    type_params = f.get("type_params")
    ptb_type_args: list[str] = []
    if isinstance(type_params, list) and type_params:
        # Heuristic: fill all type params with 0x2::sui::SUI
        # SUI has key+store+drop (mostly), satisfying many constraints.
        for _ in type_params:
            ptb_type_args.append(f"{SUI_FRAMEWORK_ADDRESS}::{SUI_MODULE}::{SUI_STRUCT}")

    params = f.get("params")
    ptb_args = []
    if isinstance(params, list):
        params = strip_implicit_tx_context_params([p for p in params if isinstance(p, dict)])
        for p in params:
            arg = type_to_default_ptb_arg(p)
            if arg is None:
                reasons.append(ExclusionReason.UNSUPPORTED_PARAM_TYPE)
                # We can stop checking params if one is unsupported, or collect all reasons.
                # For now, just marking unsupported type is enough.
                break
            ptb_args.append(arg)

    if reasons:
        return FunctionAnalysis(is_runnable=False, reasons=reasons)

    return FunctionAnalysis(is_runnable=True, reasons=[], ptb_args=ptb_args, ptb_type_args=ptb_type_args)


def analyze_package(interface_json: dict) -> PackageAnalysis:
    pkg_id = interface_json.get("package_id")
    if not isinstance(pkg_id, str) or not pkg_id:
        pkg_id = "0x0"

    modules = interface_json.get("modules")
    if not isinstance(modules, dict):
        return PackageAnalysis(
            package_id=pkg_id,
            candidates_ok=[],
            candidates_rejected=[],
            reasons_summary={ExclusionReason.INTERFACE_INVALID: 1},
        )

    candidates_ok = []
    candidates_rejected = []
    reasons_summary = {}

    for module_name in sorted(modules.keys()):
        mod = modules.get(module_name)
        if not isinstance(mod, dict):
            continue
        funs = mod.get("functions")
        if not isinstance(funs, dict):
            continue
        for fun_name in sorted(funs.keys()):
            f = funs.get(fun_name)
            if not isinstance(f, dict):
                continue

            target = f"{pkg_id}::{module_name}::{fun_name}"
            analysis = analyze_function(f)

            if analysis.is_runnable:
                candidates_ok.append({
                    "target": target,
                    "args": analysis.ptb_args,
                    "type_args": analysis.ptb_type_args
                })
            else:
                candidates_rejected.append({"target": target, "reasons": analysis.reasons})
                for r in analysis.reasons:
                    reasons_summary[r] = reasons_summary.get(r, 0) + 1

    if not candidates_ok and not candidates_rejected:
        # Empty package or no functions?
        # Counts as no candidates if it had modules but no functions analysis returned anything?
        # If it had modules, we traversed them.
        pass

    if not candidates_ok:
        reasons_summary[ExclusionReason.NO_CANDIDATES] = 1

    return PackageAnalysis(
        package_id=pkg_id,
        candidates_ok=candidates_ok,
        candidates_rejected=candidates_rejected,
        reasons_summary=reasons_summary,
    )


def compute_package_viability(interface_json: dict) -> PackageViability:
    """
    Compute conservative viability counts for Phase II executable-subset selection.

    This is intentionally "planfile-only" viability: public entry functions with no type params
    and only supported pure args (after stripping trailing TxContext ref).
    """
    modules = interface_json.get("modules")
    if not isinstance(modules, dict):
        return PackageViability(
            public_entry_total=0,
            public_entry_no_type_params_total=0,
            public_entry_no_type_params_supported_args_total=0,
        )

    public_entry_total = 0
    public_entry_no_type_params_total = 0
    public_entry_supported_total = 0

    for module_name in modules.keys():
        mod = modules.get(module_name)
        if not isinstance(mod, dict):
            continue
        funs = mod.get("functions")
        if not isinstance(funs, dict):
            continue
        for fun_name in funs.keys():
            f = funs.get(fun_name)
            if not isinstance(f, dict):
                continue
            if f.get("visibility") != "public" or f.get("is_entry") is not True:
                continue
            public_entry_total += 1

            type_params = f.get("type_params")
            if isinstance(type_params, list) and type_params:
                continue
            public_entry_no_type_params_total += 1

            params = f.get("params")
            if not isinstance(params, list):
                continue
            params = strip_implicit_tx_context_params([p for p in params if isinstance(p, dict)])
            ok = True
            for p in params:
                if type_to_default_ptb_arg(p) is None:
                    ok = False
                    break
            if ok:
                public_entry_supported_total += 1

    return PackageViability(
        public_entry_total=public_entry_total,
        public_entry_no_type_params_total=public_entry_no_type_params_total,
        public_entry_no_type_params_supported_args_total=public_entry_supported_total,
    )


def select_executable_ptb_spec(
    *,
    interface_json: dict,
    max_calls_per_package: int = 1,
) -> tuple[dict | None, list[dict]]:
    """
    Select a deterministic "executable subset" PTB spec from a package interface.

    Current policy (intentionally conservative):
    - `public entry` functions only
    - no type parameters
    - only "pure" arg types supported by `smi_tx_sim`
    - implicit trailing `&mut TxContext` is stripped

    Returns:
    - `ptb_spec` (or None if no candidates)
    - `selected_calls` (for reporting/debug)
    """
    pkg_id = interface_json.get("package_id")
    if not isinstance(pkg_id, str) or not pkg_id:
        pkg_id = "0x0"

    modules = interface_json.get("modules")
    if not isinstance(modules, dict):
        return None, []

    calls: list[dict] = []
    for module_name in sorted(modules.keys()):
        mod = modules.get(module_name)
        if not isinstance(mod, dict):
            continue
        funs = mod.get("functions")
        if not isinstance(funs, dict):
            continue
        for fun_name in sorted(funs.keys()):
            f = funs.get(fun_name)
            if not isinstance(f, dict):
                continue
            if f.get("visibility") != "public" or f.get("is_entry") is not True:
                continue
            type_params = f.get("type_params")
            if isinstance(type_params, list) and type_params:
                continue
            params = f.get("params")
            if not isinstance(params, list):
                continue
            params = strip_implicit_tx_context_params([p for p in params if isinstance(p, dict)])
            args: list[dict] = []
            ok = True
            for p in params:
                arg = type_to_default_ptb_arg(p)
                if arg is None:
                    ok = False
                    break
                args.append(arg)
            if not ok:
                continue
            calls.append({"target": f"{pkg_id}::{module_name}::{fun_name}", "type_args": [], "args": args})
            if len(calls) >= max_calls_per_package:
                return {"calls": calls}, calls

    if not calls:
        return None, []
    return {"calls": calls}, calls
