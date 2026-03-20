# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Operation registry for Code Mode architecture (MCP-29 through MCP-32).

Defines metadata for every operation the server supports, Pydantic models
for runtime parameter validation, and a search function for operation
discovery.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Registry data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OperationParam:
    """Metadata for a single operation parameter."""

    name: str
    param_type: str
    description: str
    required: bool = False
    default: str | None = None


@dataclass(frozen=True, slots=True)
class OperationDef:
    """Metadata for a single operation in the registry."""

    name: str
    summary: str
    description: str
    params: tuple[OperationParam, ...]
    requires_database: bool
    read_only: bool
    tags: tuple[str, ...]


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


OPERATION_REGISTRY: dict[str, OperationDef] = {
    "load_file": OperationDef(
        name="load_file",
        summary="Load and parse a GEDCOM (.ged) file into memory",
        description=(
            "Load and parse a GEDCOM (.ged) file into memory. This must be executed "
            "before any other operation. Calling again replaces the previously loaded file. "
            "Returns a summary with the filename, GEDCOM version, and record counts."
        ),
        params=(
            OperationParam(
                name="file_path",
                param_type="string",
                description="Absolute path to the .ged file",
                required=True,
            ),
        ),
        requires_database=False,
        read_only=False,
        tags=("load", "file", "parse", "open"),
    ),
    "search_persons": OperationDef(
        name="search_persons",
        summary="Search individuals by name, dates, place, or sex",
        description=(
            "Search individuals in the loaded GEDCOM file. Filters by name "
            "(case-insensitive substring), birth/death year ranges, place "
            "(case-insensitive substring on any event place), and sex. "
            "Returns up to max_results matches (default 50, max 100)."
        ),
        params=(
            OperationParam(
                name="name",
                param_type="string",
                description="Case-insensitive name substring to match",
            ),
            OperationParam(
                name="birth_year_min",
                param_type="integer",
                description="Minimum birth year (inclusive)",
            ),
            OperationParam(
                name="birth_year_max",
                param_type="integer",
                description="Maximum birth year (inclusive)",
            ),
            OperationParam(
                name="death_year_min",
                param_type="integer",
                description="Minimum death year (inclusive)",
            ),
            OperationParam(
                name="death_year_max",
                param_type="integer",
                description="Maximum death year (inclusive)",
            ),
            OperationParam(
                name="place",
                param_type="string",
                description="Case-insensitive place substring to match on any event",
            ),
            OperationParam(
                name="sex",
                param_type="string",
                description="Sex filter: M, F, or U",
            ),
            OperationParam(
                name="max_results",
                param_type="integer",
                description="Maximum number of results (default 50, max 100)",
                default="50",
            ),
        ),
        requires_database=True,
        read_only=True,
        tags=("search", "find", "person", "individual", "query"),
    ),
    "get_person": OperationDef(
        name="get_person",
        summary="Retrieve a specific individual by cross-reference ID",
        description=(
            "Retrieve a specific individual by cross-reference ID (e.g. '@I1@'). "
            "Use 'concise' format for name + vital dates + family links only. "
            "Use 'detailed' format for all fields including notes and sources."
        ),
        params=(
            OperationParam(
                name="xref",
                param_type="string",
                description="Cross-reference ID (e.g. '@I1@')",
                required=True,
            ),
            OperationParam(
                name="response_format",
                param_type="string",
                description="'concise' or 'detailed' (default 'detailed')",
                default="detailed",
            ),
        ),
        requires_database=True,
        read_only=True,
        tags=("person", "individual", "detail", "retrieve"),
    ),
    "get_family": OperationDef(
        name="get_family",
        summary="Retrieve a family record by cross-reference ID",
        description=(
            "Retrieve a family record by cross-reference ID. Accepts either a family "
            "xref (e.g. '@F1@') or an individual xref (e.g. '@I1@'). When given an "
            "individual xref, returns all families where that person is a spouse."
        ),
        params=(
            OperationParam(
                name="xref",
                param_type="string",
                description="Family or individual cross-reference ID",
                required=True,
            ),
            OperationParam(
                name="response_format",
                param_type="string",
                description="'concise' or 'detailed' (default 'detailed')",
                default="detailed",
            ),
        ),
        requires_database=True,
        read_only=True,
        tags=("family", "marriage", "spouse", "children"),
    ),
    "get_ancestors": OperationDef(
        name="get_ancestors",
        summary="Get the ancestor tree for an individual",
        description=(
            "Traverse parent links up to max_generations deep (default 5, max 50). "
            "Each generation roughly doubles the number of ancestors. "
            "Uses BFS with cycle detection."
        ),
        params=(
            OperationParam(
                name="xref",
                param_type="string",
                description="Cross-reference ID of the starting individual",
                required=True,
            ),
            OperationParam(
                name="max_generations",
                param_type="integer",
                description="Maximum depth (default 5, max 50)",
                default="5",
            ),
        ),
        requires_database=True,
        read_only=True,
        tags=("ancestor", "parent", "tree", "lineage", "pedigree"),
    ),
    "get_descendants": OperationDef(
        name="get_descendants",
        summary="Get the descendant tree for an individual",
        description=(
            "Traverse children links up to max_generations deep (default 5, max 50). "
            "Descendant trees can grow exponentially. "
            "Uses BFS with cycle detection."
        ),
        params=(
            OperationParam(
                name="xref",
                param_type="string",
                description="Cross-reference ID of the starting individual",
                required=True,
            ),
            OperationParam(
                name="max_generations",
                param_type="integer",
                description="Maximum depth (default 5, max 50)",
                default="5",
            ),
        ),
        requires_database=True,
        read_only=True,
        tags=("descendant", "children", "tree", "offspring"),
    ),
    "get_stats": OperationDef(
        name="get_stats",
        summary="Get statistics about the loaded GEDCOM file",
        description=(
            "Returns record counts, sex distribution, top 10 surnames, "
            "birth/death date ranges, and data quality indicators."
        ),
        params=(),
        requires_database=True,
        read_only=True,
        tags=("statistics", "summary", "counts", "overview"),
    ),
}

PARAM_MODELS: dict[str, type[BaseModel]] = {
    "load_file": LoadFileParams,
    "search_persons": SearchPersonsParams,
    "get_person": GetPersonParams,
    "get_family": GetFamilyParams,
    "get_ancestors": GetAncestorsParams,
    "get_descendants": GetDescendantsParams,
    "get_stats": GetStatsParams,
}


# ---------------------------------------------------------------------------
# Search function
# ---------------------------------------------------------------------------


def search_operations(query: str) -> list[OperationDef]:
    """Search the operation registry by keyword matching.

    Args:
        query: Free-text search query. Empty string returns all operations.

    Returns:
        List of matching OperationDef objects sorted by relevance (score desc,
        then name asc).
    """
    if not query.strip():
        return sorted(OPERATION_REGISTRY.values(), key=lambda op: op.name)

    tokens = query.lower().split()
    scored: list[tuple[int, OperationDef]] = []

    for op in OPERATION_REGISTRY.values():
        searchable = f"{op.name} {op.summary} {' '.join(op.tags)}".lower()
        score = sum(1 for token in tokens if token in searchable)
        if score > 0:
            scored.append((score, op))

    scored.sort(key=lambda pair: (-pair[0], pair[1].name))
    return [op for _, op in scored]
