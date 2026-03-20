# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Execute meta-tool for validated operation dispatch (MCP-32)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from gedcom_mcp.tools._errors import McpToolError, require_database
from gedcom_mcp.tools._handlers import (
    handle_get_ancestors,
    handle_get_descendants,
    handle_get_family,
    handle_get_person,
    handle_get_stats,
    handle_load_file,
    handle_search_persons,
)
from gedcom_mcp.tools._registry import OPERATION_REGISTRY, PARAM_MODELS

HANDLER_MAP: dict[str, Callable[..., Awaitable[str]]] = {
    "load_file": handle_load_file,
    "search_persons": handle_search_persons,
    "get_person": handle_get_person,
    "get_family": handle_get_family,
    "get_ancestors": handle_get_ancestors,
    "get_descendants": handle_get_descendants,
    "get_stats": handle_get_stats,
}


def register(mcp: FastMCP) -> None:
    """Register the execute meta-tool on the given FastMCP server.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    async def execute(
        ctx: Context[Any, Any, Any],
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Execute a GEDCOM operation with validated parameters.

        Use the search tool first to discover available operations and their
        parameters. Then call this tool with the operation name and a params
        dict matching the operation's schema.

        Returns the operation result as a formatted string.
        """
        op_def = OPERATION_REGISTRY.get(operation)
        if not op_def:
            available = ", ".join(sorted(OPERATION_REGISTRY.keys()))
            raise McpToolError(
                f"Unknown operation '{operation}'. "
                f"Available operations: {available}. "
                "Use the search tool to discover operations."
            )

        param_model = PARAM_MODELS[operation]
        try:
            validated = param_model.model_validate(params or {})
        except ValidationError as exc:
            field_errors = "; ".join(
                f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
            )
            raise McpToolError(
                f"Invalid parameters for '{operation}': {field_errors}. "
                f"Use the search tool to see the expected parameters."
            ) from exc

        if op_def.requires_database:
            require_database(ctx)

        handler = HANDLER_MAP[operation]
        return await handler(ctx, **validated.model_dump(exclude_none=True))
