# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Person search and retrieval tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.parser.models import Individual
from gedcom_mcp.tools._errors import (
    McpToolError,
    get_app_context,
    raise_tool_error,
    require_database,
)
from gedcom_mcp.tools._formatting import (
    format_person_concise,
    format_person_detailed,
    matches_name,
    matches_place,
    matches_year_range,
)


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
                if name and not matches_name(indi, name):
                    continue
                if place and not matches_place(indi, place):
                    continue
                if sex and indi.sex != sex.upper():
                    continue
                if not matches_year_range(
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
                lines.append(format_person_concise(indi, db))
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
                return format_person_concise(indi, db)
            return format_person_detailed(indi, db)
        except McpToolError:
            raise
        except Exception as e:
            raise_tool_error(e, "get person", entity_type="individual", identifier=xref)
