# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Ancestor and descendant traversal tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.tools._errors import (
    McpToolError,
    get_app_context,
    raise_tool_error,
    require_database,
)
from gedcom_mcp.tools._formatting import (
    get_ancestors as _get_ancestors,
)
from gedcom_mcp.tools._formatting import (
    get_descendants as _get_descendants,
)
from gedcom_mcp.tools._formatting import (
    person_summary as _person_summary,
)


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
        try:
            db = require_database(ctx)
            app_ctx = get_app_context(ctx)

            if xref not in db.individuals:
                raise McpToolError(
                    f"Individual '{xref}' not found. "
                    "Use search_persons to find valid cross-reference IDs."
                )

            max_gen = min(
                max_generations or app_ctx.settings.default_ancestor_depth,
                app_ctx.settings.max_tree_depth,
            )

            root = db.individuals[xref]
            ancestors = _get_ancestors(xref, db, max_gen)

            if not ancestors:
                return (
                    f"No ancestors found for {_person_summary(root)} (no parent links in the data)."
                )

            lines = [f"Ancestors of {_person_summary(root)} (up to {max_gen} generations):", ""]
            current_gen = 0
            for gen, indi in ancestors:
                if gen != current_gen:
                    current_gen = gen
                    lines.append(f"Generation {gen}:")
                lines.append(f"  {_person_summary(indi)}")

            lines.append(f"\nTotal: {len(ancestors)} ancestor(s) found")
            return "\n".join(lines)
        except McpToolError:
            raise
        except Exception as e:
            raise_tool_error(e, "get ancestors", entity_type="individual", identifier=xref)

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
        try:
            db = require_database(ctx)
            app_ctx = get_app_context(ctx)

            if xref not in db.individuals:
                raise McpToolError(
                    f"Individual '{xref}' not found. "
                    "Use search_persons to find valid cross-reference IDs."
                )

            max_gen = min(
                max_generations or app_ctx.settings.default_descendant_depth,
                app_ctx.settings.max_tree_depth,
            )

            root = db.individuals[xref]
            descendants = _get_descendants(xref, db, max_gen)

            if not descendants:
                return f"No descendants found for {_person_summary(root)}."

            lines = [
                f"Descendants of {_person_summary(root)} (up to {max_gen} generations):",
                "",
            ]
            current_gen = 0
            for gen, indi in descendants:
                if gen != current_gen:
                    current_gen = gen
                    lines.append(f"Generation {gen}:")
                lines.append(f"  {_person_summary(indi)}")

            lines.append(f"\nTotal: {len(descendants)} descendant(s) found")
            return "\n".join(lines)
        except McpToolError:
            raise
        except Exception as e:
            raise_tool_error(e, "get descendants", entity_type="individual", identifier=xref)
