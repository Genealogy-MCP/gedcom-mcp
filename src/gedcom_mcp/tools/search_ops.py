# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Handler for the search_persons operation (category: search)."""

from __future__ import annotations

from typing import Any

from mcp.types import TextContent

from gedcom_mcp.parser.models import Individual
from gedcom_mcp.tools._errors import (
    McpToolError,
    get_app_context,
    raise_tool_error,
    require_database,
)
from gedcom_mcp.tools._formatting import (
    format_person_concise,
    matches_name,
    matches_place,
    matches_year_range,
)


async def handle_search_persons(ctx: Any, params: Any) -> list[TextContent]:
    """Search individuals in the loaded GEDCOM database.

    Args:
        ctx: MCP request context.
        params: SearchPersonsParams with filter fields.

    Returns:
        Formatted search results.
    """
    try:
        db = require_database(ctx)
        app_ctx = get_app_context(ctx)
        ceiling = app_ctx.settings.max_search_results
        limit = min(params.max_results or 50, ceiling)

        matches: list[Individual] = []
        for indi in db.individuals.values():
            if params.name and not matches_name(indi, params.name):
                continue
            if params.place and not matches_place(indi, params.place):
                continue
            if params.sex and indi.sex != params.sex.upper():
                continue
            if not matches_year_range(
                indi,
                params.birth_year_min,
                params.birth_year_max,
                params.death_year_min,
                params.death_year_max,
            ):
                continue
            matches.append(indi)
            if len(matches) >= limit:
                break

        total_in_db = len(db.individuals)
        if not matches:
            text = (
                f"No individuals found matching the search criteria"
                f" (searched {total_in_db} records)."
            )
            return [TextContent(type="text", text=text)]

        lines = [f"Found {len(matches)} individual(s)"]
        if len(matches) >= limit:
            lines[0] += f" (showing first {limit}, narrow your search for more specific results)"
        lines.append("")
        for indi in matches:
            lines.append(format_person_concise(indi, db))
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "person search")
