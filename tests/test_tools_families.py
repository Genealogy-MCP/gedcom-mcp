# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for family tools."""

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


async def test_get_family_by_fam_xref(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_family")
    result = await tool.fn(ctx=ctx, xref="@F1@", response_format="detailed")
    assert "Family @F1@" in result
    assert "John /Smith/" in result
    assert "Mary /Jones/" in result
    assert "James /Smith/" in result


async def test_get_family_by_indi_xref(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_family")
    result = await tool.fn(ctx=ctx, xref="@I1@", response_format="concise")
    assert "Family @F1@" in result
    assert "Husband" in result


async def test_get_family_indi_not_spouse(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_family")
    result = await tool.fn(ctx=ctx, xref="@I3@", response_format="detailed")
    assert "not a spouse" in result


async def test_get_family_not_found(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_family")
    with pytest.raises(McpToolError, match="not found"):
        await tool.fn(ctx=ctx, xref="@F999@", response_format="detailed")


async def test_get_family_concise_format(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    tool = _find_tool(mcp, "get_family")
    result = await tool.fn(ctx=ctx, xref="@F1@", response_format="concise")
    assert "Marriage:" in result
    assert "10 JUN 1924" in result


async def test_get_family_medium_multiple(mcp: Any, fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    tool = _find_tool(mcp, "get_family")
    result = await tool.fn(ctx=ctx, xref="@F1@", response_format="detailed")
    assert "Children:" in result


async def test_get_family_detailed_with_divorce_notes_sources(mcp: Any) -> None:
    """Exercise detailed format paths: divorce, other_events, notes, sources."""
    from gedcom_mcp.parser.models import (
        Family,
        GedcomDatabase,
        GedcomDate,
        GedcomEvent,
        GedcomHeader,
        GedcomNote,
        GedcomPlace,
        GedcomSource,
        Individual,
    )

    db = GedcomDatabase(
        header=GedcomHeader(),
        individuals={
            "@I1@": Individual(xref="@I1@"),
            "@I2@": Individual(xref="@I2@"),
        },
        families={
            "@F1@": Family(
                xref="@F1@",
                husband_xref="@I1@",
                wife_xref="@I2@",
                marriage=GedcomEvent(
                    event_type="MARR",
                    date=GedcomDate(original="1 JAN 1900"),
                    place=GedcomPlace(name="London", parts=["London"]),
                ),
                divorce=GedcomEvent(
                    event_type="DIV",
                    date=GedcomDate(original="5 MAR 1910"),
                    place=GedcomPlace(name="London", parts=["London"]),
                ),
                other_events=[
                    GedcomEvent(
                        event_type="CENS",
                        date=GedcomDate(original="1901"),
                        place=GedcomPlace(name="England", parts=["England"]),
                    ),
                ],
                note_xrefs=["@N1@"],
                source_xrefs=["@S1@"],
            ),
        },
        sources={"@S1@": GedcomSource(xref="@S1@", title="Parish Records")},
        notes={"@N1@": GedcomNote(xref="@N1@", text="Family was prominent.")},
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=Settings(), database=db)
    tool = _find_tool(mcp, "get_family")
    result = await tool.fn(ctx=ctx, xref="@F1@", response_format="detailed")
    assert "Divorce: 5 MAR 1910, London" in result
    assert "CENS: 1901, England" in result
    assert "Note: Family was prominent." in result
    assert "Source: Parish Records" in result


async def test_get_family_person_label_no_name(mcp: Any) -> None:
    """_person_label returns xref when individual has no names."""
    from gedcom_mcp.parser.models import (
        Family,
        GedcomDatabase,
        GedcomHeader,
        Individual,
    )

    db = GedcomDatabase(
        header=GedcomHeader(),
        individuals={"@I1@": Individual(xref="@I1@")},
        families={
            "@F1@": Family(xref="@F1@", husband_xref="@I1@", children_xrefs=["@I1@"]),
        },
        sources={},
        notes={},
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=Settings(), database=db)
    tool = _find_tool(mcp, "get_family")
    result = await tool.fn(ctx=ctx, xref="@F1@", response_format="concise")
    assert "Husband: @I1@" in result
    assert "- @I1@" in result
