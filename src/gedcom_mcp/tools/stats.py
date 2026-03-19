# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Statistics tool for the loaded GEDCOM database."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.tools._handlers import handle_get_stats


def register(mcp: FastMCP) -> None:
    """Register statistics tools."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    async def get_stats(ctx: Context[Any, Any, Any]) -> str:
        """Get statistics about the loaded GEDCOM file.

        Returns record counts, sex distribution, top 10 surnames, date ranges,
        and data quality indicators.

        A GEDCOM file must be loaded first via load_file.
        """
        return await handle_get_stats(ctx)
