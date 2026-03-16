# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for file management tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from gedcom_mcp.server import AppContext, create_server
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools._errors import McpToolError


def _make_ctx(settings: Settings | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=settings or Settings())
    return ctx


def _find_tool(mcp: Any, name: str) -> Any:
    for tool in mcp._tool_manager._tools.values():
        if tool.name == name:
            return tool
    raise ValueError(f"Tool {name} not found")


@pytest.fixture
def mcp() -> Any:
    return create_server()


async def test_load_file_minimal(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    tool = _find_tool(mcp, "load_file")
    result = await tool.fn(ctx=ctx, file_path=str(fixtures_dir / "minimal.ged"))
    assert "Loaded: minimal.ged" in result
    assert "Individuals: 3" in result
    assert "Families: 1" in result
    app_ctx = ctx.request_context.lifespan_context
    assert app_ctx.database is not None


async def test_load_file_medium(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    tool = _find_tool(mcp, "load_file")
    result = await tool.fn(ctx=ctx, file_path=str(fixtures_dir / "medium.ged"))
    assert "Individuals: 15" in result
    assert "Families: 5" in result


async def test_load_file_relative_path(mcp: Any) -> None:
    ctx = _make_ctx()
    tool = _find_tool(mcp, "load_file")
    with pytest.raises(McpToolError, match="Path must be absolute"):
        await tool.fn(ctx=ctx, file_path="relative/path.ged")


async def test_load_file_wrong_extension(mcp: Any) -> None:
    ctx = _make_ctx()
    tool = _find_tool(mcp, "load_file")
    with pytest.raises(McpToolError, match="must have a .ged extension"):
        await tool.fn(ctx=ctx, file_path="/tmp/file.txt")


async def test_load_file_not_found(mcp: Any) -> None:
    ctx = _make_ctx()
    tool = _find_tool(mcp, "load_file")
    with pytest.raises(McpToolError, match="File not found"):
        await tool.fn(ctx=ctx, file_path="/tmp/nonexistent.ged")


async def test_load_file_outside_allowed_dirs(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(Settings(allowed_base_dirs="/some/other/dir"))
    tool = _find_tool(mcp, "load_file")
    with pytest.raises(McpToolError, match="outside allowed directories"):
        await tool.fn(ctx=ctx, file_path=str(fixtures_dir / "minimal.ged"))


async def test_load_file_replaces_previous(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    tool = _find_tool(mcp, "load_file")
    await tool.fn(ctx=ctx, file_path=str(fixtures_dir / "minimal.ged"))
    app_ctx = ctx.request_context.lifespan_context
    assert len(app_ctx.database.individuals) == 3

    await tool.fn(ctx=ctx, file_path=str(fixtures_dir / "empty.ged"))
    assert len(app_ctx.database.individuals) == 0
