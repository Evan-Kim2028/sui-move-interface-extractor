from __future__ import annotations

from typing import Any


class PTBCausalityError(ValueError):
    """Raised when a PTB plan violates causality or references missing inputs."""
    pass


def validate_ptb_causality(ptb_spec: dict[str, Any]) -> None:
    """
    Validate that a PTB spec is logically coherent.
    
    Invariants:
    1. If a call uses Result(i), then i must be < current_call_index.
    2. Every argument must be a known type (imm_or_owned_object, shared_object, pure, result).
    """
    if not isinstance(ptb_spec, dict):
        raise PTBCausalityError("PTB spec must be a dictionary")
    
    calls = ptb_spec.get("calls")
    if not isinstance(calls, list):
        raise PTBCausalityError("PTB spec must contain a 'calls' list")
    
    for i, call in enumerate(calls):
        if not isinstance(call, dict):
            raise PTBCausalityError(f"Call at index {i} must be a dictionary")
        
        args = call.get("args")
        if not isinstance(args, list):
            continue
            
        for arg_i, arg in enumerate(args):
            if not isinstance(arg, dict):
                raise PTBCausalityError(f"Argument {arg_i} in call {i} must be a dictionary")
            
            # Check for result reference
            if "result" in arg:
                res_idx = arg["result"]
                if not isinstance(res_idx, int):
                    raise PTBCausalityError(f"Result index in call {i}, arg {arg_i} must be an integer")
                if res_idx < 0:
                    raise PTBCausalityError(f"Result index in call {i}, arg {arg_i} cannot be negative")
                if res_idx >= i:
                    raise PTBCausalityError(
                        f"Causality violation in call {i}: references result {res_idx} "
                        f"which hasn't been produced yet."
                    )
            
            # Future expansion: validate shared_object vs imm_or_owned_object if we have inventory context
