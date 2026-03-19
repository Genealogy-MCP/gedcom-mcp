# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Person search and retrieval tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.tools._handlers import handle_get_person, handle_search_persons


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
        return await handle_search_persons(
            ctx,
            name=name,
            birth_year_min=birth_year_min,
            birth_year_max=birth_year_max,
            death_year_min=death_year_min,
            death_year_max=death_year_max,
            place=place,
            sex=sex,
            max_results=max_results,
        )

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
        return await handle_get_person(ctx, xref=xref, response_format=response_format)
