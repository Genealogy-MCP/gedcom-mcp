# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for handler functions called directly (no MCP framework)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
from gedcom_mcp.tools._handlers import (
    handle_get_ancestors,
    handle_get_descendants,
    handle_get_family,
    handle_get_person,
    handle_get_stats,
    handle_load_file,
    handle_search_persons,
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


# ---------------------------------------------------------------------------
# load_file
# ---------------------------------------------------------------------------


async def test_handle_load_file(fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    result = await handle_load_file(ctx, file_path=str(fixtures_dir / "minimal.ged"))
    assert "Loaded: minimal.ged" in result
    assert "Individuals: 3" in result
    assert "Families: 1" in result
    assert ctx.request_context.lifespan_context.database is not None


async def test_handle_load_file_medium(fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    result = await handle_load_file(ctx, file_path=str(fixtures_dir / "medium.ged"))
    assert "Individuals: 15" in result
    assert "Families: 5" in result


async def test_handle_load_file_relative_path() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="Path must be absolute"):
        await handle_load_file(ctx, file_path="relative/path.ged")


async def test_handle_load_file_wrong_extension() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="must have a .ged extension"):
        await handle_load_file(ctx, file_path="/tmp/file.txt")


async def test_handle_load_file_not_found() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="File not found"):
        await handle_load_file(ctx, file_path="/tmp/nonexistent.ged")


async def test_handle_load_file_outside_allowed_dirs(fixtures_dir: Path) -> None:
    ctx = _make_ctx(settings=Settings(allowed_base_dirs="/some/other/dir"))
    with pytest.raises(McpToolError, match="outside allowed directories"):
        await handle_load_file(ctx, file_path=str(fixtures_dir / "minimal.ged"))


async def test_handle_load_file_replaces_previous(fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    await handle_load_file(ctx, file_path=str(fixtures_dir / "minimal.ged"))
    app_ctx = ctx.request_context.lifespan_context
    assert len(app_ctx.database.individuals) == 3

    await handle_load_file(ctx, file_path=str(fixtures_dir / "empty.ged"))
    assert len(app_ctx.database.individuals) == 0


# ---------------------------------------------------------------------------
# search_persons
# ---------------------------------------------------------------------------


async def test_handle_search_by_name(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_search_persons(ctx, name="John")
    assert "@I1@" in result
    assert "John /Smith/" in result


async def test_handle_search_by_surname(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_search_persons(ctx, name="Smith")
    assert "@I1@" in result
    assert "@I3@" in result


async def test_handle_search_by_sex(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_search_persons(ctx, sex="F")
    assert "Mary" in result
    assert "John" not in result


async def test_handle_search_by_place(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_search_persons(ctx, place="Paris")
    assert "Mary" in result


async def test_handle_search_by_birth_year_range(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_search_persons(ctx, birth_year_min=1920, birth_year_max=1930)
    assert "James" in result
    assert "John" not in result


async def test_handle_search_no_results(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_search_persons(ctx, name="Nonexistent")
    assert "No individuals found" in result


async def test_handle_search_no_database() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="No GEDCOM file is loaded"):
        await handle_search_persons(ctx, name="John")


async def test_handle_search_max_results(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_search_persons(ctx, max_results=2)
    assert "showing first 2" in result


async def test_handle_search_by_death_year_range(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_search_persons(ctx, death_year_min=1920, death_year_max=1960)
    assert "Henry" in result
    assert "Alice" in result


# ---------------------------------------------------------------------------
# get_person
# ---------------------------------------------------------------------------


async def test_handle_get_person_detailed(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_get_person(ctx, xref="@I1@", response_format="detailed")
    assert "John /Smith/" in result
    assert "1 JAN 1900" in result
    assert "London, England" in result


async def test_handle_get_person_concise(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_get_person(ctx, xref="@I1@", response_format="concise")
    assert "John /Smith/" in result
    assert "@F1@" in result


async def test_handle_get_person_not_found(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    with pytest.raises(McpToolError, match="not found"):
        await handle_get_person(ctx, xref="@I999@", response_format="detailed")


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
    result = await handle_get_person(ctx, xref="@I1@", response_format="detailed")
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
    result = await handle_get_family(ctx, xref="@F1@", response_format="detailed")
    assert "Family @F1@" in result
    assert "John /Smith/" in result
    assert "Mary /Jones/" in result
    assert "James /Smith/" in result


async def test_handle_get_family_by_indi_xref(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_get_family(ctx, xref="@I1@", response_format="concise")
    assert "Family @F1@" in result
    assert "Husband" in result


async def test_handle_get_family_indi_not_spouse(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_get_family(ctx, xref="@I3@", response_format="detailed")
    assert "not a spouse" in result


async def test_handle_get_family_not_found(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    with pytest.raises(McpToolError, match="not found"):
        await handle_get_family(ctx, xref="@F999@", response_format="detailed")


async def test_handle_get_family_concise_format(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir)
    result = await handle_get_family(ctx, xref="@F1@", response_format="concise")
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
    result = await handle_get_family(ctx, xref="@F1@", response_format="detailed")
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
    result = await handle_get_family(ctx, xref="@F1@", response_format="concise")
    assert "Husband: @I1@" in result
    assert "- @I1@" in result


# ---------------------------------------------------------------------------
# get_ancestors
# ---------------------------------------------------------------------------


async def test_handle_get_ancestors(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_ancestors(ctx, xref="@I9@", max_generations=5)
    assert "Ancestors of" in result
    assert "Thomas /Adams/" in result
    assert "Generation 1" in result
    assert "Robert /Adams/" in result


async def test_handle_get_ancestors_full_chain(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_ancestors(ctx, xref="@I9@", max_generations=10)
    assert "William /Adams/" in result
    assert "Elizabeth /Brown/" in result


async def test_handle_get_ancestors_no_parents(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_ancestors(ctx, xref="@I1@", max_generations=5)
    assert "No ancestors found" in result


async def test_handle_get_ancestors_not_found(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    with pytest.raises(McpToolError, match="not found"):
        await handle_get_ancestors(ctx, xref="@I999@", max_generations=5)


async def test_handle_ancestors_default_depth(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_ancestors(ctx, xref="@I9@")
    assert "up to 5 generations" in result


# ---------------------------------------------------------------------------
# get_descendants
# ---------------------------------------------------------------------------


async def test_handle_get_descendants(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_descendants(ctx, xref="@I1@", max_generations=5)
    assert "Descendants of" in result
    assert "George /Adams/" in result


async def test_handle_get_descendants_full_chain(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_descendants(ctx, xref="@I1@", max_generations=10)
    assert "Thomas /Adams/" in result


async def test_handle_get_descendants_no_children(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_descendants(ctx, xref="@I9@", max_generations=5)
    assert "No descendants found" in result


async def test_handle_get_descendants_not_found(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    with pytest.raises(McpToolError, match="not found"):
        await handle_get_descendants(ctx, xref="@I999@", max_generations=5)


async def test_handle_descendants_capped_by_max(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_descendants(ctx, xref="@I1@", max_generations=1)
    assert "up to 1 generations" in result
    assert "George /Adams/" in result
    assert "Thomas /Adams/" not in result


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


async def test_handle_get_stats_medium(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_stats(ctx)
    assert "GEDCOM Statistics" in result
    assert "Individuals: 15" in result
    assert "Families: 5" in result
    assert "Sources: 1" in result
    assert "Notes: 1" in result


async def test_handle_get_stats_sex_distribution(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_stats(ctx)
    assert "Sex Distribution:" in result
    assert "M:" in result
    assert "F:" in result


async def test_handle_get_stats_surnames(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_stats(ctx)
    assert "Top 10 Surnames:" in result
    assert "Adams:" in result


async def test_handle_get_stats_year_ranges(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_stats(ctx)
    assert "Birth Year Range:" in result
    assert "1800" in result


async def test_handle_get_stats_data_quality(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "medium.ged")
    result = await handle_get_stats(ctx)
    assert "Data Quality:" in result
    assert "With birth event:" in result
    assert "With name:" in result


async def test_handle_get_stats_empty(fixtures_dir: Path) -> None:
    ctx = _make_ctx(fixtures_dir, "empty.ged")
    result = await handle_get_stats(ctx)
    assert "Individuals: 0" in result
    assert "Families: 0" in result


async def test_handle_get_stats_no_database() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="No GEDCOM file is loaded"):
        await handle_get_stats(ctx)
