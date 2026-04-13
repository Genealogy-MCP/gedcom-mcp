# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""FastMCP server setup with AppContext lifespan and library-based tool registration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from mcp_codemode import (
    ExecuteOperationParams,
    SearchOperationsParams,
    execute_operation,
    format_search_results,
    search_operations,
)

from gedcom_mcp.operations import OPERATION_REGISTRY
from gedcom_mcp.parser.models import GedcomDatabase
from gedcom_mcp.settings import Settings


@dataclass
class AppContext:
    """Lifespan context holding parsed GEDCOM state."""

    settings: Settings
    database: GedcomDatabase | None = field(default=None)


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize settings and yield the application context."""
    settings = Settings()
    yield AppContext(settings=settings)


def _register_tools(mcp: FastMCP) -> None:
    """Register search + execute meta-tools using library functions.

    Uses mcp.types.ToolAnnotations directly to avoid the library's
    lightweight ToolAnnotations dataclass incompatibility with newer
    FastMCP versions (library bug, tracked upstream).
    """

    @mcp.tool(
        name="search",
        description=(
            "Discover available operations and their parameters. "
            "Call with a top-level 'query' string (not inside params). "
            "Returns matching operations with parameter schemas and usage examples. "
            "Always use this before calling 'execute' to find the correct operation name."
        ),
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def search(arguments: SearchOperationsParams) -> list[Any]:
        matches = search_operations(
            arguments.query,
            OPERATION_REGISTRY,
            category=arguments.category,
        )
        text = format_search_results(matches, OPERATION_REGISTRY)
        from mcp.types import TextContent

        return [TextContent(type="text", text=text)]

    @mcp.tool(
        name="execute",
        description=(
            "Run a named operation. Use 'search' first to discover the exact "
            "operation name and its params schema, then call this with "
            "{operation: '...', params: {...}}."
        ),
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def execute(ctx: Any, arguments: ExecuteOperationParams) -> list[Any]:
        return await execute_operation(arguments.model_dump(), OPERATION_REGISTRY, ctx)


def create_server() -> FastMCP:
    """Create and configure the GEDCOM MCP server with all tools registered."""
    mcp = FastMCP("GEDCOM", lifespan=app_lifespan)

    _register_tools(mcp)

    @mcp.custom_route("/health", ["GET"])
    async def health_check(request: Any) -> Any:
        """Health check endpoint for Docker HEALTHCHECK."""
        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "status": "healthy",
                "service": "GEDCOM MCP Server",
                "tools": 2,
                "operations": len(OPERATION_REGISTRY),
            }
        )

    return mcp
