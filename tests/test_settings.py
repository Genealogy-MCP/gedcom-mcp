# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for settings module."""

from __future__ import annotations

import pytest

from gedcom_mcp.settings import Settings


def test_default_settings() -> None:
    s = Settings()
    assert s.max_file_size_mb == 100
    assert s.default_ancestor_depth == 5
    assert s.default_descendant_depth == 5
    assert s.max_tree_depth == 50
    assert s.max_search_results == 100
    assert s.allowed_base_dirs == ""


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEDCOM_MAX_FILE_SIZE_MB", "50")
    monkeypatch.setenv("GEDCOM_MAX_SEARCH_RESULTS", "200")
    monkeypatch.setenv("GEDCOM_ALLOWED_BASE_DIRS", "/home/user/gedcom,/tmp")
    s = Settings()
    assert s.max_file_size_mb == 50
    assert s.max_search_results == 200
    assert s.allowed_base_dirs == "/home/user/gedcom,/tmp"
