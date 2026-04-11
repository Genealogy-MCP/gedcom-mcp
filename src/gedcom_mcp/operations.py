# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Operation registry for Code Mode architecture (MCP-ORG-1 through MCP-ORG-4).

Single source of truth for all operations the server supports. Each OperationEntry
bundles metadata, parameter schema, and handler function reference. The search
function enables LLM discovery via the search meta-tool.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from gedcom_mcp.tools.analysis import (
    handle_get_ancestors,
    handle_get_descendants,
    handle_get_stats,
)
from gedcom_mcp.tools.read_ops import handle_get_family, handle_get_person
from gedcom_mcp.tools.search_ops import handle_search_persons
from gedcom_mcp.tools.setup import handle_load_file

# ---------------------------------------------------------------------------
# Registry data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperationEntry:
    """Metadata for a single operation in the registry.

    Bundles the operation's description, parameter schema, handler function,
    and behavioral flags into a single immutable entry.
    """

    name: str
    summary: str
    description: str
    category: str
    params_schema: type[BaseModel]
    handler: Callable[..., Any]
    read_only: bool
    destructive: bool
    token_warning: str | None = field(default=None)


# ---------------------------------------------------------------------------
# Pydantic param models for runtime validation
# ---------------------------------------------------------------------------


class LoadFileParams(BaseModel):
    """Parameters for the load_file operation."""

    file_path: str


class SearchPersonsParams(BaseModel):
    """Parameters for the search_persons operation."""

    name: str | None = None
    birth_year_min: int | None = None
    birth_year_max: int | None = None
    death_year_min: int | None = None
    death_year_max: int | None = None
    place: str | None = None
    sex: str | None = None
    max_results: int | None = None


class GetPersonParams(BaseModel):
    """Parameters for the get_person operation."""

    xref: str
    response_format: str = "detailed"


class GetFamilyParams(BaseModel):
    """Parameters for the get_family operation."""

    xref: str
    response_format: str = "detailed"


class GetAncestorsParams(BaseModel):
    """Parameters for the get_ancestors operation."""

    xref: str
    max_generations: int | None = None


class GetDescendantsParams(BaseModel):
    """Parameters for the get_descendants operation."""

    xref: str
    max_generations: int | None = None


class GetStatsParams(BaseModel):
    """Parameters for the get_stats operation."""


# ---------------------------------------------------------------------------
# Operation registry
# ---------------------------------------------------------------------------

OPERATION_REGISTRY: dict[str, OperationEntry] = {
    "load_file": OperationEntry(
        name="load_file",
        summary="Load and parse a GEDCOM (.ged) file into memory",
        description=(
            "Load and parse a GEDCOM (.ged) file into memory. This must be executed "
            "before any other operation. Calling again replaces the previously loaded file. "
            "Returns a summary with the filename, GEDCOM version, and record counts."
        ),
        category="setup",
        params_schema=LoadFileParams,
        handler=handle_load_file,
        read_only=False,
        destructive=False,
    ),
    "search_persons": OperationEntry(
        name="search_persons",
        summary="Search individuals by name, dates, place, or sex",
        description=(
            "Search individuals in the loaded GEDCOM file. Filters by name "
            "(case-insensitive substring), birth/death year ranges, place "
            "(case-insensitive substring on any event place), and sex. "
            "Returns up to max_results matches (default 50, max 100)."
        ),
        category="search",
        params_schema=SearchPersonsParams,
        handler=handle_search_persons,
        read_only=True,
        destructive=False,
        token_warning="Large result sets may be token-heavy. Use max_results to limit output.",
    ),
    "get_person": OperationEntry(
        name="get_person",
        summary="Retrieve a specific individual by cross-reference ID",
        description=(
            "Retrieve a specific individual by cross-reference ID (e.g. '@I1@'). "
            "Use 'concise' format for name + vital dates + family links only. "
            "Use 'detailed' format for all fields including notes and sources."
        ),
        category="read",
        params_schema=GetPersonParams,
        handler=handle_get_person,
        read_only=True,
        destructive=False,
    ),
    "get_family": OperationEntry(
        name="get_family",
        summary="Retrieve a family record by cross-reference ID",
        description=(
            "Retrieve a family record by cross-reference ID. Accepts either a family "
            "xref (e.g. '@F1@') or an individual xref (e.g. '@I1@'). When given an "
            "individual xref, returns all families where that person is a spouse."
        ),
        category="read",
        params_schema=GetFamilyParams,
        handler=handle_get_family,
        read_only=True,
        destructive=False,
    ),
    "get_ancestors": OperationEntry(
        name="get_ancestors",
        summary="Get the ancestor tree for an individual",
        description=(
            "Traverse parent links up to max_generations deep (default 5, max 50). "
            "Each generation roughly doubles the number of ancestors. "
            "Uses BFS with cycle detection."
        ),
        category="analysis",
        params_schema=GetAncestorsParams,
        handler=handle_get_ancestors,
        read_only=True,
        destructive=False,
        token_warning=(
            "Deep ancestor trees grow exponentially. Limit max_generations for large files."
        ),
    ),
    "get_descendants": OperationEntry(
        name="get_descendants",
        summary="Get the descendant tree for an individual",
        description=(
            "Traverse children links up to max_generations deep (default 5, max 50). "
            "Descendant trees can grow exponentially. "
            "Uses BFS with cycle detection."
        ),
        category="analysis",
        params_schema=GetDescendantsParams,
        handler=handle_get_descendants,
        read_only=True,
        destructive=False,
        token_warning=(
            "Deep descendant trees grow exponentially. Limit max_generations for large files."
        ),
    ),
    "get_stats": OperationEntry(
        name="get_stats",
        summary="Get statistics about the loaded GEDCOM file",
        description=(
            "Returns record counts, sex distribution, top 10 surnames, "
            "birth/death date ranges, and data quality indicators."
        ),
        category="analysis",
        params_schema=GetStatsParams,
        handler=handle_get_stats,
        read_only=True,
        destructive=False,
    ),
}


# ---------------------------------------------------------------------------
# Search function
# ---------------------------------------------------------------------------

VALID_CATEGORIES = frozenset({"setup", "search", "read", "analysis"})


def search_operations(
    query: str,
    *,
    category: str | None = None,
    max_results: int = 10,
) -> list[OperationEntry]:
    """Search the operation registry by keyword matching with weighted scoring.

    Scoring:
        +3: exact operation name match
        +2: query token found in operation name
        +1: query token found in summary or description

    Args:
        query: Free-text search query. Empty string returns all operations.
        category: Optional category filter (setup/search/read/analysis).
        max_results: Maximum number of results to return.

    Returns:
        List of matching OperationEntry objects sorted by relevance.
    """
    ops = OPERATION_REGISTRY.values()

    if category:
        ops = [op for op in ops if op.category == category]

    if not query.strip():
        return sorted(ops, key=lambda op: op.name)[:max_results]

    tokens = query.lower().split()
    scored: list[tuple[int, OperationEntry]] = []

    for op in ops:
        score = 0
        name_lower = op.name.lower()

        # +3 for exact name match
        if query.lower() == name_lower:
            score += 3

        for token in tokens:
            # +2 for token in operation name
            if token in name_lower:
                score += 2
            # +1 for token in summary or description
            elif token in op.summary.lower() or token in op.description.lower():
                score += 1

        if score > 0:
            scored.append((score, op))

    scored.sort(key=lambda pair: (-pair[0], pair[1].name))
    return [op for _, op in scored[:max_results]]


# ---------------------------------------------------------------------------
# Parameter summarization
# ---------------------------------------------------------------------------


def summarize_params(schema: type[BaseModel]) -> list[dict[str, str | bool]]:
    """Produce an LLM-friendly summary of a Pydantic model's fields.

    Args:
        schema: Pydantic BaseModel subclass to introspect.

    Returns:
        List of dicts with keys: name, type, required, description.
    """
    result: list[dict[str, str | bool]] = []
    for name, field_info in schema.model_fields.items():
        is_required = field_info.is_required()
        field_type = "string"
        if field_info.annotation is not None:
            annotation_str = str(field_info.annotation)
            if "int" in annotation_str:
                field_type = "integer"
            elif "bool" in annotation_str:
                field_type = "boolean"
            elif "float" in annotation_str:
                field_type = "number"

        entry: dict[str, str | bool] = {
            "name": name,
            "type": field_type,
            "required": is_required,
            "description": field_info.description or "",
        }
        if not is_required and field_info.default is not None:
            entry["default"] = str(field_info.default)

        result.append(entry)
    return result
