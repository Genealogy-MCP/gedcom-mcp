# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Pure formatting, matching, and traversal helpers for tool handlers.

All functions in this module are pure (no MCP Context dependency) and can be
unit-tested independently. Extracted from the original per-tool modules during
the Code Mode migration (MCP-29).
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from gedcom_mcp.parser.models import Family, GedcomDatabase, Individual
from gedcom_mcp.tools._errors import McpToolError

# ---------------------------------------------------------------------------
# Path validation (from file_management.py)
# ---------------------------------------------------------------------------


def validate_path(file_path: str, allowed_base_dirs: str, max_size_mb: int) -> Path:
    """Validate and resolve a file path securely.

    Args:
        file_path: User-provided file path string.
        allowed_base_dirs: Comma-separated allowed base directories (empty = allow all).
        max_size_mb: Maximum file size in megabytes.

    Returns:
        Resolved Path object.

    Raises:
        McpToolError: If validation fails.
    """
    path = Path(file_path)

    if not path.is_absolute():
        raise McpToolError(
            f"Path must be absolute: '{file_path}'. Provide the full path to the .ged file."
        )

    resolved = path.resolve()

    if ".." in resolved.parts:
        raise McpToolError("Path traversal is not allowed.")

    if resolved.suffix.lower() != ".ged":
        raise McpToolError(
            f"File must have a .ged extension, got '{resolved.suffix}'. "
            "Only GEDCOM files are supported."
        )

    if allowed_base_dirs:
        allowed = [Path(d.strip()).resolve() for d in allowed_base_dirs.split(",") if d.strip()]
        if allowed and not any(str(resolved).startswith(str(base)) for base in allowed):
            raise McpToolError(
                "File is outside allowed directories. Check GEDCOM_ALLOWED_BASE_DIRS configuration."
            )

    if not resolved.exists():
        raise McpToolError(
            f"File not found: '{resolved.name}'. Verify the path is correct and the file exists."
        )

    size_mb = resolved.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise McpToolError(
            f"File size ({size_mb:.1f} MB) exceeds the {max_size_mb} MB limit. "
            "Adjust GEDCOM_MAX_FILE_SIZE_MB if needed."
        )

    return resolved


# ---------------------------------------------------------------------------
# Person matching (from persons.py)
# ---------------------------------------------------------------------------


def matches_name(indi: Individual, query: str) -> bool:
    """Check if any of the individual's names match the query (case-insensitive)."""
    q = query.lower()
    return any(
        q in name.full.lower()
        or (name.given and q in name.given.lower())
        or (name.surname and q in name.surname.lower())
        for name in indi.names
    )


def matches_place(indi: Individual, query: str) -> bool:
    """Check if any event place matches the query (case-insensitive)."""
    q = query.lower()
    events = [indi.birth, indi.death, *indi.other_events]
    return any(evt and evt.place and q in evt.place.name.lower() for evt in events)


def matches_year_range(
    indi: Individual,
    birth_min: int | None,
    birth_max: int | None,
    death_min: int | None,
    death_max: int | None,
) -> bool:
    """Check if individual's birth/death years fall within ranges."""
    if birth_min is not None or birth_max is not None:
        if not indi.birth or not indi.birth.date or not indi.birth.date.year:
            return False
        year = indi.birth.date.year
        if birth_min is not None and year < birth_min:
            return False
        if birth_max is not None and year > birth_max:
            return False

    if death_min is not None or death_max is not None:
        if not indi.death or not indi.death.date or not indi.death.date.year:
            return False
        year = indi.death.date.year
        if death_min is not None and year < death_min:
            return False
        if death_max is not None and year > death_max:
            return False

    return True


# ---------------------------------------------------------------------------
# Person formatting (from persons.py)
# ---------------------------------------------------------------------------


def format_person_concise(indi: Individual, db: GedcomDatabase) -> str:
    """Format a person with name, vital dates, and family links."""
    name = indi.names[0].full if indi.names else "Unknown"
    parts = [f"{indi.xref}: {name}"]

    if indi.sex:
        parts.append(f"  Sex: {indi.sex}")

    if indi.birth and indi.birth.date:
        birth_str = indi.birth.date.original
        if indi.birth.place:
            birth_str += f", {indi.birth.place.name}"
        parts.append(f"  Birth: {birth_str}")

    if indi.death and indi.death.date:
        death_str = indi.death.date.original
        if indi.death.place:
            death_str += f", {indi.death.place.name}"
        parts.append(f"  Death: {death_str}")

    if indi.family_spouse_xrefs:
        parts.append(f"  Spouse families: {', '.join(indi.family_spouse_xrefs)}")
    if indi.family_child_xref:
        parts.append(f"  Child of family: {indi.family_child_xref}")

    return "\n".join(parts)


def format_person_detailed(indi: Individual, db: GedcomDatabase) -> str:
    """Format a person with all available fields."""
    parts = [format_person_concise(indi, db)]

    if len(indi.names) > 1:
        alt_names = [n.full for n in indi.names[1:]]
        parts.append(f"  Alternate names: {', '.join(alt_names)}")

    for evt in indi.other_events:
        evt_str = f"  {evt.event_type}: {evt.date.original if evt.date else 'no date'}"
        if evt.place:
            evt_str += f", {evt.place.name}"
        if evt.description:
            evt_str += f" ({evt.description})"
        parts.append(evt_str)

    if indi.note_xrefs:
        for nref in indi.note_xrefs:
            note = db.notes.get(nref)
            if note:
                parts.append(f"  Note: {note.text[:200]}")

    if indi.source_xrefs:
        for sref in indi.source_xrefs:
            src = db.sources.get(sref)
            if src:
                parts.append(f"  Source: {src.title or sref}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Family formatting (from families.py)
# ---------------------------------------------------------------------------


def person_label(xref: str, db: GedcomDatabase) -> str:
    """Get a display label for a person xref."""
    indi = db.individuals.get(xref)
    if not indi or not indi.names:
        return xref
    return f"{indi.names[0].full} ({xref})"


def format_family_concise(fam: Family, db: GedcomDatabase) -> str:
    """Format a family with spouse names and children list."""
    parts = [f"Family {fam.xref}"]

    if fam.husband_xref:
        parts.append(f"  Husband: {person_label(fam.husband_xref, db)}")
    if fam.wife_xref:
        parts.append(f"  Wife: {person_label(fam.wife_xref, db)}")

    if fam.marriage and fam.marriage.date:
        m_str = fam.marriage.date.original
        if fam.marriage.place:
            m_str += f", {fam.marriage.place.name}"
        parts.append(f"  Marriage: {m_str}")

    if fam.children_xrefs:
        parts.append("  Children:")
        for cxref in fam.children_xrefs:
            parts.append(f"    - {person_label(cxref, db)}")

    return "\n".join(parts)


def format_family_detailed(fam: Family, db: GedcomDatabase) -> str:
    """Format a family with all available fields."""
    parts = [format_family_concise(fam, db)]

    if fam.divorce and fam.divorce.date:
        d_str = fam.divorce.date.original
        if fam.divorce.place:
            d_str += f", {fam.divorce.place.name}"
        parts.append(f"  Divorce: {d_str}")

    for evt in fam.other_events:
        evt_str = f"  {evt.event_type}: {evt.date.original if evt.date else 'no date'}"
        if evt.place:
            evt_str += f", {evt.place.name}"
        parts.append(evt_str)

    if fam.note_xrefs:
        for nref in fam.note_xrefs:
            note = db.notes.get(nref)
            if note:
                parts.append(f"  Note: {note.text[:200]}")

    if fam.source_xrefs:
        for sref in fam.source_xrefs:
            src = db.sources.get(sref)
            if src:
                parts.append(f"  Source: {src.title or sref}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Genealogy traversal (from genealogy.py)
# ---------------------------------------------------------------------------


def person_summary(indi: Individual) -> str:
    """One-line summary: xref, name, birth/death years."""
    name = indi.names[0].full if indi.names else "Unknown"
    years = ""
    b_year = indi.birth.date.year if indi.birth and indi.birth.date else None
    d_year = indi.death.date.year if indi.death and indi.death.date else None
    if b_year or d_year:
        years = f" ({b_year or '?'}-{d_year or '?'})"
    return f"{indi.xref}: {name}{years}"


def get_ancestors(xref: str, db: GedcomDatabase, max_gen: int) -> list[tuple[int, Individual]]:
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


def get_descendants(xref: str, db: GedcomDatabase, max_gen: int) -> list[tuple[int, Individual]]:
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
