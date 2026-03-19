# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Family retrieval tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.tools._handlers import handle_get_family


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
        return await handle_get_family(ctx, xref=xref, response_format=response_format)
