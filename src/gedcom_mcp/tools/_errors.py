# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Shared error handling for MCP tool responses (MCP-8, MCP-10).

McpToolError and raise_tool_error are re-exported from the shared library.
Repo-specific helpers (get_app_context, require_database) stay here.
"""

from __future__ import annotations

from typing import Any

from mcp_codemode import McpToolError, raise_tool_error

from gedcom_mcp.parser.models import GedcomDatabase

__all__ = [
    "McpToolError",
    "raise_tool_error",
    "get_app_context",
    "require_database",
]


def get_app_context(ctx: Any) -> Any:
    """Extract AppContext from MCP request context.

    Args:
        ctx: FastMCP Context object.

    Returns:
        The AppContext instance.
    """
    return ctx.request_context.lifespan_context  # type: ignore[no-any-return]


def require_database(ctx: Any) -> GedcomDatabase:
    """Extract database from context, raising if no file is loaded.

    Args:
        ctx: FastMCP Context object.

    Returns:
        The loaded GedcomDatabase.

    Raises:
        McpToolError: If no GEDCOM file has been loaded.
    """
    app_ctx = get_app_context(ctx)
    if app_ctx.database is None:
        raise McpToolError(
            "No GEDCOM file is loaded. Execute the 'load_file' operation first to load a .ged file."
        )
    return app_ctx.database  # type: ignore[no-any-return]
