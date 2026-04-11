# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for the search meta-tool via FastMCP."""

from __future__ import annotations

from typing import Any

from mcp.types import TextContent

from gedcom_mcp.server import create_server


def _find_tool(mcp: Any, name: str) -> Any:
    """Extract a registered tool from FastMCP by name."""
    for tool in mcp._tool_manager._tools.values():
        if tool.name == name:
            return tool
    raise ValueError(f"Tool {name} not found")


def _extract_text(result: Any) -> str:
    """Extract text from tool result (handles str or list[TextContent])."""
    if isinstance(result, str):
        return result
    if isinstance(result, list) and result and isinstance(result[0], TextContent):
        return "\n".join(item.text for item in result)
    return str(result)


async def test_search_tool_registered() -> None:
    mcp = create_server()
    tool = _find_tool(mcp, "search")
    assert tool is not None


async def test_search_empty_query_returns_all() -> None:
    mcp = create_server()
    tool = _find_tool(mcp, "search")
    result = _extract_text(await tool.fn(query=""))
    assert "load_file" in result
    assert "search_persons" in result
    assert "get_person" in result
    assert "get_family" in result
    assert "get_ancestors" in result
    assert "get_descendants" in result
    assert "get_stats" in result


async def test_search_specific_query() -> None:
    mcp = create_server()
    tool = _find_tool(mcp, "search")
    result = _extract_text(await tool.fn(query="ancestor"))
    assert "get_ancestors" in result


async def test_search_no_match() -> None:
    mcp = create_server()
    tool = _find_tool(mcp, "search")
    result = _extract_text(await tool.fn(query="zzzznonexistentzzzz"))
    assert "No operations found" in result


async def test_search_result_contains_params() -> None:
    mcp = create_server()
    tool = _find_tool(mcp, "search")
    result = _extract_text(await tool.fn(query="search person"))
    assert "name" in result
    assert "birth_year_min" in result


async def test_search_shows_category() -> None:
    mcp = create_server()
    tool = _find_tool(mcp, "search")
    result = _extract_text(await tool.fn(query="load"))
    assert "[setup]" in result


async def test_search_with_category_filter() -> None:
    mcp = create_server()
    tool = _find_tool(mcp, "search")
    result = _extract_text(await tool.fn(query="", category="analysis"))
    assert "get_ancestors" in result
    assert "get_descendants" in result
    assert "get_stats" in result
    assert "load_file" not in result


async def test_search_shows_token_warning() -> None:
    mcp = create_server()
    tool = _find_tool(mcp, "search")
    result = _extract_text(await tool.fn(query="search_persons"))
    assert "token-heavy" in result or "Note:" in result
