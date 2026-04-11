# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Tests for the execute meta-tool via FastMCP."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from mcp.types import TextContent

from gedcom_mcp.parser import parse_file
from gedcom_mcp.server import AppContext, create_server
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools._errors import McpToolError


def _find_tool(mcp: Any, name: str) -> Any:
    """Extract a registered tool from FastMCP by name."""
    for tool in mcp._tool_manager._tools.values():
        if tool.name == name:
            return tool
    raise ValueError(f"Tool {name} not found")


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


def _extract_text(result: Any) -> str:
    """Extract text from tool result (handles str or list[TextContent])."""
    if isinstance(result, str):
        return result
    if isinstance(result, list) and result and isinstance(result[0], TextContent):
        return "\n".join(item.text for item in result)
    return str(result)


@pytest.fixture
def mcp() -> Any:
    return create_server()


# ---------------------------------------------------------------------------
# Basic dispatch
# ---------------------------------------------------------------------------


async def test_execute_tool_registered(mcp: Any) -> None:
    tool = _find_tool(mcp, "execute")
    assert tool is not None


async def test_execute_unknown_operation(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "execute")
    with pytest.raises(McpToolError, match="Unknown operation 'nonexistent'"):
        await tool.fn(ctx=ctx, operation="nonexistent")


async def test_execute_unknown_operation_suggests_close_match(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "execute")
    with pytest.raises(McpToolError, match="Did you mean"):
        await tool.fn(ctx=ctx, operation="get_perosn")


async def test_execute_invalid_params(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "execute")
    with pytest.raises(McpToolError, match="file_path"):
        await tool.fn(ctx=ctx, operation="load_file", params={})


async def test_execute_requires_database(mcp: Any) -> None:
    ctx = _make_ctx()
    tool = _find_tool(mcp, "execute")
    with pytest.raises(McpToolError, match="No GEDCOM file is loaded"):
        await tool.fn(ctx=ctx, operation="search_persons", params={"name": "John"})


async def test_execute_load_file_no_database_check(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    tool = _find_tool(mcp, "execute")
    result = _extract_text(
        await tool.fn(
            ctx=ctx,
            operation="load_file",
            params={"file_path": str(fixtures_dir / "minimal.ged")},
        )
    )
    assert "Loaded: minimal.ged" in result


# ---------------------------------------------------------------------------
# Happy paths for each operation
# ---------------------------------------------------------------------------


async def test_execute_search_persons(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "execute")
    result = _extract_text(
        await tool.fn(ctx=ctx, operation="search_persons", params={"name": "John"})
    )
    assert "@I1@" in result
    assert "John /Smith/" in result


async def test_execute_get_person(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "execute")
    result = _extract_text(await tool.fn(ctx=ctx, operation="get_person", params={"xref": "@I1@"}))
    assert "John /Smith/" in result


async def test_execute_get_person_concise(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "execute")
    result = _extract_text(
        await tool.fn(
            ctx=ctx,
            operation="get_person",
            params={"xref": "@I1@", "response_format": "concise"},
        )
    )
    assert "John /Smith/" in result
    assert "@F1@" in result


async def test_execute_get_family(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "execute")
    result = _extract_text(await tool.fn(ctx=ctx, operation="get_family", params={"xref": "@F1@"}))
    assert "Family @F1@" in result


async def test_execute_get_ancestors(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    tool = _find_tool(mcp, "execute")
    result = _extract_text(
        await tool.fn(
            ctx=ctx,
            operation="get_ancestors",
            params={"xref": "@I9@", "max_generations": 5},
        )
    )
    assert "Ancestors of" in result
    assert "Thomas /Adams/" in result


async def test_execute_get_descendants(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    tool = _find_tool(mcp, "execute")
    result = _extract_text(
        await tool.fn(
            ctx=ctx,
            operation="get_descendants",
            params={"xref": "@I1@", "max_generations": 5},
        )
    )
    assert "Descendants of" in result
    assert "George /Adams/" in result


async def test_execute_get_stats(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    tool = _find_tool(mcp, "execute")
    result = _extract_text(await tool.fn(ctx=ctx, operation="get_stats"))
    assert "GEDCOM Statistics" in result
    assert "Individuals: 15" in result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


async def test_execute_none_params_defaults_to_empty(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    tool = _find_tool(mcp, "execute")
    result = _extract_text(await tool.fn(ctx=ctx, operation="get_stats", params=None))
    assert "GEDCOM Statistics" in result


async def test_execute_search_persons_empty_params(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "execute")
    result = _extract_text(await tool.fn(ctx=ctx, operation="search_persons", params={}))
    assert "Found" in result


async def test_execute_validation_error_detail(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "execute")
    with pytest.raises(McpToolError, match="birth_year_min"):
        await tool.fn(
            ctx=ctx,
            operation="search_persons",
            params={"birth_year_min": "not_a_number"},
        )
