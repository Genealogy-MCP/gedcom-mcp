# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Shared fixtures for gedcom-mcp tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from gedcom_mcp.settings import Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings() -> Settings:
    """Default test settings."""
    return Settings()


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixture files."""
    return FIXTURES_DIR
