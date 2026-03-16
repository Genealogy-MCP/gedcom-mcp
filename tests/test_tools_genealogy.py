# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for genealogy traversal tools."""

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


async def test_get_ancestors(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_ancestors")
    result = await tool.fn(ctx=ctx, xref="@I9@", max_generations=5)
    assert "Ancestors of" in result
    assert "Thomas /Adams/" in result
    assert "Generation 1" in result
    assert "Robert /Adams/" in result


async def test_get_ancestors_full_chain(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_ancestors")
    result = await tool.fn(ctx=ctx, xref="@I9@", max_generations=10)
    assert "William /Adams/" in result
    assert "Elizabeth /Brown/" in result


async def test_get_ancestors_no_parents(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_ancestors")
    result = await tool.fn(ctx=ctx, xref="@I1@", max_generations=5)
    assert "No ancestors found" in result


async def test_get_ancestors_not_found(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_ancestors")
    with pytest.raises(McpToolError, match="not found"):
        await tool.fn(ctx=ctx, xref="@I999@", max_generations=5)


async def test_get_descendants(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_descendants")
    result = await tool.fn(ctx=ctx, xref="@I1@", max_generations=5)
    assert "Descendants of" in result
    assert "George /Adams/" in result


async def test_get_descendants_full_chain(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_descendants")
    result = await tool.fn(ctx=ctx, xref="@I1@", max_generations=10)
    assert "Thomas /Adams/" in result


async def test_get_descendants_no_children(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_descendants")
    result = await tool.fn(ctx=ctx, xref="@I9@", max_generations=5)
    assert "No descendants found" in result


async def test_get_descendants_not_found(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_descendants")
    with pytest.raises(McpToolError, match="not found"):
        await tool.fn(ctx=ctx, xref="@I999@", max_generations=5)


async def test_ancestors_default_depth(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_ancestors")
    result = await tool.fn(ctx=ctx, xref="@I9@")
    assert "up to 5 generations" in result


async def test_descendants_capped_by_max(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_descendants")
    result = await tool.fn(ctx=ctx, xref="@I1@", max_generations=1)
    assert "up to 1 generations" in result
    assert "George /Adams/" in result
    assert "Thomas /Adams/" not in result
