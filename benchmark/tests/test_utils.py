"""Tests for utility functions (P0/P1 fixes)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from smi_bench.utils import (
    BinaryNotFoundError,
    BinaryNotExecutableError,
    cleanup_old_temp_files,
    compute_json_checksum,
    ensure_temp_dir,
    safe_json_loads,
    validate_binary,
)


def test_validate_binary_not_found(tmp_path: Path) -> None:
    """Test binary validation raises clear error when binary doesn't exist."""
    fake_bin = tmp_path / "nonexistent"
    with pytest.raises(BinaryNotFoundError) as exc_info:
        validate_binary(fake_bin, binary_name="test binary")
    assert "not found" in str(exc_info.value).lower()
    assert "test binary" in str(exc_info.value)


def test_validate_binary_success(tmp_path: Path) -> None:
    """Test binary validation succeeds for existing executable."""
    test_bin = tmp_path / "test_bin"
    test_bin.write_text("#!/bin/sh\necho test\n")
    test_bin.chmod(0o755)
    result = validate_binary(test_bin, binary_name="test binary")
    assert result == test_bin


def test_safe_json_loads_success() -> None:
    """Test safe JSON parsing succeeds for valid JSON."""
    data = safe_json_loads('{"key": "value"}', context="test")
    assert data == {"key": "value"}


def test_safe_json_loads_error_context() -> None:
    """Test safe JSON parsing includes context in error messages."""
    with pytest.raises(ValueError) as exc_info:
        safe_json_loads('{"key": invalid}', context="test file")
    assert "test file" in str(exc_info.value)
    assert "snippet" in str(exc_info.value).lower()


def test_compute_json_checksum_deterministic() -> None:
    """Test checksum computation is deterministic."""
    data = {"a": 1, "b": 2}
    checksum1 = compute_json_checksum(data)
    checksum2 = compute_json_checksum(data)
    assert checksum1 == checksum2
    assert len(checksum1) == 8  # 8-character hex


def test_compute_json_checksum_order_independent() -> None:
    """Test checksum is independent of key order (uses sorted keys)."""
    data1 = {"a": 1, "b": 2}
    data2 = {"b": 2, "a": 1}
    assert compute_json_checksum(data1) == compute_json_checksum(data2)


def test_cleanup_old_temp_files(tmp_path: Path) -> None:
    """Test temp file cleanup removes old files."""
    import time

    # Create old file
    old_file = tmp_path / "ptb_spec_1000.json"
    old_file.write_text("{}")
    old_mtime = time.time() - 100000  # 100k seconds ago
    old_file.touch()
    import os

    os.utime(old_file, (old_mtime, old_mtime))

    # Create new file
    new_file = tmp_path / "ptb_spec_2000.json"
    new_file.write_text("{}")

    removed = cleanup_old_temp_files(tmp_path, max_age_seconds=86400)  # 24 hours
    assert removed == 1
    assert not old_file.exists()
    assert new_file.exists()


def test_ensure_temp_dir_creates_and_cleans(tmp_path: Path) -> None:
    """Test ensure_temp_dir creates directory and cleans old files."""
    tmp_dir = tmp_path / "tmp"
    result = ensure_temp_dir(tmp_dir)
    assert result == tmp_dir
    assert tmp_dir.exists()
    assert tmp_dir.is_dir()


def test_safe_json_loads_malformed() -> None:
    """Test safe JSON parsing provides helpful error for malformed JSON."""
    with pytest.raises(ValueError) as exc_info:
        safe_json_loads('{"unclosed": ', context="test")
    error_msg = str(exc_info.value)
    assert "test" in error_msg
    assert "snippet" in error_msg.lower() or "position" in error_msg.lower()
