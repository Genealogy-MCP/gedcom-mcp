# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Execute meta-tool for validated operation dispatch (MCP-ORG-4)."""

from __future__ import annotations

import difflib
from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import BaseModel, ValidationError

from gedcom_mcp.operations import OPERATION_REGISTRY
from gedcom_mcp.tools._errors import McpToolError, require_database


class ExecuteOperationParams(BaseModel):
    """Top-level parameters for the execute meta-tool."""

    operation: str
    params: dict[str, Any] = {}


async def execute_operation_tool(
    arguments: dict[str, object], ctx: Context[Any, Any, Any]
) -> list[TextContent]:
    """Execute a GEDCOM operation with validated parameters.

    Use the search tool first to discover available operations and their
    parameters. Then call this tool with the operation name and a params
    dict matching the operation's schema.

    Args:
        arguments: Dict with 'operation' (str) and 'params' (dict).
        ctx: MCP request context.

    Returns:
        Operation result as formatted text content.
    """
    validated = ExecuteOperationParams.model_validate(arguments)

    entry = OPERATION_REGISTRY.get(validated.operation)
    if not entry:
        available = sorted(OPERATION_REGISTRY.keys())
        close = difflib.get_close_matches(validated.operation, available, n=3, cutoff=0.5)
        suggestion = ""
        if close:
            suggestion = f" Did you mean: {', '.join(close)}?"
        raise McpToolError(
            f"Unknown operation '{validated.operation}'.{suggestion} "
            f"Available operations: {', '.join(available)}. "
            "Use the search tool to discover operations."
        )

    # Validate operation-specific parameters
    try:
        op_validated = entry.params_schema.model_validate(validated.params)
    except ValidationError as exc:
        field_errors = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise McpToolError(
            f"Invalid parameters for '{validated.operation}': {field_errors}. "
            f"Use the search tool to see the expected parameters."
        ) from exc

    # Check database requirement (all ops except load_file)
    if entry.name != "load_file":
        require_database(ctx)

    return await entry.handler(ctx, **op_validated.model_dump(exclude_none=True))
