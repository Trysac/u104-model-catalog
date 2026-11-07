"""Unit tests for model_catalog satisfying all acceptance criteria."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from model_catalog import CatalogError, load_catalog
from model_catalog.__main__ import main

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "catalog.json"


def test_fixture_get_m_a() -> None:
    """With the fixture catalog, get('m-a') returns a Model with input_per_mtok == Decimal('3.00'),
    output_per_mtok == Decimal('15.00') and context_window == 200000."""
    cat = load_catalog(FIXTURE_PATH)
    m = cat.get("m-a")
    assert m.input_per_mtok == Decimal("3.00")
    assert m.output_per_mtok == Decimal("15.00")
    assert m.context_window == 200000
    assert m.id == "m-a"
    assert m.provider == "alpha"
    assert m.capabilities == frozenset({"tools", "vision"})
    assert m.valid_from == date(2026, 1, 1)
    assert m.source == "https://example.com/pricing"


def test_versioning_and_not_valid_at() -> None:
    """For model 'm-a' with entries valid_from '2026-01-01' (price '3.00')
    and '2026-06-01' (price '2.50'):
    get('m-a', at=date(2026, 5, 31)).input_per_mtok == Decimal('3.00'),
    at=date(2026, 6, 1) gives Decimal('2.50'),
    and at=date(2025, 12, 31) raises CatalogError with code 'not_valid_at'."""
    raw = {
        "schema": "model-catalog/1",
        "version": "2026-11-06",
        "models": [
            {
                "id": "m-a",
                "provider": "alpha",
                "entries": [
                    {
                        "valid_from": "2026-01-01",
                        "context_window": 200000,
                        "max_output": 8192,
                        "input_per_mtok": "3.00",
                        "output_per_mtok": "15.00",
                        "capabilities": ["tools", "vision"],
                        "source": "https://example.com/pricing",
                    },
                    {
                        "valid_from": "2026-06-01",
                        "context_window": 200000,
                        "max_output": 8192,
                        "input_per_mtok": "2.50",
                        "output_per_mtok": "15.00",
                        "capabilities": ["tools", "vision"],
                        "source": "https://example.com/pricing-v2",
                    },
                ],
            }
        ],
    }
    cat = load_catalog(raw)
    assert cat.get("m-a", at=date(2026, 5, 31)).input_per_mtok == Decimal("3.00")
    assert cat.get("m-a", at=date(2026, 6, 1)).input_per_mtok == Decimal("2.50")

    with pytest.raises(CatalogError) as exc_info:
        cat.get("m-a", at=date(2025, 12, 31))
    assert exc_info.value.code == "not_valid_at"


def test_query_filters() -> None:
    """query(capabilities=['vision'], min_context=100_000) returns ids ['m-b', 'm-a'],
    query(provider='beta') returns ['m-c', 'm-b']
    and query(max_input_price=Decimal('0.50')) returns ['m-c', 'm-b']."""
    cat = load_catalog(FIXTURE_PATH)

    q1 = cat.query(capabilities=["vision"], min_context=100_000)
    assert [m.id for m in q1] == ["m-b", "m-a"]

    q2 = cat.query(provider="beta")
    assert [m.id for m in q2] == ["m-c", "m-b"]

    q3 = cat.query(max_input_price=Decimal("0.50"))
    assert [m.id for m in q3] == ["m-c", "m-b"]


def test_invalid_catalog_validations() -> None:
    """A float price 3.0 raises CatalogError with code 'invalid_catalog' whose message contains
    'models[0].entries[0].input_per_mtok'; an unknown capability 'telepathy', a duplicate model id
    and a duplicate valid_from within one model raise the same code."""
    # Float price
    cat_float: dict[str, Any] = {
        "schema": "model-catalog/1",
        "version": "2026-11-06",
        "models": [
            {
                "id": "m-a",
                "provider": "alpha",
                "entries": [
                    {
                        "valid_from": "2026-01-01",
                        "context_window": 200000,
                        "max_output": 8192,
                        "input_per_mtok": 3.0,
                        "output_per_mtok": "15.00",
                        "capabilities": ["tools"],
                        "source": "https://example.com",
                    }
                ],
            }
        ],
    }
    with pytest.raises(CatalogError) as exc1:
        load_catalog(cat_float)
    assert exc1.value.code == "invalid_catalog"
    assert "models[0].entries[0].input_per_mtok" in str(exc1.value)

    # Unknown capability 'telepathy'
    cat_cap: dict[str, Any] = {
        "schema": "model-catalog/1",
        "version": "2026-11-06",
        "models": [
            {
                "id": "m-a",
                "provider": "alpha",
                "entries": [
                    {
                        "valid_from": "2026-01-01",
                        "context_window": 200000,
                        "max_output": 8192,
                        "input_per_mtok": "3.00",
                        "output_per_mtok": "15.00",
                        "capabilities": ["telepathy"],
                        "source": "https://example.com",
                    }
                ],
            }
        ],
    }
    with pytest.raises(CatalogError) as exc2:
        load_catalog(cat_cap)
    assert exc2.value.code == "invalid_catalog"
    assert "models[0].entries[0].capabilities[0]" in str(exc2.value)

    # Duplicate model id
    cat_dup_id: dict[str, Any] = {
        "schema": "model-catalog/1",
        "version": "2026-11-06",
        "models": [
            {
                "id": "m-a",
                "provider": "alpha",
                "entries": [
                    {
                        "valid_from": "2026-01-01",
                        "context_window": 200000,
                        "max_output": 8192,
                        "input_per_mtok": "3.00",
                        "output_per_mtok": "15.00",
                        "capabilities": ["tools"],
                        "source": "https://example.com",
                    }
                ],
            },
            {
                "id": "m-a",
                "provider": "alpha-2",
                "entries": [
                    {
                        "valid_from": "2026-01-01",
                        "context_window": 200000,
                        "max_output": 8192,
                        "input_per_mtok": "3.00",
                        "output_per_mtok": "15.00",
                        "capabilities": ["tools"],
                        "source": "https://example.com",
                    }
                ],
            },
        ],
    }
    with pytest.raises(CatalogError) as exc3:
        load_catalog(cat_dup_id)
    assert exc3.value.code == "invalid_catalog"
    assert "duplicate model id 'm-a'" in str(exc3.value)

    # Duplicate valid_from within one model
    cat_dup_date: dict[str, Any] = {
        "schema": "model-catalog/1",
        "version": "2026-11-06",
        "models": [
            {
                "id": "m-a",
                "provider": "alpha",
                "entries": [
                    {
                        "valid_from": "2026-01-01",
                        "context_window": 200000,
                        "max_output": 8192,
                        "input_per_mtok": "3.00",
                        "output_per_mtok": "15.00",
                        "capabilities": ["tools"],
                        "source": "https://example.com",
                    },
                    {
                        "valid_from": "2026-01-01",
                        "context_window": 100000,
                        "max_output": 4096,
                        "input_per_mtok": "2.00",
                        "output_per_mtok": "10.00",
                        "capabilities": ["tools"],
                        "source": "https://example.com",
                    },
                ],
            }
        ],
    }
    with pytest.raises(CatalogError) as exc4:
        load_catalog(cat_dup_date)
    assert exc4.value.code == "invalid_catalog"
    assert "duplicate valid_from date '2026-01-01'" in str(exc4.value)


def test_unknown_model_and_size_limits(tmp_path: Path) -> None:
    """get('nope') raises CatalogError with code 'unknown_model', and a catalog file of 1_048_577
    bytes raises code 'too_large' while a 1_048_576-byte file padded with spaces loads."""
    cat = load_catalog(FIXTURE_PATH)
    with pytest.raises(CatalogError) as exc_nope:
        cat.get("nope")
    assert exc_nope.value.code == "unknown_model"

    # Prepare valid catalog json string
    base_json = json.dumps(
        {
            "schema": "model-catalog/1",
            "version": "2026-11-06",
            "models": [],
        }
    )
    assert len(base_json.encode("utf-8")) <= 1_048_576

    # Create a 1_048_576 file padded with trailing whitespace
    exact_pad = 1_048_576 - len(base_json.encode("utf-8"))
    exact_file = tmp_path / "exact.json"
    exact_file.write_bytes(base_json.encode("utf-8") + b" " * exact_pad)
    assert exact_file.stat().st_size == 1_048_576
    loaded = load_catalog(exact_file)
    assert loaded.query() == []

    # Create a 1_048_577 byte file
    oversized_file = tmp_path / "oversized.json"
    oversized_file.write_bytes(base_json.encode("utf-8") + b" " * (exact_pad + 1))
    assert oversized_file.stat().st_size == 1_048_577
    with pytest.raises(CatalogError) as exc_large:
        load_catalog(oversized_file)
    assert exc_large.value.code == "too_large"


def test_main_cli(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """main(['query', path, '--capability', 'vision']) prints exactly
    'm-b\tbeta\t128000\t0.50\t1.50\nm-a\talpha\t200000\t3.00\t15.00\n'
    and returns 0, and an invalid catalog file returns 2."""
    ret = main(["query", str(FIXTURE_PATH), "--capability", "vision"])
    assert ret == 0
    captured = capsys.readouterr()
    expected = "m-b\tbeta\t128000\t0.50\t1.50\nm-a\talpha\t200000\t3.00\t15.00\n"
    assert captured.out == expected

    # Invalid catalog file returns 2
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json", encoding="utf-8")
    ret_bad = main(["query", str(bad_file)])
    assert ret_bad == 2


def test_additional_edge_cases_and_cli_coverage(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test edge cases such as empty models list, unknown capability in query returning [],
    get command in CLI, at parameter in query and get, error paths, and properties."""
    cat = load_catalog(
        {
            "schema": "model-catalog/1",
            "version": "2026-11-06",
            "models": [],
        }
    )
    assert cat.schema == "model-catalog/1"
    assert cat.version == "2026-11-06"
    assert cat.query() == []
    assert cat.query(capabilities=["unknown_fake_cap"]) == []

    # Test CLI get command
    ret = main(["get", str(FIXTURE_PATH), "m-a"])
    assert ret == 0
    out = capsys.readouterr().out
    assert out == "m-a\talpha\t200000\t3.00\t15.00\n"

    # Test CLI get with --at
    ret_at = main(["get", str(FIXTURE_PATH), "m-a", "--at", "2026-05-01"])
    assert ret_at == 0
    assert capsys.readouterr().out == "m-a\talpha\t200000\t3.00\t15.00\n"

    # Test CLI get unknown model -> exit 1
    ret_unk = main(["get", str(FIXTURE_PATH), "nonexistent"])
    assert ret_unk == 1
    assert "unknown_model" in capsys.readouterr().err

    # CLI without args
    assert main([]) == 2

    # CLI with invalid date format
    assert main(["get", str(FIXTURE_PATH), "m-a", "--at", "invalid-date"]) == 2

    # CLI with invalid decimal format
    assert main(["query", str(FIXTURE_PATH), "--max-input-price", "invalid-num"]) == 2

    # Non-existent file via CLI
    assert main(["get", str(tmp_path / "missing.json"), "m-a"]) == 2

    # Catalog validation errors: bad schema
    with pytest.raises(CatalogError) as exc_schema:
        load_catalog({"schema": "bad-schema", "version": "2026-01-01", "models": []})
    assert exc_schema.value.code == "invalid_catalog"

    # Unknown key at root
    with pytest.raises(CatalogError) as exc_key:
        load_catalog(
            {"schema": "model-catalog/1", "version": "2026-01-01", "models": [], "extra": 1}
        )
    assert exc_key.value.code == "invalid_catalog"

    # Missing field at root
    with pytest.raises(CatalogError) as exc_missing:
        load_catalog({"schema": "model-catalog/1", "models": []})
    assert exc_missing.value.code == "invalid_catalog"

    # Invalid root type
    with pytest.raises(CatalogError):
        load_catalog("string-not-json-or-path-that-exists")  # type: ignore[arg-type]

    # Negative context window or bool
    with pytest.raises(CatalogError) as exc_int:
        load_catalog(
            {
                "schema": "model-catalog/1",
                "version": "2026-11-06",
                "models": [
                    {
                        "id": "m-a",
                        "provider": "alpha",
                        "entries": [
                            {
                                "valid_from": "2026-01-01",
                                "context_window": True,
                                "max_output": 8192,
                                "input_per_mtok": "3.00",
                                "output_per_mtok": "15.00",
                                "capabilities": ["tools"],
                                "source": "https://example.com",
                            }
                        ],
                    }
                ],
            }
        )
    assert exc_int.value.code == "invalid_catalog"

    # Decimal exponent kept in output
    m = load_catalog(FIXTURE_PATH).get("m-a")
    assert str(m.input_per_mtok) == "3.00"
