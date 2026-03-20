# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""FastMCP server setup with AppContext lifespan."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from mcp.server.fastmcp import FastMCP

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


def create_server() -> FastMCP:
    """Create and configure the GEDCOM MCP server with all tools registered."""
    mcp = FastMCP("GEDCOM", lifespan=app_lifespan)

    from gedcom_mcp.tools import execute, search

    search.register(mcp)
    execute.register(mcp)

    return mcp
