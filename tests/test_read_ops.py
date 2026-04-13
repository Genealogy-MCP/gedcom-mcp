# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Tests for read operation handlers: get_person, get_family."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gedcom_mcp.operations import GetFamilyParams, GetPersonParams
from gedcom_mcp.parser import parse_file
from gedcom_mcp.parser.models import (
    Family,
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
from gedcom_mcp.server import AppContext
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools._errors import McpToolError
from gedcom_mcp.tools.read_ops import handle_get_family, handle_get_person


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


# ---------------------------------------------------------------------------
# get_person
# ---------------------------------------------------------------------------


async def test_handle_get_person_detailed(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(
        await handle_get_person(ctx, GetPersonParams(xref="@I1@", response_format="detailed"))
    )
    assert "John /Smith/" in result
    assert "1 JAN 1900" in result
    assert "London, England" in result


async def test_handle_get_person_concise(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(
        await handle_get_person(ctx, GetPersonParams(xref="@I1@", response_format="concise"))
    )
    assert "John /Smith/" in result
    assert "@F1@" in result


async def test_handle_get_person_not_found(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    with pytest.raises(McpToolError, match="not found"):
        await handle_get_person(ctx, GetPersonParams(xref="@I999@", response_format="detailed"))


async def test_handle_get_person_detailed_with_notes_sources_events() -> None:
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
    result = _text(
        await handle_get_person(ctx, GetPersonParams(xref="@I1@", response_format="detailed"))
    )
    assert "Alternate names: Johnny Smith" in result
    assert "OCCU: 1925, London (Teacher)" in result
    assert "RESI: no date" in result
    assert "Note: Important person in the town." in result
    assert "Source: Parish Records" in result
    assert "Death: 5 MAR 1970, Oxford" in result


# ---------------------------------------------------------------------------
# get_family
# ---------------------------------------------------------------------------


async def test_handle_get_family_by_fam_xref(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(
        await handle_get_family(ctx, GetFamilyParams(xref="@F1@", response_format="detailed"))
    )
    assert "Family @F1@" in result
    assert "John /Smith/" in result
    assert "Mary /Jones/" in result
    assert "James /Smith/" in result


async def test_handle_get_family_by_indi_xref(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(
        await handle_get_family(ctx, GetFamilyParams(xref="@I1@", response_format="concise"))
    )
    assert "Family @F1@" in result
    assert "Husband" in result


async def test_handle_get_family_indi_not_spouse(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(
        await handle_get_family(ctx, GetFamilyParams(xref="@I3@", response_format="detailed"))
    )
    assert "not a spouse" in result


async def test_handle_get_family_not_found(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    with pytest.raises(McpToolError, match="not found"):
        await handle_get_family(ctx, GetFamilyParams(xref="@F999@", response_format="detailed"))


async def test_handle_get_family_concise_format(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = _text(
        await handle_get_family(ctx, GetFamilyParams(xref="@F1@", response_format="concise"))
    )
    assert "Marriage:" in result
    assert "10 JUN 1924" in result


async def test_handle_get_family_detailed_with_divorce_notes_sources() -> None:
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
    result = _text(
        await handle_get_family(ctx, GetFamilyParams(xref="@F1@", response_format="detailed"))
    )
    assert "Divorce: 5 MAR 1910, London" in result
    assert "CENS: 1901, England" in result
    assert "Note: Family was prominent." in result
    assert "Source: Parish Records" in result


async def test_handle_get_family_person_label_no_name() -> None:
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
    result = _text(
        await handle_get_family(ctx, GetFamilyParams(xref="@F1@", response_format="concise"))
    )
    assert "Husband: @I1@" in result
    assert "- @I1@" in result
