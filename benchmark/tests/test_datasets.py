from __future__ import annotations

from pathlib import Path


def test_packages_with_keys_dataset_exists() -> None:
    p = Path("manifests/datasets/packages_with_keys.txt")
    assert p.exists(), "expected dataset manifest to exist"
    content = p.read_text(encoding="utf-8").strip().splitlines()
    assert any(line.strip() for line in content), "expected dataset manifest to be non-empty"
