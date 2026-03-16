# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Application settings loaded from environment variables at startup."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """GEDCOM MCP server configuration.

    All settings have sensible defaults. No required env vars needed
    since this server operates entirely offline on local files.
    """

    model_config = {"env_prefix": "GEDCOM_"}

    max_file_size_mb: int = 100
    default_ancestor_depth: int = 5
    default_descendant_depth: int = 5
    max_tree_depth: int = 50
    max_search_results: int = 100
    allowed_base_dirs: str = ""
