# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Family retrieval tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.parser.models import Family, GedcomDatabase
from gedcom_mcp.tools._errors import McpToolError, raise_tool_error, require_database


def _person_label(xref: str, db: GedcomDatabase) -> str:
    """Get a display label for a person xref."""
    indi = db.individuals.get(xref)
    if not indi or not indi.names:
        return xref
    return f"{indi.names[0].full} ({xref})"


def _format_family_concise(fam: Family, db: GedcomDatabase) -> str:
    """Format a family with spouse names and children list."""
    parts = [f"Family {fam.xref}"]

    if fam.husband_xref:
        parts.append(f"  Husband: {_person_label(fam.husband_xref, db)}")
    if fam.wife_xref:
        parts.append(f"  Wife: {_person_label(fam.wife_xref, db)}")

    if fam.marriage and fam.marriage.date:
        m_str = fam.marriage.date.original
        if fam.marriage.place:
            m_str += f", {fam.marriage.place.name}"
        parts.append(f"  Marriage: {m_str}")

    if fam.children_xrefs:
        parts.append("  Children:")
        for cxref in fam.children_xrefs:
            parts.append(f"    - {_person_label(cxref, db)}")

    return "\n".join(parts)


def _format_family_detailed(fam: Family, db: GedcomDatabase) -> str:
    """Format a family with all available fields."""
    parts = [_format_family_concise(fam, db)]

    if fam.divorce and fam.divorce.date:
        d_str = fam.divorce.date.original
        if fam.divorce.place:
            d_str += f", {fam.divorce.place.name}"
        parts.append(f"  Divorce: {d_str}")

    for evt in fam.other_events:
        evt_str = f"  {evt.event_type}: {evt.date.original if evt.date else 'no date'}"
        if evt.place:
            evt_str += f", {evt.place.name}"
        parts.append(evt_str)

    if fam.note_xrefs:
        for nref in fam.note_xrefs:
            note = db.notes.get(nref)
            if note:
                parts.append(f"  Note: {note.text[:200]}")

    if fam.source_xrefs:
        for sref in fam.source_xrefs:
            src = db.sources.get(sref)
            if src:
                parts.append(f"  Source: {src.title or sref}")

    return "\n".join(parts)


def register(mcp: FastMCP) -> None:
    """Register family-related tools."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    async def get_family(
        ctx: Context[Any, Any, Any],
        xref: str,
        response_format: str = "detailed",
    ) -> str:
        """Retrieve a family record by cross-reference ID.

        Accepts either a family xref (e.g. "@F1@") or an individual xref
        (e.g. "@I1@"). When given an individual xref, returns all families
        where that person is a spouse.

        Use "concise" for spouse names + children list.
        Use "detailed" for all fields including events, notes, and sources.

        A GEDCOM file must be loaded first via load_file.
        """
        try:
            db = require_database(ctx)
            formatter = (
                _format_family_concise if response_format == "concise" else _format_family_detailed
            )

            if xref in db.families:
                return formatter(db.families[xref], db)

            if xref in db.individuals:
                indi = db.individuals[xref]
                if not indi.family_spouse_xrefs:
                    return f"Individual {xref} is not a spouse in any family."
                results: list[str] = []
                for fxref in indi.family_spouse_xrefs:
                    fam = db.families.get(fxref)
                    if fam:
                        results.append(formatter(fam, db))
                if not results:
                    return f"No family records found for individual {xref}."
                return "\n\n".join(results)

            raise McpToolError(
                f"'{xref}' not found as a family or individual. "
                "Use search_persons to find valid cross-reference IDs."
            )
        except McpToolError:
            raise
        except Exception as e:
            raise_tool_error(e, "get family", entity_type="family", identifier=xref)
