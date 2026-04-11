# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Tests for error handling utilities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gedcom_mcp.parser.models import GedcomDatabase
from gedcom_mcp.server import AppContext
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools._errors import (
    McpToolError,
    get_app_context,
    raise_tool_error,
    require_database,
)


def _make_ctx(database: GedcomDatabase | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=Settings(), database=database)
    return ctx


def test_mcp_tool_error_is_exception() -> None:
    err = McpToolError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"


def test_raise_tool_error_basic() -> None:
    with pytest.raises(McpToolError, match="Unexpected error during file load"):
        raise_tool_error(ValueError("bad"), "file load")


def test_raise_tool_error_with_context() -> None:
    with pytest.raises(McpToolError, match=r"\[individual: @I1@\]"):
        raise_tool_error(
            ValueError("not found"), "lookup", entity_type="individual", identifier="@I1@"
        )


def test_raise_tool_error_preserves_mcp_tool_error() -> None:
    original = McpToolError("original message")
    with pytest.raises(McpToolError, match="original message"):
        raise_tool_error(original, "operation")


def test_raise_tool_error_with_identifier_only() -> None:
    with pytest.raises(McpToolError, match=r"\[id: @F1@\]"):
        raise_tool_error(ValueError("err"), "op", identifier="@F1@")


def test_get_app_context() -> None:
    ctx = _make_ctx()
    app_ctx = get_app_context(ctx)
    assert isinstance(app_ctx, AppContext)


def test_require_database_no_file_loaded() -> None:
    ctx = _make_ctx(database=None)
    with pytest.raises(McpToolError, match="No GEDCOM file is loaded"):
        require_database(ctx)


def test_require_database_with_file_loaded() -> None:
    db = GedcomDatabase()
    ctx = _make_ctx(database=db)
    result = require_database(ctx)
    assert result is db
