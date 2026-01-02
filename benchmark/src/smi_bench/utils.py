"""Shared utility functions for error handling, validation, and resource management."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import time
from pathlib import Path
from typing import Any


class BinaryNotFoundError(FileNotFoundError):
    """Raised when a required binary is not found."""

    pass


class BinaryNotExecutableError(PermissionError):
    """Raised when a binary exists but is not executable."""

    pass


def validate_binary(path: Path, *, binary_name: str = "binary") -> Path:
    """
    Validate that a binary exists and is executable.

    Args:
        path: Path to the binary.
        binary_name: Human-readable name for error messages.

    Returns:
        The validated path.

    Raises:
        BinaryNotFoundError: If the binary doesn't exist.
        BinaryNotExecutableError: If the binary isn't executable.
    """
    if not path.exists():
        raise BinaryNotFoundError(
            f"{binary_name} not found: {path}\n"
            f"Run: cargo build --release --locked"
        )
    # Prefer stat-based checks so we can distinguish between directories/files.
    # Note: some tests mock `Path.exists()` without creating a real file. In that case,
    # `stat()` may fail; treat that as "cannot verify" and allow the caller to proceed.
    try:
        st = path.stat()
    except OSError:
        return path

    if not stat.S_ISREG(st.st_mode):
        raise BinaryNotFoundError(f"{binary_name} is not a regular file: {path}")
    if not os.access(path, os.X_OK):
        raise BinaryNotExecutableError(f"{binary_name} is not executable: {path}")
    return path


def safe_json_loads(text: str, *, context: str = "", max_snippet_len: int = 100) -> Any:
    """
    Parse JSON with better error messages that include context and snippet.

    Args:
        text: JSON text to parse.
        context: Context string for error messages (e.g., "checkpoint file").
        max_snippet_len: Maximum length of error snippet to include.

    Returns:
        Parsed JSON object.

    Raises:
        ValueError: If JSON parsing fails, with context and snippet.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Extract snippet around error position
        start = max(0, e.pos - max_snippet_len // 2)
        end = min(len(text), e.pos + max_snippet_len // 2)
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        raise ValueError(
            f"JSON parse error{f' in {context}' if context else ''}: {e.msg}\n"
            f"Position {e.pos}, snippet: {snippet!r}"
        ) from e


def compute_json_checksum(data: dict[str, Any]) -> str:
    """
    Compute a short checksum for JSON data (for corruption detection).

    Args:
        data: Dictionary to checksum.

    Returns:
        8-character hex checksum.
    """
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode()).hexdigest()[:8]


def cleanup_old_temp_files(tmp_dir: Path, *, max_age_seconds: int = 86400) -> int:
    """
    Remove temporary files older than max_age_seconds.

    Args:
        tmp_dir: Directory containing temp files.
        max_age_seconds: Maximum age in seconds (default: 24 hours).

    Returns:
        Number of files removed.
    """
    if not tmp_dir.exists() or not tmp_dir.is_dir():
        return 0

    removed = 0
    now = time.time()
    for p in tmp_dir.glob("ptb_spec_*.json"):
        try:
            if now - p.stat().st_mtime > max_age_seconds:
                p.unlink()
                removed += 1
        except Exception:
            # Best-effort cleanup; ignore errors
            pass
    return removed


def ensure_temp_dir(tmp_dir: Path) -> Path:
    """
    Ensure a temp directory exists and clean up old files.

    Args:
        tmp_dir: Path to temp directory.

    Returns:
        The temp directory path.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    cleanup_old_temp_files(tmp_dir)
    return tmp_dir
