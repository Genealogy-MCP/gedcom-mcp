# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Handlers for read operations: get_person, get_family (category: read)."""

from __future__ import annotations

from typing import Any

from mcp.types import TextContent

from gedcom_mcp.tools._errors import McpToolError, raise_tool_error, require_database
from gedcom_mcp.tools._formatting import (
    format_family_concise,
    format_family_detailed,
    format_person_concise,
    format_person_detailed,
)


async def handle_get_person(ctx: Any, params: Any) -> list[TextContent]:
    """Retrieve a specific individual by cross-reference ID.

    Args:
        ctx: MCP request context.
        params: GetPersonParams with xref and response_format.

    Returns:
        Formatted person data.
    """
    try:
        db = require_database(ctx)
        indi = db.individuals.get(params.xref)
        if not indi:
            raise McpToolError(
                f"Individual '{params.xref}' not found. "
                "Use search_persons to find valid cross-reference IDs."
            )

        if params.response_format == "concise":
            text = format_person_concise(indi, db)
        else:
            text = format_person_detailed(indi, db)
        return [TextContent(type="text", text=text)]
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get person", entity_type="individual", identifier=params.xref)


async def handle_get_family(ctx: Any, params: Any) -> list[TextContent]:
    """Retrieve a family record by cross-reference ID.

    Args:
        ctx: MCP request context.
        params: GetFamilyParams with xref and response_format.

    Returns:
        Formatted family data.
    """
    try:
        db = require_database(ctx)
        formatter = (
            format_family_concise if params.response_format == "concise" else format_family_detailed
        )

        if params.xref in db.families:
            text = formatter(db.families[params.xref], db)
            return [TextContent(type="text", text=text)]

        if params.xref in db.individuals:
            indi = db.individuals[params.xref]
            if not indi.family_spouse_xrefs:
                text = f"Individual {params.xref} is not a spouse in any family."
                return [TextContent(type="text", text=text)]
            results: list[str] = []
            for fxref in indi.family_spouse_xrefs:
                fam = db.families.get(fxref)
                if fam:
                    results.append(formatter(fam, db))
            if not results:
                text = f"No family records found for individual {params.xref}."
                return [TextContent(type="text", text=text)]
            return [TextContent(type="text", text="\n\n".join(results))]

        raise McpToolError(
            f"'{params.xref}' not found as a family or individual. "
            "Use search_persons to find valid cross-reference IDs."
        )
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get family", entity_type="family", identifier=params.xref)
