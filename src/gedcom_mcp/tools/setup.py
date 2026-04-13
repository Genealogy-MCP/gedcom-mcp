# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Handler for the load_file operation (category: setup)."""

from __future__ import annotations

from typing import Any

from mcp.types import TextContent

from gedcom_mcp.parser import parse_file
from gedcom_mcp.tools._errors import McpToolError, get_app_context, raise_tool_error
from gedcom_mcp.tools._formatting import validate_path


async def handle_load_file(ctx: Any, params: Any) -> list[TextContent]:
    """Load and parse a GEDCOM file into the application context.

    Args:
        ctx: MCP request context.
        params: LoadFileParams with file_path.

    Returns:
        Summary with filename, version, and record counts.
    """
    app_ctx = get_app_context(ctx)
    try:
        resolved = validate_path(
            params.file_path,
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
        return [TextContent(type="text", text="\n".join(lines))]
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "file load")
