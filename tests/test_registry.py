# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for the operation registry."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gedcom_mcp.tools._registry import (
    OPERATION_REGISTRY,
    PARAM_MODELS,
    GetAncestorsParams,
    GetDescendantsParams,
    GetFamilyParams,
    GetPersonParams,
    GetStatsParams,
    LoadFileParams,
    SearchPersonsParams,
    search_operations,
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


def test_registry_contains_all_operations() -> None:
    assert set(OPERATION_REGISTRY.keys()) == EXPECTED_OPERATIONS


def test_param_models_match_registry() -> None:
    assert set(PARAM_MODELS.keys()) == EXPECTED_OPERATIONS


def test_every_operation_has_summary() -> None:
    for name, op in OPERATION_REGISTRY.items():
        assert op.summary, f"{name} missing summary"
        assert op.description, f"{name} missing description"


def test_every_operation_has_name_matching_key() -> None:
    for key, op in OPERATION_REGISTRY.items():
        assert op.name == key


def test_load_file_not_requires_database() -> None:
    assert not OPERATION_REGISTRY["load_file"].requires_database


def test_all_others_require_database() -> None:
    for name, op in OPERATION_REGISTRY.items():
        if name != "load_file":
            assert op.requires_database, f"{name} should require database"


def test_load_file_not_read_only() -> None:
    assert not OPERATION_REGISTRY["load_file"].read_only


def test_all_others_read_only() -> None:
    for name, op in OPERATION_REGISTRY.items():
        if name != "load_file":
            assert op.read_only, f"{name} should be read-only"


# ---------------------------------------------------------------------------
# search_operations
# ---------------------------------------------------------------------------


def test_search_empty_query_returns_all() -> None:
    results = search_operations("")
    assert len(results) == len(EXPECTED_OPERATIONS)


def test_search_by_name() -> None:
    results = search_operations("ancestor")
    names = {r.name for r in results}
    assert "get_ancestors" in names


def test_search_by_tag() -> None:
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
    params = SearchPersonsParams.model_validate({
        "name": "John",
        "birth_year_min": 1900,
        "max_results": 10,
    })
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

    params = GetFamilyParams.model_validate({"xref": "@F1@"})
    assert params.xref == "@F1@"


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
