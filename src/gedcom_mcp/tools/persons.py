# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Person search and retrieval tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.parser.models import GedcomDatabase, Individual
from gedcom_mcp.tools._errors import (
    McpToolError,
    get_app_context,
    raise_tool_error,
    require_database,
)


def _matches_name(indi: Individual, query: str) -> bool:
    """Check if any of the individual's names match the query (case-insensitive)."""
    q = query.lower()
    return any(
        q in name.full.lower()
        or (name.given and q in name.given.lower())
        or (name.surname and q in name.surname.lower())
        for name in indi.names
    )


def _matches_place(indi: Individual, query: str) -> bool:
    """Check if any event place matches the query (case-insensitive)."""
    q = query.lower()
    events = [indi.birth, indi.death, *indi.other_events]
    return any(evt and evt.place and q in evt.place.name.lower() for evt in events)


def _matches_year_range(
    indi: Individual,
    birth_min: int | None,
    birth_max: int | None,
    death_min: int | None,
    death_max: int | None,
) -> bool:
    """Check if individual's birth/death years fall within ranges."""
    if birth_min is not None or birth_max is not None:
        if not indi.birth or not indi.birth.date or not indi.birth.date.year:
            return False
        year = indi.birth.date.year
        if birth_min is not None and year < birth_min:
            return False
        if birth_max is not None and year > birth_max:
            return False

    if death_min is not None or death_max is not None:
        if not indi.death or not indi.death.date or not indi.death.date.year:
            return False
        year = indi.death.date.year
        if death_min is not None and year < death_min:
            return False
        if death_max is not None and year > death_max:
            return False

    return True


def _format_person_concise(indi: Individual, db: GedcomDatabase) -> str:
    """Format a person with name, vital dates, and family links."""
    name = indi.names[0].full if indi.names else "Unknown"
    parts = [f"{indi.xref}: {name}"]

    if indi.sex:
        parts.append(f"  Sex: {indi.sex}")

    if indi.birth and indi.birth.date:
        birth_str = indi.birth.date.original
        if indi.birth.place:
            birth_str += f", {indi.birth.place.name}"
        parts.append(f"  Birth: {birth_str}")

    if indi.death and indi.death.date:
        death_str = indi.death.date.original
        if indi.death.place:
            death_str += f", {indi.death.place.name}"
        parts.append(f"  Death: {death_str}")

    if indi.family_spouse_xrefs:
        parts.append(f"  Spouse families: {', '.join(indi.family_spouse_xrefs)}")
    if indi.family_child_xref:
        parts.append(f"  Child of family: {indi.family_child_xref}")

    return "\n".join(parts)


def _format_person_detailed(indi: Individual, db: GedcomDatabase) -> str:
    """Format a person with all available fields."""
    parts = [_format_person_concise(indi, db)]

    if len(indi.names) > 1:
        alt_names = [n.full for n in indi.names[1:]]
        parts.append(f"  Alternate names: {', '.join(alt_names)}")

    for evt in indi.other_events:
        evt_str = f"  {evt.event_type}: {evt.date.original if evt.date else 'no date'}"
        if evt.place:
            evt_str += f", {evt.place.name}"
        if evt.description:
            evt_str += f" ({evt.description})"
        parts.append(evt_str)

    if indi.note_xrefs:
        for nref in indi.note_xrefs:
            note = db.notes.get(nref)
            if note:
                parts.append(f"  Note: {note.text[:200]}")

    if indi.source_xrefs:
        for sref in indi.source_xrefs:
            src = db.sources.get(sref)
            if src:
                parts.append(f"  Source: {src.title or sref}")

    return "\n".join(parts)


def register(mcp: FastMCP) -> None:
    """Register person-related tools."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    async def search_persons(
        ctx: Context[Any, Any, Any],
        name: str | None = None,
        birth_year_min: int | None = None,
        birth_year_max: int | None = None,
        death_year_min: int | None = None,
        death_year_max: int | None = None,
        place: str | None = None,
        sex: str | None = None,
        max_results: int | None = None,
    ) -> str:
        """Search individuals in the loaded GEDCOM file.

        Filters by name (case-insensitive substring), birth/death year ranges,
        place (case-insensitive substring on any event place), and sex.
        Returns up to max_results matches (default 50, max 100).

        A GEDCOM file must be loaded first via load_file.
        """
        try:
            db = require_database(ctx)
            app_ctx = get_app_context(ctx)
            ceiling = app_ctx.settings.max_search_results
            limit = min(max_results or 50, ceiling)

            matches: list[Individual] = []
            for indi in db.individuals.values():
                if name and not _matches_name(indi, name):
                    continue
                if place and not _matches_place(indi, place):
                    continue
                if sex and indi.sex != sex.upper():
                    continue
                if not _matches_year_range(
                    indi, birth_year_min, birth_year_max, death_year_min, death_year_max
                ):
                    continue
                matches.append(indi)
                if len(matches) >= limit:
                    break

            total_in_db = len(db.individuals)
            if not matches:
                return (
                    f"No individuals found matching the search criteria"
                    f" (searched {total_in_db} records)."
                )

            lines = [f"Found {len(matches)} individual(s)"]
            if len(matches) >= limit:
                lines[0] += (
                    f" (showing first {limit}, narrow your search for more specific results)"
                )
            lines.append("")
            for indi in matches:
                lines.append(_format_person_concise(indi, db))
                lines.append("")

            return "\n".join(lines)
        except McpToolError:
            raise
        except Exception as e:
            raise_tool_error(e, "person search")

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    async def get_person(
        ctx: Context[Any, Any, Any],
        xref: str,
        response_format: str = "detailed",
    ) -> str:
        """Retrieve a specific individual by cross-reference ID.

        Use "concise" format for name + vital dates + family links only.
        Use "detailed" format for all fields including notes and sources.

        A GEDCOM file must be loaded first via load_file.
        """
        try:
            db = require_database(ctx)
            indi = db.individuals.get(xref)
            if not indi:
                raise McpToolError(
                    f"Individual '{xref}' not found. "
                    "Use search_persons to find valid cross-reference IDs."
                )

            if response_format == "concise":
                return _format_person_concise(indi, db)
            return _format_person_detailed(indi, db)
        except McpToolError:
            raise
        except Exception as e:
            raise_tool_error(e, "get person", entity_type="individual", identifier=xref)
