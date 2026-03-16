# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Ancestor and descendant traversal tools."""

from __future__ import annotations

from collections import deque
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.parser.models import GedcomDatabase, Individual
from gedcom_mcp.tools._errors import (
    McpToolError,
    get_app_context,
    raise_tool_error,
    require_database,
)


def _person_summary(indi: Individual) -> str:
    """One-line summary: xref, name, birth/death years."""
    name = indi.names[0].full if indi.names else "Unknown"
    years = ""
    b_year = indi.birth.date.year if indi.birth and indi.birth.date else None
    d_year = indi.death.date.year if indi.death and indi.death.date else None
    if b_year or d_year:
        years = f" ({b_year or '?'}-{d_year or '?'})"
    return f"{indi.xref}: {name}{years}"


def _get_ancestors(xref: str, db: GedcomDatabase, max_gen: int) -> list[tuple[int, Individual]]:
    """BFS ancestor traversal returning (generation, individual) pairs."""
    result: list[tuple[int, Individual]] = []
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(xref, 0)])

    while queue:
        current_xref, gen = queue.popleft()
        if current_xref in visited:
            continue
        visited.add(current_xref)

        indi = db.individuals.get(current_xref)
        if not indi:
            continue

        if gen > 0:
            result.append((gen, indi))

        if gen >= max_gen:
            continue

        if indi.family_child_xref:
            fam = db.families.get(indi.family_child_xref)
            if fam:
                if fam.husband_xref and fam.husband_xref not in visited:
                    queue.append((fam.husband_xref, gen + 1))
                if fam.wife_xref and fam.wife_xref not in visited:
                    queue.append((fam.wife_xref, gen + 1))

    return result


def _get_descendants(xref: str, db: GedcomDatabase, max_gen: int) -> list[tuple[int, Individual]]:
    """BFS descendant traversal returning (generation, individual) pairs."""
    result: list[tuple[int, Individual]] = []
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(xref, 0)])

    while queue:
        current_xref, gen = queue.popleft()
        if current_xref in visited:
            continue
        visited.add(current_xref)

        indi = db.individuals.get(current_xref)
        if not indi:
            continue

        if gen > 0:
            result.append((gen, indi))

        if gen >= max_gen:
            continue

        for fxref in indi.family_spouse_xrefs:
            fam = db.families.get(fxref)
            if fam:
                for cxref in fam.children_xrefs:
                    if cxref not in visited:
                        queue.append((cxref, gen + 1))

    return result


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

            lines = [f"Descendants of {_person_summary(root)} (up to {max_gen} generations):", ""]
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
