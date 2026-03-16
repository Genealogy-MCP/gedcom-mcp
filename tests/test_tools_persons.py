# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for person tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from gedcom_mcp.parser import parse_file
from gedcom_mcp.server import AppContext, create_server
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools._errors import McpToolError


def _make_ctx(fixtures_dir: Path, fixture: str = "minimal.ged") -> MagicMock:
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


async def test_search_by_name(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "search_persons")
    result = await tool.fn(ctx=ctx, name="John")
    assert "@I1@" in result
    assert "John /Smith/" in result


async def test_search_by_surname(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "search_persons")
    result = await tool.fn(ctx=ctx, name="Smith")
    assert "@I1@" in result
    assert "@I3@" in result


async def test_search_by_sex(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "search_persons")
    result = await tool.fn(ctx=ctx, sex="F")
    assert "Mary" in result
    assert "John" not in result


async def test_search_by_place(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "search_persons")
    result = await tool.fn(ctx=ctx, place="Paris")
    assert "Mary" in result


async def test_search_by_birth_year_range(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "search_persons")
    result = await tool.fn(ctx=ctx, birth_year_min=1920, birth_year_max=1930)
    assert "James" in result
    assert "John" not in result


async def test_search_no_results(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "search_persons")
    result = await tool.fn(ctx=ctx, name="Nonexistent")
    assert "No individuals found" in result


async def test_search_no_database(mcp: Any) -> None:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=Settings())
    tool = _find_tool(mcp, "search_persons")
    with pytest.raises(McpToolError, match="No GEDCOM file is loaded"):
        await tool.fn(ctx=ctx, name="John")


async def test_get_person_detailed(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_person")
    result = await tool.fn(ctx=ctx, xref="@I1@", response_format="detailed")
    assert "John /Smith/" in result
    assert "1 JAN 1900" in result
    assert "London, England" in result


async def test_get_person_concise(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_person")
    result = await tool.fn(ctx=ctx, xref="@I1@", response_format="concise")
    assert "John /Smith/" in result
    assert "@F1@" in result


async def test_get_person_not_found(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_person")
    with pytest.raises(McpToolError, match="not found"):
        await tool.fn(ctx=ctx, xref="@I999@", response_format="detailed")


async def test_search_max_results(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    tool = _find_tool(mcp, "search_persons")
    result = await tool.fn(ctx=ctx, max_results=2)
    assert "showing first 2" in result


async def test_search_by_death_year_range(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    tool = _find_tool(mcp, "search_persons")
    result = await tool.fn(ctx=ctx, death_year_min=1920, death_year_max=1960)
    assert "Henry" in result
    assert "Alice" in result


async def test_get_person_detailed_with_notes_sources_events(mcp: Any) -> None:
    """Exercise detailed format: alternate names, other_events, notes, sources."""
    from gedcom_mcp.parser.models import (
        GedcomDatabase,
        GedcomDate,
        GedcomEvent,
        GedcomHeader,
        GedcomName,
        GedcomNote,
        GedcomPlace,
        GedcomSource,
        Individual,
    )

    db = GedcomDatabase(
        header=GedcomHeader(),
        individuals={
            "@I1@": Individual(
                xref="@I1@",
                names=[
                    GedcomName(full="John Smith", given="John", surname="Smith"),
                    GedcomName(full="Johnny Smith", given="Johnny", surname="Smith"),
                ],
                sex="M",
                birth=GedcomEvent(
                    event_type="BIRT",
                    date=GedcomDate(original="1 JAN 1900"),
                    place=GedcomPlace(name="London", parts=["London"]),
                ),
                death=GedcomEvent(
                    event_type="DEAT",
                    date=GedcomDate(original="5 MAR 1970"),
                    place=GedcomPlace(name="Oxford", parts=["Oxford"]),
                ),
                other_events=[
                    GedcomEvent(
                        event_type="OCCU",
                        date=GedcomDate(original="1925"),
                        place=GedcomPlace(name="London", parts=["London"]),
                        description="Teacher",
                    ),
                    GedcomEvent(event_type="RESI"),
                ],
                note_xrefs=["@N1@"],
                source_xrefs=["@S1@"],
            ),
        },
        families={},
        sources={"@S1@": GedcomSource(xref="@S1@", title="Parish Records")},
        notes={"@N1@": GedcomNote(xref="@N1@", text="Important person in the town.")},
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=Settings(), database=db)
    tool = _find_tool(mcp, "get_person")
    result = await tool.fn(ctx=ctx, xref="@I1@", response_format="detailed")
    assert "Alternate names: Johnny Smith" in result
    assert "OCCU: 1925, London (Teacher)" in result
    assert "RESI: no date" in result
    assert "Note: Important person in the town." in result
    assert "Source: Parish Records" in result
    assert "Death: 5 MAR 1970, Oxford" in result
