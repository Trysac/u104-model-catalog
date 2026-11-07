"""Behavior tests for the public API of model_catalog."""

from __future__ import annotations

import pytest

import model_catalog


def test_normalize_trims_and_lowercases() -> None:
    assert model_catalog.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        model_catalog.normalize(value)


def test_version_is_semver() -> None:
    parts = model_catalog.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
