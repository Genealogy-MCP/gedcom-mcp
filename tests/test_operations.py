# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for the operation registry, search function, and parameter summarization."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gedcom_mcp.operations import (
    OPERATION_REGISTRY,
    VALID_CATEGORIES,
    GetAncestorsParams,
    GetDescendantsParams,
    GetFamilyParams,
    GetPersonParams,
    GetStatsParams,
    LoadFileParams,
    SearchPersonsParams,
    search_operations,
    summarize_params,
)

EXPECTED_OPERATIONS = {
    "load_file",
    "search_persons",
    "get_person",
    "get_family",
    "get_ancestors",
    "get_descendants",
    "get_stats",
}


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


def test_registry_contains_all_operations() -> None:
    assert set(OPERATION_REGISTRY.keys()) == EXPECTED_OPERATIONS


def test_registry_has_exactly_7_operations() -> None:
    assert len(OPERATION_REGISTRY) == 7


def test_every_operation_has_name_matching_key() -> None:
    for key, op in OPERATION_REGISTRY.items():
        assert op.name == key


def test_every_operation_has_summary_and_description() -> None:
    for name, op in OPERATION_REGISTRY.items():
        assert op.summary, f"{name} missing summary"
        assert op.description, f"{name} missing description"


def test_every_operation_has_valid_category() -> None:
    for name, op in OPERATION_REGISTRY.items():
        assert op.category in VALID_CATEGORIES, f"{name} has invalid category '{op.category}'"


def test_every_operation_has_callable_handler() -> None:
    for name, op in OPERATION_REGISTRY.items():
        assert callable(op.handler), f"{name} handler is not callable"


def test_every_operation_has_pydantic_schema() -> None:
    for name, op in OPERATION_REGISTRY.items():
        assert hasattr(op.params_schema, "model_validate"), (
            f"{name} params_schema is not a Pydantic model"
        )


def test_operation_entry_is_frozen() -> None:
    entry = OPERATION_REGISTRY["load_file"]
    with pytest.raises(AttributeError):
        entry.name = "hacked"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Behavioral flags
# ---------------------------------------------------------------------------


def test_load_file_is_not_read_only() -> None:
    assert not OPERATION_REGISTRY["load_file"].read_only


def test_all_others_are_read_only() -> None:
    for name, op in OPERATION_REGISTRY.items():
        if name != "load_file":
            assert op.read_only, f"{name} should be read-only"


def test_no_operations_are_destructive() -> None:
    for name, op in OPERATION_REGISTRY.items():
        assert not op.destructive, f"{name} should not be destructive"


# ---------------------------------------------------------------------------
# Category assignments
# ---------------------------------------------------------------------------


def test_category_setup() -> None:
    assert OPERATION_REGISTRY["load_file"].category == "setup"


def test_category_search() -> None:
    assert OPERATION_REGISTRY["search_persons"].category == "search"


def test_category_read() -> None:
    assert OPERATION_REGISTRY["get_person"].category == "read"
    assert OPERATION_REGISTRY["get_family"].category == "read"


def test_category_analysis() -> None:
    assert OPERATION_REGISTRY["get_ancestors"].category == "analysis"
    assert OPERATION_REGISTRY["get_descendants"].category == "analysis"
    assert OPERATION_REGISTRY["get_stats"].category == "analysis"


# ---------------------------------------------------------------------------
# search_operations
# ---------------------------------------------------------------------------


def test_search_empty_query_returns_all() -> None:
    results = search_operations("")
    assert len(results) == len(EXPECTED_OPERATIONS)


def test_search_empty_query_sorted_by_name() -> None:
    results = search_operations("")
    names = [r.name for r in results]
    assert names == sorted(names)


def test_search_exact_name_scores_highest() -> None:
    results = search_operations("get_person")
    assert results[0].name == "get_person"


def test_search_token_in_name_scores_higher_than_description() -> None:
    results = search_operations("ancestor")
    assert results[0].name == "get_ancestors"


def test_search_by_summary_keyword() -> None:
    results = search_operations("family")
    names = {r.name for r in results}
    assert "get_family" in names


def test_search_no_match() -> None:
    results = search_operations("zzzznonexistentzzzz")
    assert results == []


def test_search_case_insensitive() -> None:
    results = search_operations("PERSON")
    names = {r.name for r in results}
    assert "search_persons" in names or "get_person" in names


def test_search_with_category_filter() -> None:
    results = search_operations("", category="read")
    assert len(results) == 2
    assert all(r.category == "read" for r in results)


def test_search_with_category_and_query() -> None:
    results = search_operations("person", category="read")
    assert results[0].name == "get_person"


def test_search_max_results() -> None:
    results = search_operations("", max_results=3)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# summarize_params
# ---------------------------------------------------------------------------


def test_summarize_params_load_file() -> None:
    summary = summarize_params(LoadFileParams)
    assert len(summary) == 1
    assert summary[0]["name"] == "file_path"
    assert summary[0]["required"] is True
    assert summary[0]["type"] == "string"


def test_summarize_params_search_persons() -> None:
    summary = summarize_params(SearchPersonsParams)
    assert len(summary) == 8
    names = {p["name"] for p in summary}
    assert "name" in names
    assert "birth_year_min" in names
    assert "max_results" in names
    assert all(p["required"] is False for p in summary)


def test_summarize_params_get_person() -> None:
    summary = summarize_params(GetPersonParams)
    xref_param = next(p for p in summary if p["name"] == "xref")
    assert xref_param["required"] is True
    format_param = next(p for p in summary if p["name"] == "response_format")
    assert format_param["required"] is False
    assert format_param["default"] == "detailed"


def test_summarize_params_empty_model() -> None:
    summary = summarize_params(GetStatsParams)
    assert summary == []


def test_summarize_params_integer_type() -> None:
    summary = summarize_params(GetAncestorsParams)
    gen_param = next(p for p in summary if p["name"] == "max_generations")
    assert gen_param["type"] == "integer"


# ---------------------------------------------------------------------------
# Pydantic param models — validation
# ---------------------------------------------------------------------------


def test_load_file_params_requires_file_path() -> None:
    with pytest.raises(ValidationError):
        LoadFileParams.model_validate({})

    params = LoadFileParams.model_validate({"file_path": "/tmp/test.ged"})
    assert params.file_path == "/tmp/test.ged"


def test_search_persons_params_all_optional() -> None:
    params = SearchPersonsParams.model_validate({})
    assert params.name is None
    assert params.max_results is None


def test_search_persons_params_with_values() -> None:
    params = SearchPersonsParams.model_validate(
        {"name": "John", "birth_year_min": 1900, "max_results": 10}
    )
    assert params.name == "John"
    assert params.birth_year_min == 1900
    assert params.max_results == 10


def test_get_person_params_requires_xref() -> None:
    with pytest.raises(ValidationError):
        GetPersonParams.model_validate({})

    params = GetPersonParams.model_validate({"xref": "@I1@"})
    assert params.xref == "@I1@"
    assert params.response_format == "detailed"


def test_get_person_params_concise() -> None:
    params = GetPersonParams.model_validate({"xref": "@I1@", "response_format": "concise"})
    assert params.response_format == "concise"


def test_get_family_params_requires_xref() -> None:
    with pytest.raises(ValidationError):
        GetFamilyParams.model_validate({})


def test_get_ancestors_params() -> None:
    params = GetAncestorsParams.model_validate({"xref": "@I1@"})
    assert params.max_generations is None

    params = GetAncestorsParams.model_validate({"xref": "@I1@", "max_generations": 3})
    assert params.max_generations == 3


def test_get_descendants_params() -> None:
    params = GetDescendantsParams.model_validate({"xref": "@I1@"})
    assert params.max_generations is None


def test_get_stats_params() -> None:
    params = GetStatsParams.model_validate({})
    assert params is not None


def test_invalid_type_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchPersonsParams.model_validate({"birth_year_min": "not_a_number"})
