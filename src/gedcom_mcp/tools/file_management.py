# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""File loading tool for GEDCOM files."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.tools._handlers import handle_load_file


def register(mcp: FastMCP) -> None:
    """Register file management tools."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def load_file(ctx: Context[Any, Any, Any], file_path: str) -> str:
        """Load and parse a GEDCOM (.ged) file into memory.

        This must be called before any other tool. Loads the file, parses all
        records, and makes them available for querying. Calling again replaces
        the previously loaded file.

        Requires an absolute file path. Returns a summary with the filename,
        GEDCOM version, and record counts.
        """
        return await handle_load_file(ctx, file_path=file_path)
