# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Ancestor and descendant traversal tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.tools._handlers import handle_get_ancestors, handle_get_descendants


def register(mcp: FastMCP) -> None:
    """Register genealogy traversal tools."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    async def get_ancestors(
        ctx: Context[Any, Any, Any],
        xref: str,
        max_generations: int | None = None,
    ) -> str:
        """Get the ancestor tree for an individual.

        Traverses parent links up to max_generations deep (default 5, max 50).
        Warning: each generation roughly doubles the number of ancestors.
        At depth 5, up to 62 ancestors may be returned.

        Uses BFS and tracks visited xrefs to handle circular references.

        A GEDCOM file must be loaded first via load_file.
        """
        return await handle_get_ancestors(ctx, xref=xref, max_generations=max_generations)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    async def get_descendants(
        ctx: Context[Any, Any, Any],
        xref: str,
        max_generations: int | None = None,
    ) -> str:
        """Get the descendant tree for an individual.

        Traverses children links up to max_generations deep (default 5, max 50).
        Warning: descendant trees can grow exponentially with each generation.

        Uses BFS and tracks visited xrefs to handle circular references.

        A GEDCOM file must be loaded first via load_file.
        """
        return await handle_get_descendants(ctx, xref=xref, max_generations=max_generations)
