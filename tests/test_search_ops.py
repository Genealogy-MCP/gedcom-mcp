# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Tests for the search_persons handler (search category)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gedcom_mcp.operations import SearchPersonsParams
from gedcom_mcp.parser import parse_file
from gedcom_mcp.server import AppContext
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools._errors import McpToolError
from gedcom_mcp.tools.search_ops import handle_search_persons


def _make_ctx(
    fixtures_dir: Path | None = None,
    fixture: str = "minimal.ged",
    settings: Settings | None = None,
) -> MagicMock:
    """Build a mock context with an optionally pre-loaded database."""
    s = settings or Settings()
    db = None
    if fixtures_dir is not None:
        raw = (fixtures_dir / fixture).read_bytes()
        db = parse_file(raw)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=s, database=db)
    return ctx


def _text(result: list) -> str:  # type: ignore[type-arg]
    """Extract text from list[TextContent]."""
    return "\n".join(item.text for item in result)


async def test_handle_search_by_name(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(await handle_search_persons(ctx, SearchPersonsParams(name="John")))
    assert "@I1@" in result
    assert "John /Smith/" in result


async def test_handle_search_by_surname(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(await handle_search_persons(ctx, SearchPersonsParams(name="Smith")))
    assert "@I1@" in result
    assert "@I3@" in result


async def test_handle_search_by_sex(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(await handle_search_persons(ctx, SearchPersonsParams(sex="F")))
    assert "Mary" in result
    assert "John" not in result


async def test_handle_search_by_place(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(await handle_search_persons(ctx, SearchPersonsParams(place="Paris")))
    assert "Mary" in result


async def test_handle_search_by_birth_year_range(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(
        await handle_search_persons(
            ctx, SearchPersonsParams(birth_year_min=1920, birth_year_max=1930)
        )
    )
    assert "James" in result
    assert "John" not in result


async def test_handle_search_no_results(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(await handle_search_persons(ctx, SearchPersonsParams(name="Nonexistent")))
    assert "No individuals found" in result


async def test_handle_search_no_database() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="No GEDCOM file is loaded"):
        await handle_search_persons(ctx, SearchPersonsParams(name="John"))


async def test_handle_search_max_results(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_search_persons(ctx, SearchPersonsParams(max_results=2)))
    assert "showing first 2" in result


async def test_handle_search_by_death_year_range(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(
        await handle_search_persons(
            ctx, SearchPersonsParams(death_year_min=1920, death_year_max=1960)
        )
    )
    assert "Henry" in result
    assert "Alice" in result
