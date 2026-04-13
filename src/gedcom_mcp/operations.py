# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Operation registry for Code Mode architecture (MCP-ORG-1 through MCP-ORG-4).

Single source of truth for all operations the server supports. Each OperationEntry
bundles metadata, parameter schema, and handler function reference.
"""

from __future__ import annotations

from mcp_codemode import OperationEntry
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
