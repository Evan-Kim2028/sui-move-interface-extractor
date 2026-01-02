"""Schema types and validators.

This module provides TypedDict definitions and validation functions to ensure
schema stability and catch accidental breakage during refactors.
"""

from __future__ import annotations

from typing import Any, TypedDict

# Phase I Schema Definitions

class Phase1PackageRow(TypedDict, total=False):
    """Schema for a single package row in Phase I output."""
    package_id: str
    truth_key_types: int
    predicted_key_types: int
    score: dict[str, Any]  # KeyTypeScore dict
    error: str | None
    elapsed_seconds: float | None
    attempts: int | None
    max_structs_used: int | None
    timed_out: bool | None
    truth_key_types_list: list[str] | None
    predicted_key_types_list: list[str] | None


class Phase1RunJson(TypedDict, total=False):
    """Schema for Phase I run JSON output."""
    schema_version: int
    started_at_unix_seconds: int
    finished_at_unix_seconds: int
    corpus_root_name: str
    corpus_git: dict[str, Any] | None
    target_ids_file: str | None
    target_ids_total: int | None
    samples: int
    seed: int
    agent: str
    aggregate: dict[str, Any]
    packages: list[Phase1PackageRow]
    _checksum: str  # Optional, added by checkpoint writer


# Phase II Schema Definitions

class Phase2PackageRow(TypedDict, total=False):
    """Schema for a single package row in Phase II output."""
    package_id: str
    score: dict[str, Any]  # InhabitationScore dict
    error: str | None
    elapsed_seconds: float | None
    timed_out: bool | None
    created_object_types_list: list[str] | None
    simulation_mode: str | None
    fell_back_to_dev_inspect: bool | None
    ptb_parse_ok: bool | None
    tx_build_ok: bool | None
    dry_run_ok: bool | None
    dry_run_exec_ok: bool | None
    dry_run_status: str | None
    dry_run_effects_error: str | None
    dry_run_abort_code: int | None
    dry_run_abort_location: str | None
    dev_inspect_ok: bool | None
    dry_run_error: str | None
    plan_attempts: int | None
    sim_attempts: int | None
    gas_budget_used: int | None
    plan_variant: str | None
    schema_violation_count: int | None
    schema_violation_attempts_until_first_valid: int | None
    semantic_failure_count: int | None
    semantic_failure_attempts_until_first_success: int | None


class Phase2RunJson(TypedDict, total=False):
    """Schema for Phase II run JSON output."""
    schema_version: int
    started_at_unix_seconds: int
    finished_at_unix_seconds: int
    corpus_root_name: str
    samples: int
    seed: int
    agent: str
    rpc_url: str
    sender: str
    gas_budget: int
    gas_coin: str | None
    aggregate: dict[str, Any]
    packages: list[Phase2PackageRow]
    _checksum: str  # Optional, added by checkpoint writer


# Validation Functions

def validate_phase1_run_json(data: dict[str, Any]) -> None:
    """Validate Phase I run JSON against schema.
    
    Raises ValueError with descriptive message if validation fails.
    This catches accidental renames/removals early.
    """
    # Required top-level fields
    required_fields = {
        "schema_version": int,
        "started_at_unix_seconds": int,
        "finished_at_unix_seconds": int,
        "corpus_root_name": str,
        "samples": int,
        "seed": int,
        "agent": str,
        "aggregate": dict,
        "packages": list,
    }
    
    for field, expected_type in required_fields.items():
        if field not in data:
            raise ValueError(f"missing required field: {field}")
        if not isinstance(data[field], expected_type):
            raise ValueError(
                f"field {field}: expected {expected_type.__name__}, got {type(data[field]).__name__}"
            )
    
    # Validate schema_version
    if data["schema_version"] not in (1, 2):
        raise ValueError(f"unsupported schema_version: {data['schema_version']} (expected 1 or 2)")
    
    # Validate aggregate structure
    aggregate = data["aggregate"]
    if not isinstance(aggregate, dict):
        raise ValueError("aggregate must be a dict")
    
    # Validate packages list
    packages = data["packages"]
    if not isinstance(packages, list):
        raise ValueError("packages must be a list")
    
    for i, pkg in enumerate(packages):
        if not isinstance(pkg, dict):
            raise ValueError(f"packages[{i}]: must be a dict")
        
        # Required package fields
        if "package_id" not in pkg:
            raise ValueError(f"packages[{i}]: missing required field 'package_id'")
        if not isinstance(pkg["package_id"], str):
            raise ValueError(f"packages[{i}].package_id: must be a string")
        
        if "truth_key_types" not in pkg:
            raise ValueError(f"packages[{i}]: missing required field 'truth_key_types'")
        if not isinstance(pkg["truth_key_types"], int):
            raise ValueError(f"packages[{i}].truth_key_types: must be an int")
        
        if "predicted_key_types" not in pkg:
            raise ValueError(f"packages[{i}]: missing required field 'predicted_key_types'")
        if not isinstance(pkg["predicted_key_types"], int):
            raise ValueError(f"packages[{i}].predicted_key_types: must be an int")
        
        if "score" not in pkg:
            raise ValueError(f"packages[{i}]: missing required field 'score'")
        if not isinstance(pkg["score"], dict):
            raise ValueError(f"packages[{i}].score: must be a dict")
        
        # Validate score dict has required keys
        score = pkg["score"]
        required_score_keys = {"tp", "fp", "fn", "precision", "recall", "f1", "missing_sample", "extra_sample"}
        missing_keys = required_score_keys - set(score.keys())
        if missing_keys:
            raise ValueError(f"packages[{i}].score: missing required keys: {missing_keys}")
        
        # Validate score types
        if not isinstance(score["tp"], int):
            raise ValueError(f"packages[{i}].score.tp: must be an int")
        if not isinstance(score["fp"], int):
            raise ValueError(f"packages[{i}].score.fp: must be an int")
        if not isinstance(score["fn"], int):
            raise ValueError(f"packages[{i}].score.fn: must be an int")
        if not isinstance(score["precision"], (int, float)):
            raise ValueError(f"packages[{i}].score.precision: must be a number")
        if not isinstance(score["recall"], (int, float)):
            raise ValueError(f"packages[{i}].score.recall: must be a number")
        if not isinstance(score["f1"], (int, float)):
            raise ValueError(f"packages[{i}].score.f1: must be a number")
        if not isinstance(score["missing_sample"], list):
            raise ValueError(f"packages[{i}].score.missing_sample: must be a list")
        if not isinstance(score["extra_sample"], list):
            raise ValueError(f"packages[{i}].score.extra_sample: must be a list")
    
    # Optional fields are allowed (additive schema)
    # _checksum is allowed but not validated here (handled by checkpoint loader)


def validate_phase2_run_json(data: dict[str, Any]) -> None:
    """Validate Phase II run JSON against schema.
    
    Raises ValueError with descriptive message if validation fails.
    This catches accidental renames/removals early.
    """
    # Required top-level fields
    required_fields = {
        "schema_version": int,
        "started_at_unix_seconds": int,
        "finished_at_unix_seconds": int,
        "corpus_root_name": str,
        "samples": int,
        "seed": int,
        "agent": str,
        "rpc_url": str,
        "sender": str,
        "gas_budget": int,
        "aggregate": dict,
        "packages": list,
    }
    
    for field, expected_type in required_fields.items():
        if field not in data:
            raise ValueError(f"missing required field: {field}")
        if not isinstance(data[field], expected_type):
            raise ValueError(
                f"field {field}: expected {expected_type.__name__}, got {type(data[field]).__name__}"
            )
    
    # Validate schema_version
    if data["schema_version"] not in (1, 2):
        raise ValueError(f"unsupported schema_version: {data['schema_version']} (expected 1 or 2)")
    
    # Validate aggregate structure
    aggregate = data["aggregate"]
    if not isinstance(aggregate, dict):
        raise ValueError("aggregate must be a dict")
    
    # Validate packages list
    packages = data["packages"]
    if not isinstance(packages, list):
        raise ValueError("packages must be a list")
    
    for i, pkg in enumerate(packages):
        if not isinstance(pkg, dict):
            raise ValueError(f"packages[{i}]: must be a dict")
        
        # Required package fields
        if "package_id" not in pkg:
            raise ValueError(f"packages[{i}]: missing required field 'package_id'")
        if not isinstance(pkg["package_id"], str):
            raise ValueError(f"packages[{i}].package_id: must be a string")
        
        if "score" not in pkg:
            raise ValueError(f"packages[{i}]: missing required field 'score'")
        if not isinstance(pkg["score"], dict):
            raise ValueError(f"packages[{i}].score: must be a dict")
        
        # Validate score dict has required keys
        score = pkg["score"]
        required_score_keys = {"targets", "created_distinct", "created_hits", "missing"}
        missing_keys = required_score_keys - set(score.keys())
        if missing_keys:
            raise ValueError(f"packages[{i}].score: missing required keys: {missing_keys}")
        
        # Validate score types
        if not isinstance(score["targets"], int):
            raise ValueError(f"packages[{i}].score.targets: must be an int")
        if not isinstance(score["created_distinct"], int):
            raise ValueError(f"packages[{i}].score.created_distinct: must be an int")
        if not isinstance(score["created_hits"], int):
            raise ValueError(f"packages[{i}].score.created_hits: must be an int")
        if not isinstance(score["missing"], int):
            raise ValueError(f"packages[{i}].score.missing: must be an int")
    
    # Optional fields are allowed (additive schema)
    # _checksum is allowed but not validated here (handled by checkpoint loader)
