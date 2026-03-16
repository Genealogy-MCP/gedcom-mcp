# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Statistics tool for the loaded GEDCOM database."""

from __future__ import annotations

from collections import Counter
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.tools._errors import McpToolError, raise_tool_error, require_database


def register(mcp: FastMCP) -> None:
    """Register statistics tools."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    async def get_stats(ctx: Context[Any, Any, Any]) -> str:
        """Get statistics about the loaded GEDCOM file.

        Returns record counts, sex distribution, top 10 surnames, date ranges,
        and data quality indicators.

        A GEDCOM file must be loaded first via load_file.
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

                for name in indi.names:
                    if name.surname:
                        surname_counts[name.surname] += 1

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
                lines.append(
                    f"  With birth event: {has_birth}/{total} ({100 * has_birth // total}%)"
                )
                lines.append(
                    f"  With death event: {has_death}/{total} ({100 * has_death // total}%)"
                )
                with_names = sum(1 for i in db.individuals.values() if i.names)
                lines.append(f"  With name: {with_names}/{total} ({100 * with_names // total}%)")

            return "\n".join(lines)
        except McpToolError:
            raise
        except Exception as e:
            raise_tool_error(e, "get stats")
