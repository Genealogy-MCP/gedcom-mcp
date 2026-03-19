# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Standalone handler functions for each GEDCOM operation.

Each handler is an async function that receives the MCP Context plus
keyword-only parameters. The handlers are called by the execute meta-tool
dispatcher and (during the migration) by the legacy tool closures.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from mcp.server.fastmcp import Context

from gedcom_mcp.parser import parse_file
from gedcom_mcp.parser.models import Individual
from gedcom_mcp.tools._errors import (
    McpToolError,
    get_app_context,
    raise_tool_error,
    require_database,
)
from gedcom_mcp.tools._formatting import (
    format_family_concise,
    format_family_detailed,
    format_person_concise,
    format_person_detailed,
    get_ancestors,
    get_descendants,
    matches_name,
    matches_place,
    matches_year_range,
    person_summary,
    validate_path,
)


async def handle_load_file(ctx: Context[Any, Any, Any], *, file_path: str) -> str:
    """Load and parse a GEDCOM file into the application context.

    Args:
        ctx: MCP request context.
        file_path: Absolute path to the .ged file.

    Returns:
        Summary string with filename, version, and record counts.
    """
    app_ctx = get_app_context(ctx)
    try:
        resolved = validate_path(
            file_path,
            app_ctx.settings.allowed_base_dirs,
            app_ctx.settings.max_file_size_mb,
        )
        raw = resolved.read_bytes()
        database = parse_file(raw)
        app_ctx.database = database

        basename = resolved.name
        version = database.header.gedcom_version or "unknown"
        lines = [
            f"Loaded: {basename}",
            f"GEDCOM version: {version}",
            f"Individuals: {len(database.individuals)}",
            f"Families: {len(database.families)}",
            f"Sources: {len(database.sources)}",
            f"Notes: {len(database.notes)}",
        ]
        return "\n".join(lines)
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "file load")


async def handle_search_persons(
    ctx: Context[Any, Any, Any],
    *,
    name: str | None = None,
    birth_year_min: int | None = None,
    birth_year_max: int | None = None,
    death_year_min: int | None = None,
    death_year_max: int | None = None,
    place: str | None = None,
    sex: str | None = None,
    max_results: int | None = None,
) -> str:
    """Search individuals in the loaded GEDCOM database.

    Args:
        ctx: MCP request context.
        name: Case-insensitive name substring.
        birth_year_min: Minimum birth year (inclusive).
        birth_year_max: Maximum birth year (inclusive).
        death_year_min: Minimum death year (inclusive).
        death_year_max: Maximum death year (inclusive).
        place: Case-insensitive place substring.
        sex: Sex filter (M/F/U).
        max_results: Maximum number of results to return.

    Returns:
        Formatted search results string.
    """
    try:
        db = require_database(ctx)
        app_ctx = get_app_context(ctx)
        ceiling = app_ctx.settings.max_search_results
        limit = min(max_results or 50, ceiling)

        matches: list[Individual] = []
        for indi in db.individuals.values():
            if name and not matches_name(indi, name):
                continue
            if place and not matches_place(indi, place):
                continue
            if sex and indi.sex != sex.upper():
                continue
            if not matches_year_range(
                indi, birth_year_min, birth_year_max, death_year_min, death_year_max
            ):
                continue
            matches.append(indi)
            if len(matches) >= limit:
                break

        total_in_db = len(db.individuals)
        if not matches:
            return (
                f"No individuals found matching the search criteria"
                f" (searched {total_in_db} records)."
            )

        lines = [f"Found {len(matches)} individual(s)"]
        if len(matches) >= limit:
            lines[0] += f" (showing first {limit}, narrow your search for more specific results)"
        lines.append("")
        for indi in matches:
            lines.append(format_person_concise(indi, db))
            lines.append("")

        return "\n".join(lines)
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "person search")


async def handle_get_person(
    ctx: Context[Any, Any, Any],
    *,
    xref: str,
    response_format: str = "detailed",
) -> str:
    """Retrieve a specific individual by cross-reference ID.

    Args:
        ctx: MCP request context.
        xref: Cross-reference ID (e.g. "@I1@").
        response_format: "concise" or "detailed".

    Returns:
        Formatted person string.
    """
    try:
        db = require_database(ctx)
        indi = db.individuals.get(xref)
        if not indi:
            raise McpToolError(
                f"Individual '{xref}' not found. "
                "Use search_persons to find valid cross-reference IDs."
            )

        if response_format == "concise":
            return format_person_concise(indi, db)
        return format_person_detailed(indi, db)
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get person", entity_type="individual", identifier=xref)


async def handle_get_family(
    ctx: Context[Any, Any, Any],
    *,
    xref: str,
    response_format: str = "detailed",
) -> str:
    """Retrieve a family record by cross-reference ID.

    Args:
        ctx: MCP request context.
        xref: Family or individual cross-reference ID.
        response_format: "concise" or "detailed".

    Returns:
        Formatted family string.
    """
    try:
        db = require_database(ctx)
        formatter = (
            format_family_concise if response_format == "concise" else format_family_detailed
        )

        if xref in db.families:
            return formatter(db.families[xref], db)

        if xref in db.individuals:
            indi = db.individuals[xref]
            if not indi.family_spouse_xrefs:
                return f"Individual {xref} is not a spouse in any family."
            results: list[str] = []
            for fxref in indi.family_spouse_xrefs:
                fam = db.families.get(fxref)
                if fam:
                    results.append(formatter(fam, db))
            if not results:
                return f"No family records found for individual {xref}."
            return "\n\n".join(results)

        raise McpToolError(
            f"'{xref}' not found as a family or individual. "
            "Use search_persons to find valid cross-reference IDs."
        )
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get family", entity_type="family", identifier=xref)


async def handle_get_ancestors(
    ctx: Context[Any, Any, Any],
    *,
    xref: str,
    max_generations: int | None = None,
) -> str:
    """Get the ancestor tree for an individual.

    Args:
        ctx: MCP request context.
        xref: Cross-reference ID of the starting individual.
        max_generations: Maximum depth (default from settings).

    Returns:
        Formatted ancestor tree string.
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
        ancestors = get_ancestors(xref, db, max_gen)

        if not ancestors:
            return f"No ancestors found for {person_summary(root)} (no parent links in the data)."

        lines = [f"Ancestors of {person_summary(root)} (up to {max_gen} generations):", ""]
        current_gen = 0
        for gen, indi in ancestors:
            if gen != current_gen:
                current_gen = gen
                lines.append(f"Generation {gen}:")
            lines.append(f"  {person_summary(indi)}")

        lines.append(f"\nTotal: {len(ancestors)} ancestor(s) found")
        return "\n".join(lines)
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get ancestors", entity_type="individual", identifier=xref)


async def handle_get_descendants(
    ctx: Context[Any, Any, Any],
    *,
    xref: str,
    max_generations: int | None = None,
) -> str:
    """Get the descendant tree for an individual.

    Args:
        ctx: MCP request context.
        xref: Cross-reference ID of the starting individual.
        max_generations: Maximum depth (default from settings).

    Returns:
        Formatted descendant tree string.
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
        descendants = get_descendants(xref, db, max_gen)

        if not descendants:
            return f"No descendants found for {person_summary(root)}."

        lines = [f"Descendants of {person_summary(root)} (up to {max_gen} generations):", ""]
        current_gen = 0
        for gen, indi in descendants:
            if gen != current_gen:
                current_gen = gen
                lines.append(f"Generation {gen}:")
            lines.append(f"  {person_summary(indi)}")

        lines.append(f"\nTotal: {len(descendants)} descendant(s) found")
        return "\n".join(lines)
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get descendants", entity_type="individual", identifier=xref)


async def handle_get_stats(ctx: Context[Any, Any, Any]) -> str:
    """Get statistics about the loaded GEDCOM file.

    Args:
        ctx: MCP request context.

    Returns:
        Formatted statistics string.
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

        return "\n".join(lines)
    except McpToolError:
        raise
    except Exception as e:
        raise_tool_error(e, "get stats")
