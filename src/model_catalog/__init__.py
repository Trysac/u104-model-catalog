"""Versioned, validated catalog of LLM models with point-in-time lookups and queries."""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal

__all__ = [
    "Catalog",
    "CatalogError",
    "ErrorCode",
    "Model",
    "load_catalog",
]

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

ErrorCode = Literal["invalid_catalog", "unknown_model", "not_valid_at", "too_large"]

ALLOWED_CAPABILITIES = frozenset(
    {
        "vision",
        "tools",
        "json_mode",
        "streaming",
        "reasoning",
        "audio",
        "batch",
        "caching",
    }
)

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,99}$")
PRICE_PATTERN = re.compile(r"^\d+(\.\d{1,6})?$")
MAX_MODELS = 1000
MAX_ENTRIES_PER_MODEL = 100
DEFAULT_MAX_BYTES = 1_048_576


class CatalogError(Exception):
    """Base exception for all model_catalog errors."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        truncated_msg = message[:200] if len(message) > 200 else message
        super().__init__(truncated_msg)
        self.code: ErrorCode = code
        self.message: str = truncated_msg

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


@dataclass(frozen=True, slots=True)
class Model:
    """A snapshot of an LLM model's specs and pricing at a given point in time."""

    id: str
    provider: str
    context_window: int
    max_output: int
    input_per_mtok: Decimal
    output_per_mtok: Decimal
    capabilities: frozenset[str]
    valid_from: date
    source: str


@dataclass(frozen=True, slots=True)
class _ModelEntry:
    valid_from: date
    context_window: int
    max_output: int
    input_per_mtok: Decimal
    output_per_mtok: Decimal
    capabilities: frozenset[str]
    source: str


@dataclass(frozen=True, slots=True)
class _ModelDefinition:
    id: str
    provider: str
    entries: list[_ModelEntry]


class Catalog:
    """In-memory validated model catalog."""

    def __init__(self, schema: str, version: str, definitions: dict[str, _ModelDefinition]) -> None:
        self._schema = schema
        self._version = version
        self._definitions = definitions

    @property
    def schema(self) -> str:
        """Schema identifier string."""
        return self._schema

    @property
    def version(self) -> str:
        """Catalog version date string."""
        return self._version

    def get(self, model_id: str, *, at: date | None = None) -> Model:
        """Get model specifications by id, optionally evaluated as of a specific date."""
        model_def = self._definitions.get(model_id)
        if model_def is None:
            raise CatalogError("unknown_model", f"Unknown model id: {model_id}")

        if at is None:
            entry = model_def.entries[-1]
        else:
            valid_entries = [e for e in model_def.entries if e.valid_from <= at]
            if not valid_entries:
                raise CatalogError(
                    "not_valid_at",
                    f"Model {model_id} has no entry valid at {at.isoformat()}",
                )
            entry = max(valid_entries, key=lambda e: e.valid_from)

        return Model(
            id=model_def.id,
            provider=model_def.provider,
            context_window=entry.context_window,
            max_output=entry.max_output,
            input_per_mtok=entry.input_per_mtok,
            output_per_mtok=entry.output_per_mtok,
            capabilities=entry.capabilities,
            valid_from=entry.valid_from,
            source=entry.source,
        )

    def query(
        self,
        *,
        provider: str | None = None,
        min_context: int | None = None,
        capabilities: Iterable[str] = (),
        max_input_price: Decimal | None = None,
        at: date | None = None,
    ) -> list[Model]:
        """Query models matching criteria, sorted by (input_per_mtok, id)."""
        req_caps = frozenset(capabilities)
        results: list[Model] = []

        for m_id in self._definitions:
            try:
                m = self.get(m_id, at=at)
            except CatalogError as err:
                if err.code == "not_valid_at":
                    continue
                raise

            if provider is not None and m.provider != provider:
                continue
            if min_context is not None and m.context_window < min_context:
                continue
            if req_caps and not req_caps.issubset(m.capabilities):
                continue
            if max_input_price is not None and m.input_per_mtok > max_input_price:
                continue

            results.append(m)

        results.sort(key=lambda item: (item.input_per_mtok, item.id))
        return results


def _parse_iso_date(val: Any, path: str) -> date:
    if not isinstance(val, str) or len(val) != 10:
        raise CatalogError("invalid_catalog", f"{path}: date must be YYYY-MM-DD string")
    try:
        return date.fromisoformat(val)
    except ValueError as exc:
        raise CatalogError("invalid_catalog", f"{path}: invalid date format ({exc})") from exc


def _parse_positive_int(val: Any, path: str) -> int:
    if isinstance(val, bool) or not isinstance(val, int) or val <= 0:
        raise CatalogError("invalid_catalog", f"{path}: must be an integer > 0")
    return val


def _parse_price_decimal(val: Any, path: str) -> Decimal:
    if not isinstance(val, str) or not PRICE_PATTERN.match(val):
        raise CatalogError(
            "invalid_catalog",
            f"{path}: price must be a decimal string matching ^\\d+(\\.\\d{{1,6}})?$",
        )
    return Decimal(val)


def _validate_keys(mapping: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = set(mapping.keys()) - allowed
    if unknown:
        first = sorted(unknown)[0]
        raise CatalogError("invalid_catalog", f"{path}: unknown key '{first}'")


def _parse_model_entry(raw: Any, path: str) -> _ModelEntry:
    if not isinstance(raw, dict):
        raise CatalogError("invalid_catalog", f"{path}: entry must be an object")

    allowed_keys = {
        "valid_from",
        "context_window",
        "max_output",
        "input_per_mtok",
        "output_per_mtok",
        "capabilities",
        "source",
    }
    _validate_keys(raw, allowed_keys, path)

    for key in allowed_keys:
        if key not in raw:
            raise CatalogError("invalid_catalog", f"{path}.{key}: missing required field")

    valid_from = _parse_iso_date(raw["valid_from"], f"{path}.valid_from")
    context_window = _parse_positive_int(raw["context_window"], f"{path}.context_window")
    max_output = _parse_positive_int(raw["max_output"], f"{path}.max_output")
    input_per_mtok = _parse_price_decimal(raw["input_per_mtok"], f"{path}.input_per_mtok")
    output_per_mtok = _parse_price_decimal(raw["output_per_mtok"], f"{path}.output_per_mtok")

    raw_caps = raw["capabilities"]
    if not isinstance(raw_caps, list):
        raise CatalogError("invalid_catalog", f"{path}.capabilities: must be a list of strings")

    caps: set[str] = set()
    for idx, c in enumerate(raw_caps):
        if not isinstance(c, str):
            raise CatalogError(
                "invalid_catalog",
                f"{path}.capabilities[{idx}]: capability must be a string",
            )
        if c not in ALLOWED_CAPABILITIES:
            raise CatalogError(
                "invalid_catalog",
                f"{path}.capabilities[{idx}]: unknown capability '{c}'",
            )
        caps.add(c)

    raw_source = raw["source"]
    if not isinstance(raw_source, str) or not raw_source.strip():
        raise CatalogError("invalid_catalog", f"{path}.source: source must be a non-empty string")

    return _ModelEntry(
        valid_from=valid_from,
        context_window=context_window,
        max_output=max_output,
        input_per_mtok=input_per_mtok,
        output_per_mtok=output_per_mtok,
        capabilities=frozenset(caps),
        source=raw_source,
    )


def _parse_model(raw: Any, path: str) -> _ModelDefinition:
    if not isinstance(raw, dict):
        raise CatalogError("invalid_catalog", f"{path}: model must be an object")

    allowed_keys = {"id", "provider", "entries"}
    _validate_keys(raw, allowed_keys, path)

    for key in allowed_keys:
        if key not in raw:
            raise CatalogError("invalid_catalog", f"{path}.{key}: missing required field")

    raw_id = raw["id"]
    if not isinstance(raw_id, str) or not ID_PATTERN.match(raw_id):
        raise CatalogError("invalid_catalog", f"{path}.id: invalid model id format")

    raw_provider = raw["provider"]
    if not isinstance(raw_provider, str) or not raw_provider.strip():
        raise CatalogError(
            "invalid_catalog", f"{path}.provider: provider must be a non-empty string"
        )

    raw_entries = raw["entries"]
    if not isinstance(raw_entries, list) or len(raw_entries) == 0:
        raise CatalogError("invalid_catalog", f"{path}.entries: must be a non-empty list")
    if len(raw_entries) > MAX_ENTRIES_PER_MODEL:
        raise CatalogError(
            "invalid_catalog",
            f"{path}.entries: cannot exceed {MAX_ENTRIES_PER_MODEL} entries",
        )

    entries: list[_ModelEntry] = []
    seen_dates: set[date] = set()
    for idx, e in enumerate(raw_entries):
        entry_path = f"{path}.entries[{idx}]"
        entry = _parse_model_entry(e, entry_path)
        if entry.valid_from in seen_dates:
            raise CatalogError(
                "invalid_catalog",
                f"{entry_path}.valid_from: duplicate valid_from date "
                f"'{entry.valid_from.isoformat()}'",
            )
        seen_dates.add(entry.valid_from)
        entries.append(entry)

    # Keep entries sorted chronologically
    entries.sort(key=lambda item: item.valid_from)
    return _ModelDefinition(id=raw_id, provider=raw_provider, entries=entries)


def load_catalog(
    source: str | os.PathLike[str] | Mapping[str, Any],
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Catalog:
    """Load and validate a model catalog from a file path or in-memory mapping."""
    raw_data: Any
    if isinstance(source, (str, os.PathLike)):
        path_obj = os.fspath(source)
        try:
            size = os.path.getsize(path_obj)
        except OSError as exc:
            raise CatalogError("invalid_catalog", f"Cannot read catalog file: {exc}") from exc

        if size > max_bytes:
            raise CatalogError(
                "too_large", f"Catalog file size {size} exceeds max_bytes {max_bytes}"
            )

        try:
            with open(path_obj, "rb") as f:
                content = f.read()
        except OSError as exc:
            raise CatalogError("invalid_catalog", f"Cannot open file: {exc}") from exc

        if len(content) > max_bytes:
            raise CatalogError(
                "too_large", f"Catalog file size {len(content)} exceeds max_bytes {max_bytes}"
            )

        try:
            raw_data = json.loads(content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CatalogError("invalid_catalog", f"Failed to decode JSON: {exc}") from exc
    elif isinstance(source, Mapping):
        raw_data = source
    else:
        raise CatalogError("invalid_catalog", "source must be a file path or Mapping")

    if not isinstance(raw_data, Mapping):
        raise CatalogError("invalid_catalog", "catalog root must be an object")

    allowed_root_keys = {"schema", "version", "models"}
    _validate_keys(raw_data, allowed_root_keys, "$")

    for key in allowed_root_keys:
        if key not in raw_data:
            raise CatalogError("invalid_catalog", f"${key}: missing required field")

    raw_schema = raw_data["schema"]
    if raw_schema != "model-catalog/1":
        raise CatalogError("invalid_catalog", f"$.schema: unsupported schema '{raw_schema}'")

    raw_version = raw_data["version"]
    _parse_iso_date(raw_version, "$.version")

    raw_models = raw_data["models"]
    if not isinstance(raw_models, list):
        raise CatalogError("invalid_catalog", "$.models: must be a list")
    if len(raw_models) > MAX_MODELS:
        raise CatalogError("invalid_catalog", f"$.models: cannot exceed {MAX_MODELS} models")

    definitions: dict[str, _ModelDefinition] = {}
    for idx, raw_model in enumerate(raw_models):
        model_path = f"models[{idx}]"
        model_def = _parse_model(raw_model, model_path)
        if model_def.id in definitions:
            raise CatalogError(
                "invalid_catalog", f"{model_path}.id: duplicate model id '{model_def.id}'"
            )
        definitions[model_def.id] = model_def

    return Catalog(schema=str(raw_schema), version=str(raw_version), definitions=definitions)
