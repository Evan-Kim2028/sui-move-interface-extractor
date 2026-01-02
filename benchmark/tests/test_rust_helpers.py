"""Tests for Rust helper functions (P0/P1 fixes)."""

from __future__ import annotations

from pathlib import Path

import pytest

from smi_bench.rust import default_rust_binary, validate_rust_binary
from smi_bench.utils import BinaryNotFoundError


def test_default_rust_binary_returns_path() -> None:
    """Test default_rust_binary returns a Path (may not exist)."""
    path = default_rust_binary()
    assert isinstance(path, Path)


def test_validate_rust_binary_not_found(tmp_path: Path) -> None:
    """Test validate_rust_binary raises clear error when binary doesn't exist."""
    fake_bin = tmp_path / "nonexistent"
    with pytest.raises(BinaryNotFoundError) as exc_info:
        validate_rust_binary(fake_bin)
    assert "not found" in str(exc_info.value).lower()
    assert "cargo build" in str(exc_info.value).lower()
