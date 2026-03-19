# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""File loading tool for GEDCOM files."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.parser import parse_file
from gedcom_mcp.tools._errors import McpToolError, get_app_context, raise_tool_error
from gedcom_mcp.tools._formatting import validate_path


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
        app_ctx = get_app_context(ctx)
        try:
            resolved = validate_path(
                file_path,
                app_ctx.settings.allowed_base_dirs,
                app_ctx.settings.max_file_size_mb,
            )
            raw = resolved.read_bytes()
            database = parse_file(raw)
            app_ctx.database = database

            basename = resolved.name
            version = database.header.gedcom_version or "unknown"
            lines = [
                f"Loaded: {basename}",
                f"GEDCOM version: {version}",
                f"Individuals: {len(database.individuals)}",
                f"Families: {len(database.families)}",
                f"Sources: {len(database.sources)}",
                f"Notes: {len(database.notes)}",
            ]
            return "\n".join(lines)
        except McpToolError:
            raise
        except Exception as e:
            raise_tool_error(e, "file load")
