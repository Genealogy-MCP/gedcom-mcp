# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for the load_file handler (setup category)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gedcom_mcp.server import AppContext
from gedcom_mcp.settings import Settings
from gedcom_mcp.tools._errors import McpToolError
from gedcom_mcp.tools.setup import handle_load_file


def _make_ctx(settings: Settings | None = None) -> MagicMock:
    """Build a mock context without a loaded database."""
    s = settings or Settings()
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(settings=s, database=None)
    return ctx


def _text(result: list) -> str:
    """Extract text from list[TextContent]."""
    return "\n".join(item.text for item in result)


async def test_handle_load_file(fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    result = _text(await handle_load_file(ctx, file_path=str(fixtures_dir / "minimal.ged")))
    assert "Loaded: minimal.ged" in result
    assert "Individuals: 3" in result
    assert "Families: 1" in result
    assert ctx.request_context.lifespan_context.database is not None


async def test_handle_load_file_medium(fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    result = _text(await handle_load_file(ctx, file_path=str(fixtures_dir / "medium.ged")))
    assert "Individuals: 15" in result
    assert "Families: 5" in result


async def test_handle_load_file_relative_path() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="Path must be absolute"):
        await handle_load_file(ctx, file_path="relative/path.ged")


async def test_handle_load_file_wrong_extension() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="must have a .ged extension"):
        await handle_load_file(ctx, file_path="/tmp/file.txt")


async def test_handle_load_file_not_found() -> None:
    ctx = _make_ctx()
    with pytest.raises(McpToolError, match="File not found"):
        await handle_load_file(ctx, file_path="/tmp/nonexistent.ged")


async def test_handle_load_file_outside_allowed_dirs(fixtures_dir: Path) -> None:
    ctx = _make_ctx(settings=Settings(allowed_base_dirs="/some/other/dir"))
    with pytest.raises(McpToolError, match="outside allowed directories"):
        await handle_load_file(ctx, file_path=str(fixtures_dir / "minimal.ged"))


async def test_handle_load_file_replaces_previous(fixtures_dir: Path) -> None:
    ctx = _make_ctx()
    await handle_load_file(ctx, file_path=str(fixtures_dir / "minimal.ged"))
    app_ctx = ctx.request_context.lifespan_context
    assert len(app_ctx.database.individuals) == 3

    await handle_load_file(ctx, file_path=str(fixtures_dir / "empty.ged"))
    assert len(app_ctx.database.individuals) == 0
