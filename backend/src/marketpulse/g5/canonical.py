"""Canonical durable-workspace snapshots for the G5 replay acceptance layer."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine


class CanonicalizationError(ValueError):
    """Raised when durable replay state cannot be normalized without loss."""


@dataclass(frozen=True)
class CanonicalRow:
    primary_key: tuple[tuple[str, object], ...]
    values: tuple[tuple[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "primary_key": dict(self.primary_key),
            "values": dict(self.values),
        }


@dataclass(frozen=True)
class CanonicalTable:
    name: str
    primary_key_columns: tuple[str, ...]
    rows: tuple[CanonicalRow, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "primary_key_columns": list(self.primary_key_columns),
            "rows": [row.as_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class CanonicalWorkspaceSnapshot:
    """All accepted Replay business tables in their approved fixed table order."""

    tables: tuple[CanonicalTable, ...]

    def as_dict(self) -> dict[str, object]:
        return {"tables": [table.as_dict() for table in self.tables]}

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


@dataclass(frozen=True)
class CanonicalDifference:
    table: str
    primary_key: tuple[tuple[str, object], ...] | None
    path: str
    run_a_value: object
    run_b_value: object


def canonicalize_value(value: Any) -> object:
    """Normalize a PostgreSQL value into an unambiguous type-tagged canonical form.

    Every supported source type maps to a tagged list whose first element is the
    type marker, so a source JSON value can never collide with a canonical value of
    a different type. The encoding is injective across all supported types: no two
    distinct source values of distinct types share a canonical representation.
    """

    if value is None:
        return ["null"]
    if isinstance(value, bool):
        # bool is a subclass of int; check it first to preserve the type.
        return ["bool", value]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, float):
        return ["float", value.hex()]
    if isinstance(value, Decimal):
        return ["decimal", str(value)]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise CanonicalizationError("datetime values must be timezone-aware")
        return ["datetime", value.astimezone(UTC).isoformat(timespec="microseconds")]
    if isinstance(value, Enum):
        return ["enum", canonicalize_value(value.value)]
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalizationError("JSON object keys must be strings")
        return [
            "object",
            [
                [key, canonicalize_value(value[key])]
                for key in sorted(value)
            ],
        ]
    if isinstance(value, (list, tuple)):
        return ["array", [canonicalize_value(item) for item in value]]
    raise CanonicalizationError(
        f"unsupported durable value type for canonicalization: {type(value).__name__}"
    )


async def capture_workspace_snapshot(
    engine: AsyncEngine, table_names: Sequence[str]
) -> CanonicalWorkspaceSnapshot:
    """Read all specified durable tables from one repeatable-read, read-only snapshot."""

    names = tuple(table_names)
    if not names:
        raise CanonicalizationError("canonical workspace table set must not be empty")
    if len(set(names)) != len(names):
        raise CanonicalizationError("canonical workspace table set contains duplicates")

    async with engine.connect() as connection, connection.begin():
        await connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        tables = []
        for table_name in names:
            tables.append(await _capture_table(connection, table_name))
    return CanonicalWorkspaceSnapshot(tables=tuple(tables))


async def _capture_table(connection: AsyncConnection, table_name: str) -> CanonicalTable:
    primary_key_columns = await connection.run_sync(
        lambda sync_connection: tuple(
            inspect(sync_connection).get_pk_constraint(table_name).get("constrained_columns") or ()
        )
    )
    if not primary_key_columns:
        raise CanonicalizationError(
            f"{table_name} has no PostgreSQL primary key for canonical row ordering"
        )

    quoted_table = _quote_identifier(table_name)
    quoted_primary_key = ", ".join(_quote_identifier(column) for column in primary_key_columns)
    result = await connection.execute(text(f"SELECT * FROM {quoted_table} ORDER BY {quoted_primary_key}"))
    rows = []
    for row in result.mappings():
        values = tuple(
            (column, canonicalize_value(row[column]))
            for column in sorted(row)
        )
        primary_key = tuple(
            (column, row[column])
            for column in primary_key_columns
        )
        rows.append(CanonicalRow(primary_key=primary_key, values=values))
    return CanonicalTable(
        name=table_name,
        primary_key_columns=primary_key_columns,
        rows=tuple(rows),
    )


def first_snapshot_difference(
    run_a: CanonicalWorkspaceSnapshot,
    run_b: CanonicalWorkspaceSnapshot,
    *,
    table_names: Sequence[str] | None = None,
) -> CanonicalDifference | None:
    """Return the first stable, acceptance-oriented durable-state mismatch."""

    allowed = set(table_names) if table_names is not None else None
    tables_b = {table.name: table for table in run_b.tables}
    for table_a in run_a.tables:
        if allowed is not None and table_a.name not in allowed:
            continue
        table_b = tables_b.pop(table_a.name, None)
        if table_b is None:
            return CanonicalDifference(table_a.name, None, "$table", table_a.as_dict(), None)
        difference = _first_table_difference(table_a, table_b)
        if difference is not None:
            return difference
    for table_b in run_b.tables:
        if table_b.name in tables_b and (allowed is None or table_b.name in allowed):
            return CanonicalDifference(table_b.name, None, "$table", None, table_b.as_dict())
    return None


def _first_table_difference(
    table_a: CanonicalTable, table_b: CanonicalTable
) -> CanonicalDifference | None:
    if table_a.primary_key_columns != table_b.primary_key_columns:
        return CanonicalDifference(
            table_a.name,
            None,
            "$primary_key_columns",
            table_a.primary_key_columns,
            table_b.primary_key_columns,
        )
    rows_b = {row.primary_key: row for row in table_b.rows}
    for row_a in table_a.rows:
        row_b = rows_b.pop(row_a.primary_key, None)
        if row_b is None:
            return CanonicalDifference(
                table_a.name,
                row_a.primary_key,
                "$row",
                row_a.as_dict(),
                None,
            )
        values_a = dict(row_a.values)
        values_b = dict(row_b.values)
        difference = _first_value_difference(values_a, values_b, "$values")
        if difference is not None:
            path, run_a_value, run_b_value = difference
            return CanonicalDifference(
                table_a.name,
                row_a.primary_key,
                path,
                run_a_value,
                run_b_value,
            )
    if rows_b:
        row_b = next(iter(rows_b.values()))
        return CanonicalDifference(table_a.name, row_b.primary_key, "$row", None, row_b.as_dict())
    return None


_TAGGED_SCALARS = frozenset(
    {"null", "bool", "int", "str", "float", "decimal", "datetime", "enum"}
)


def _tagged_kind(value: object) -> str | None:
    """Return the canonical type marker for a tagged list, or None for plain values."""
    if (
        isinstance(value, list)
        and value
        and isinstance(value[0], str)
        and value[0] in {"object", "array", *_TAGGED_SCALARS}
    ):
        return "scalar" if value[0] in _TAGGED_SCALARS else value[0]
    return None


def _first_value_difference(
    run_a: object, run_b: object, path: str
) -> tuple[str, object, object] | None:
    if type(run_a) is not type(run_b):
        return path, run_a, run_b
    if isinstance(run_a, dict):
        keys_a = set(run_a)
        keys_b = set(run_b)
        for key in sorted(keys_a | keys_b):
            next_path = f"{path}.{key}"
            if key not in run_a:
                return next_path, None, run_b[key]
            if key not in run_b:
                return next_path, run_a[key], None
            difference = _first_value_difference(run_a[key], run_b[key], next_path)
            if difference is not None:
                return difference
        return None
    if isinstance(run_a, list):
        kind_a = _tagged_kind(run_a)
        kind_b = _tagged_kind(run_b)
        if kind_a == "scalar" or kind_b == "scalar":
            # A tagged scalar is a leaf: compare it whole, keeping the semantic path.
            if run_a != run_b:
                return path, run_a, run_b
            return None
        if kind_a == "object" and kind_b == "object":
            pairs_a = {key: value for key, value in run_a[1]}
            pairs_b = {key: value for key, value in run_b[1]}
            for key in sorted(set(pairs_a) | set(pairs_b)):
                next_path = f"{path}.{key}"
                if key not in pairs_a:
                    return next_path, None, pairs_b[key]
                if key not in pairs_b:
                    return next_path, pairs_a[key], None
                difference = _first_value_difference(pairs_a[key], pairs_b[key], next_path)
                if difference is not None:
                    return difference
            return None
        if kind_a == "array" and kind_b == "array":
            items_a, items_b = run_a[1], run_b[1]
            if len(items_a) != len(items_b):
                return f"{path}.length", len(items_a), len(items_b)
            for index, (value_a, value_b) in enumerate(zip(items_a, items_b, strict=True)):
                difference = _first_value_difference(value_a, value_b, f"{path}[{index}]")
                if difference is not None:
                    return difference
            return None
        if len(run_a) != len(run_b):
            return f"{path}.length", len(run_a), len(run_b)
        for index, (value_a, value_b) in enumerate(zip(run_a, run_b, strict=True)):
            difference = _first_value_difference(value_a, value_b, f"{path}[{index}]")
            if difference is not None:
                return difference
        return None
    if run_a != run_b:
        return path, run_a, run_b
    return None


def _quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace("\"", "\"\"")}"'
