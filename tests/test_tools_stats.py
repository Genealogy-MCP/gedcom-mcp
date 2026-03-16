# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for stats tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from gedcom_mcp.parser import parse_file
from gedcom_mcp.server import AppContext, create_server
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools._errors import McpToolError


def _make_ctx(fixtures_dir: Path, fixture: str = "medium.ged") -> MagicMock:
    raw = (fixtures_dir / fixture).read_bytes()
    db = parse_file(raw)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=Settings(), database=db)
    return ctx


def _find_tool(mcp: Any, name: str) -> Any:
    for tool in mcp._tool_manager._tools.values():
        if tool.name == name:
            return tool
    raise ValueError(f"Tool {name} not found")


@pytest.fixture
def mcp() -> Any:
    return create_server()


async def test_get_stats_medium(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_stats")
    result = await tool.fn(ctx=ctx)
    assert "GEDCOM Statistics" in result
    assert "Individuals: 15" in result
    assert "Families: 5" in result
    assert "Sources: 1" in result
    assert "Notes: 1" in result


async def test_get_stats_sex_distribution(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_stats")
    result = await tool.fn(ctx=ctx)
    assert "Sex Distribution:" in result
    assert "M:" in result
    assert "F:" in result


async def test_get_stats_surnames(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_stats")
    result = await tool.fn(ctx=ctx)
    assert "Top 10 Surnames:" in result
    assert "Adams:" in result


async def test_get_stats_year_ranges(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_stats")
    result = await tool.fn(ctx=ctx)
    assert "Birth Year Range:" in result
    assert "1800" in result


async def test_get_stats_data_quality(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_stats")
    result = await tool.fn(ctx=ctx)
    assert "Data Quality:" in result
    assert "With birth event:" in result
    assert "With name:" in result


async def test_get_stats_empty(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "empty.ged")
    tool = _find_tool(mcp, "get_stats")
    result = await tool.fn(ctx=ctx)
    assert "Individuals: 0" in result
    assert "Families: 0" in result


async def test_get_stats_no_database(mcp: Any) -> None:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=Settings())
    tool = _find_tool(mcp, "get_stats")
    with pytest.raises(McpToolError, match="No GEDCOM file is loaded"):
        await tool.fn(ctx=ctx)
