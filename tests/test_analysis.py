# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Tests for analysis operation handlers: get_ancestors, get_descendants, get_stats."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gedcom_mcp.parser import parse_file
from gedcom_mcp.server import AppContext
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools._errors import McpToolError
from gedcom_mcp.tools.analysis import (
    handle_get_ancestors,
    handle_get_descendants,
    handle_get_stats,
)


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


def _text(result: list) -> str:
    """Extract text from list[TextContent]."""
    return "\n".join(item.text for item in result)


# ---------------------------------------------------------------------------
# get_ancestors
# ---------------------------------------------------------------------------


async def test_handle_get_ancestors(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_ancestors(ctx, xref="@I9@", max_generations=5))
    assert "Ancestors of" in result
    assert "Thomas /Adams/" in result
    assert "Generation 1" in result
    assert "Robert /Adams/" in result


async def test_handle_get_ancestors_full_chain(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_ancestors(ctx, xref="@I9@", max_generations=10))
    assert "William /Adams/" in result
    assert "Elizabeth /Brown/" in result


async def test_handle_get_ancestors_no_parents(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_ancestors(ctx, xref="@I1@", max_generations=5))
    assert "No ancestors found" in result


async def test_handle_get_ancestors_not_found(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    with pytest.raises(McpToolError, match="not found"):
        await handle_get_ancestors(ctx, xref="@I999@", max_generations=5)


async def test_handle_ancestors_default_depth(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_ancestors(ctx, xref="@I9@"))
    assert "up to 5 generations" in result


# ---------------------------------------------------------------------------
# get_descendants
# ---------------------------------------------------------------------------


async def test_handle_get_descendants(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_descendants(ctx, xref="@I1@", max_generations=5))
    assert "Descendants of" in result
    assert "George /Adams/" in result


async def test_handle_get_descendants_full_chain(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_descendants(ctx, xref="@I1@", max_generations=10))
    assert "Thomas /Adams/" in result


async def test_handle_get_descendants_no_children(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_descendants(ctx, xref="@I9@", max_generations=5))
    assert "No descendants found" in result


async def test_handle_get_descendants_not_found(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    with pytest.raises(McpToolError, match="not found"):
        await handle_get_descendants(ctx, xref="@I999@", max_generations=5)


async def test_handle_descendants_capped_by_max(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_descendants(ctx, xref="@I1@", max_generations=1))
    assert "up to 1 generations" in result
    assert "George /Adams/" in result
    assert "Thomas /Adams/" not in result


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


async def test_handle_get_stats_medium(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_stats(ctx))
    assert "GEDCOM Statistics" in result
    assert "Individuals: 15" in result
    assert "Families: 5" in result
    assert "Sources: 1" in result
    assert "Notes: 1" in result


async def test_handle_get_stats_sex_distribution(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_stats(ctx))
    assert "Sex Distribution:" in result
    assert "M:" in result
    assert "F:" in result


async def test_handle_get_stats_surnames(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_stats(ctx))
    assert "Top 10 Surnames:" in result
    assert "Adams:" in result


async def test_handle_get_stats_year_ranges(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_stats(ctx))
    assert "Birth Year Range:" in result
    assert "1800" in result


async def test_handle_get_stats_data_quality(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = _text(await handle_get_stats(ctx))
    assert "Data Quality:" in result
    assert "With birth event:" in result
    assert "With name:" in result


async def test_handle_get_stats_empty(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "empty.ged")
    result = _text(await handle_get_stats(ctx))
    assert "Individuals: 0" in result
    assert "Families: 0" in result


async def test_handle_get_stats_no_database() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="No GEDCOM file is loaded"):
        await handle_get_stats(ctx)
