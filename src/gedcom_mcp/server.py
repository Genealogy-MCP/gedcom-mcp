# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""FastMCP server setup with AppContext lifespan and dynamic tool registration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import TextContent, ToolAnnotations

from gedcom_mcp.operations import OPERATION_REGISTRY
from gedcom_mcp.parser.models import GedcomDatabase
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools.meta_execute import ExecuteOperationParams, execute_operation_tool
from gedcom_mcp.tools.meta_search import SearchOperationsParams, search_operations_tool


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


_META_TOOLS: dict[str, dict[str, Any]] = {
    "search": {
        "schema": SearchOperationsParams,
        "handler": search_operations_tool,
        "description": (
            "Discover available GEDCOM operations. Search by keyword to find "
            "operations and their parameters. Use an empty query to list all. "
            f"This server has {len(OPERATION_REGISTRY)} operations."
        ),
        "annotations": ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    },
    "execute": {
        "schema": ExecuteOperationParams,
        "handler": execute_operation_tool,
        "description": (
            "Execute a GEDCOM operation with validated parameters. "
            "Use the search tool first to discover available operations."
        ),
        "annotations": ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    },
}


def create_server() -> FastMCP:
    """Create and configure the GEDCOM MCP server with all tools registered."""
    mcp = FastMCP("GEDCOM", lifespan=app_lifespan)

    search_config = _META_TOOLS["search"]

    @mcp.tool(
        name="search",
        description=search_config["description"],
        annotations=search_config["annotations"],
    )
    async def search(query: str = "", category: str | None = None) -> list[TextContent]:
        return await search_operations_tool({"query": query, "category": category})

    execute_config = _META_TOOLS["execute"]

    @mcp.tool(
        name="execute",
        description=execute_config["description"],
        annotations=execute_config["annotations"],
    )
    async def execute(
        ctx: Context[Any, Any, Any],
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> list[TextContent]:
        return await execute_operation_tool({"operation": operation, "params": params or {}}, ctx)

    @mcp.custom_route("/health", ["GET"])
    async def health_check(request: Any) -> Any:
        """Health check endpoint for Docker HEALTHCHECK."""
        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "status": "healthy",
                "service": "GEDCOM MCP Server",
                "tools": len(_META_TOOLS),
                "operations": len(OPERATION_REGISTRY),
            }
        )

    return mcp
