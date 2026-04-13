# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Handlers for analysis operations: get_ancestors, get_descendants, get_stats."""

from __future__ import annotations

from collections import Counter
from typing import Any

from mcp.types import TextContent

from gedcom_mcp.tools._errors import (
    McpToolError,
    get_app_context,
    raise_tool_error,
    require_database,
)
from gedcom_mcp.tools._formatting import (
    get_ancestors,
    get_descendants,
    person_summary,
)


async def handle_get_ancestors(ctx: Any, params: Any) -> list[TextContent]:
    """Get the ancestor tree for an individual.

    Args:
        ctx: MCP request context.
        params: GetAncestorsParams with xref and max_generations.

    Returns:
        Formatted ancestor tree.
    """
    try:
        db = require_database(ctx)
        app_ctx = get_app_context(ctx)

        if params.xref not in db.individuals:
            raise McpToolError(
                f"Individual '{params.xref}' not found. "
                "Use search_persons to find valid cross-reference IDs."
            )

        max_gen = min(
            params.max_generations or app_ctx.settings.default_ancestor_depth,
            app_ctx.settings.max_tree_depth,
        )

        root = db.individuals[params.xref]
        ancestors = get_ancestors(params.xref, db, max_gen)

        if not ancestors:
            text = f"No ancestors found for {person_summary(root)} (no parent links in the data)."
            return [TextContent(type="text", text=text)]

        lines = [f"Ancestors of {person_summary(root)} (up to {max_gen} generations):", ""]
        current_gen = 0
        for gen, indi in ancestors:
            if gen != current_gen:
                current_gen = gen
                lines.append(f"Generation {gen}:")
            lines.append(f"  {person_summary(indi)}")

        lines.append(f"\nTotal: {len(ancestors)} ancestor(s) found")
        return [TextContent(type="text", text="\n".join(lines))]
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get ancestors", entity_type="individual", identifier=params.xref)


async def handle_get_descendants(ctx: Any, params: Any) -> list[TextContent]:
    """Get the descendant tree for an individual.

    Args:
        ctx: MCP request context.
        params: GetDescendantsParams with xref and max_generations.

    Returns:
        Formatted descendant tree.
    """
    try:
        db = require_database(ctx)
        app_ctx = get_app_context(ctx)

        if params.xref not in db.individuals:
            raise McpToolError(
                f"Individual '{params.xref}' not found. "
                "Use search_persons to find valid cross-reference IDs."
            )

        max_gen = min(
            params.max_generations or app_ctx.settings.default_descendant_depth,
            app_ctx.settings.max_tree_depth,
        )

        root = db.individuals[params.xref]
        descendants = get_descendants(params.xref, db, max_gen)

        if not descendants:
            text = f"No descendants found for {person_summary(root)}."
            return [TextContent(type="text", text=text)]

        lines = [f"Descendants of {person_summary(root)} (up to {max_gen} generations):", ""]
        current_gen = 0
        for gen, indi in descendants:
            if gen != current_gen:
                current_gen = gen
                lines.append(f"Generation {gen}:")
            lines.append(f"  {person_summary(indi)}")

        lines.append(f"\nTotal: {len(descendants)} descendant(s) found")
        return [TextContent(type="text", text="\n".join(lines))]
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get descendants", entity_type="individual", identifier=params.xref)


async def handle_get_stats(ctx: Any, params: Any) -> list[TextContent]:
    """Get statistics about the loaded GEDCOM file.

    Args:
        ctx: MCP request context.
        params: GetStatsParams (empty model).

    Returns:
        Formatted statistics.
    """
    try:
        db = require_database(ctx)

        lines = ["GEDCOM Statistics", ""]

        lines.append("Record Counts:")
        lines.append(f"  Individuals: {len(db.individuals)}")
        lines.append(f"  Families: {len(db.families)}")
        lines.append(f"  Sources: {len(db.sources)}")
        lines.append(f"  Notes: {len(db.notes)}")

        sex_counts: Counter[str] = Counter()
        surname_counts: Counter[str] = Counter()
        birth_years: list[int] = []
        death_years: list[int] = []
        has_birth = 0
        has_death = 0

        for indi in db.individuals.values():
            sex_counts[indi.sex or "Unknown"] += 1

            for name_obj in indi.names:
                if name_obj.surname:
                    surname_counts[name_obj.surname] += 1

            if indi.birth:
                has_birth += 1
                if indi.birth.date and indi.birth.date.year:
                    birth_years.append(indi.birth.date.year)

            if indi.death:
                has_death += 1
                if indi.death.date and indi.death.date.year:
                    death_years.append(indi.death.date.year)

        lines.append("")
        lines.append("Sex Distribution:")
        for sex, count in sex_counts.most_common():
            lines.append(f"  {sex}: {count}")

        if surname_counts:
            lines.append("")
            lines.append("Top 10 Surnames:")
            for surname, count in surname_counts.most_common(10):
                lines.append(f"  {surname}: {count}")

        if birth_years:
            lines.append("")
            lines.append(f"Birth Year Range: {min(birth_years)}-{max(birth_years)}")

        if death_years:
            lines.append(f"Death Year Range: {min(death_years)}-{max(death_years)}")

        total = len(db.individuals)
        if total > 0:
            lines.append("")
            lines.append("Data Quality:")
            lines.append(f"  With birth event: {has_birth}/{total} ({100 * has_birth // total}%)")
            lines.append(f"  With death event: {has_death}/{total} ({100 * has_death // total}%)")
            with_names = sum(1 for i in db.individuals.values() if i.names)
            lines.append(f"  With name: {with_names}/{total} ({100 * with_names // total}%)")

        return [TextContent(type="text", text="\n".join(lines))]
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get stats")
