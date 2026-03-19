# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Family retrieval tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.tools._errors import McpToolError, raise_tool_error, require_database
from gedcom_mcp.tools._formatting import format_family_concise, format_family_detailed


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
                format_family_concise if response_format == "concise" else format_family_detailed
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
