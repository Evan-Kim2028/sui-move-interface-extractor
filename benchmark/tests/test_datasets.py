"""Tests for dataset manifest files."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_packages_with_keys_dataset_exists() -> None:
    p = Path("manifests/datasets/packages_with_keys.txt")
    assert p.exists(), "expected dataset manifest to exist"
    content = p.read_text(encoding="utf-8").strip().splitlines()
    assert any(line.strip() for line in content), "expected dataset manifest to be non-empty"


def test_top25_dataset_exists() -> None:
    p = Path("manifests/datasets/type_inhabitation_top25.txt")
    assert p.exists(), "expected top25 dataset manifest to exist"
    content = p.read_text(encoding="utf-8").strip().splitlines()

    # Check count (excluding header comments)
    package_lines = [line.strip() for line in content if line.strip() and not line.strip().startswith("#")]
    assert len(package_lines) == 25, f"expected 25 packages, got {len(package_lines)}"

    # Check all lines start with 0x
    assert all(line.startswith("0x") for line in package_lines), "all IDs should be 0x-prefixed"

    # Check no duplicates
    assert len(package_lines) == len(set(package_lines)), "expected no duplicate package IDs"


def test_type_inhabitation_top25_all_packages_in_phase2_benchmark() -> None:
    """Test that all packages in type_inhabitation_top25 are inhabitable (in Phase II benchmark)."""
    # Load type_inhabitation_top25 dataset
    top25_path = Path("manifests/datasets/type_inhabitation_top25.txt")
    top25_ids = set(
        line.strip()
        for line in top25_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )

    # Load Phase II benchmark
    phase2_path = Path("manifests/standard_phase2_benchmark.txt")
    phase2_ids = set(
        line.strip()
        for line in phase2_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )

    # All top25 packages should be in Phase II benchmark
    missing = top25_ids - phase2_ids
    assert len(missing) == 0, f"Packages not in Phase II benchmark: {missing}"


def test_type_inhabitation_top25_format_compliance() -> None:
    """Test that type_inhabitation_top25 dataset complies with format specifications."""
    dataset_path = Path("manifests/datasets/type_inhabitation_top25.txt")
    content = dataset_path.read_text(encoding="utf-8").splitlines()

    # Check header comments exist (lines 1-2)
    assert len(content) >= 2, "Dataset should have at least header lines"
    assert content[0].strip().startswith("#"), "First line should be header comment"
    assert content[1].strip().startswith("#"), "Second line should be header comment"

    # Check header contains purpose and count
    assert "25" in content[0] or "25" in content[1], "Header should contain package count"

    # Check header contains timestamp (ISO8601 format check)
    has_timestamp = any("T" in line and ":" in line for line in content[:2] if line.strip().startswith("#"))
    assert has_timestamp, "Header should contain ISO8601 timestamp"

    # Check no trailing whitespace
    has_trailing = any(line != line.rstrip() for line in content)
    assert not has_trailing, "Dataset should not have trailing whitespace"

    # Check no empty lines between packages
    package_lines = [i for i, line in enumerate(content) if line.strip() and not line.strip().startswith("#")]
    for i in range(len(package_lines) - 1):
        line_idx = package_lines[i]
        next_line_idx = package_lines[i + 1]
        assert next_line_idx == line_idx + 1, "Should have no empty lines between packages"


def test_dataset_format_standardization() -> None:
    """Test that all dataset files follow the same format standard."""
    datasets_dir = Path("manifests/datasets")

    if not datasets_dir.exists():
        pytest.skip(f"Datasets directory not found at {datasets_dir}")

    # Check all dataset files
    for dataset_file in datasets_dir.glob("*.txt"):
        content = dataset_file.read_text(encoding="utf-8").splitlines()

        # All package IDs should start with 0x
        package_lines = [line.strip() for line in content if line.strip() and not line.strip().startswith("#")]

        assert all(line.startswith("0x") for line in package_lines), (
            f"Dataset {dataset_file.name} has invalid package IDs (missing 0x prefix)"
        )

        # No duplicates
        assert len(package_lines) == len(set(package_lines)), f"Dataset {dataset_file.name} has duplicate package IDs"

        # No trailing whitespace
        has_trailing = any(line != line.rstrip() for line in content)
        assert not has_trailing, f"Dataset {dataset_file.name} has trailing whitespace"
