# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Shared error handling for MCP tool responses (MCP-8, MCP-10)."""

from __future__ import annotations

import logging
from typing import Any, NoReturn

from gedcom_mcp.parser.models import GedcomDatabase

logger = logging.getLogger(__name__)


class McpToolError(Exception):
    """Raised by tool handlers to signal an error to the LLM.

    The MCP Server SDK catches exceptions from tool handlers and wraps them
    in CallToolResult with isError=True.
    """


def raise_tool_error(
    error: Exception,
    operation: str,
    *,
    entity_type: str | None = None,
    identifier: str | None = None,
) -> NoReturn:
    """Log and re-raise an exception as McpToolError.

    Args:
        error: The original exception.
        operation: Human-readable description of the failed operation.
        entity_type: Optional entity type for context.
        identifier: Optional xref or ID for context.

    Raises:
        McpToolError: Always raised with a formatted error message.
    """
    if isinstance(error, McpToolError):
        error_msg = str(error)
    else:
        error_msg = f"Unexpected error during {operation}: {error}"

    if entity_type and identifier:
        error_msg += f" [{entity_type}: {identifier}]"
    elif identifier:
        error_msg += f" [id: {identifier}]"

    logger.error("Tool error in %s: %s", operation, error_msg)
    raise McpToolError(error_msg) from error


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
