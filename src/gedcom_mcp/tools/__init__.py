# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tool handlers for GEDCOM operations.

Re-exports domain handler functions. Meta-tools (meta_search, meta_execute) are
NOT re-exported here to prevent circular imports with operations.py.
"""

from gedcom_mcp.tools.analysis import (
    handle_get_ancestors,
    handle_get_descendants,
    handle_get_stats,
)
from gedcom_mcp.tools.read_ops import handle_get_family, handle_get_person
from gedcom_mcp.tools.search_ops import handle_search_persons
from gedcom_mcp.tools.setup import handle_load_file

__all__ = [
    "handle_get_ancestors",
    "handle_get_descendants",
    "handle_get_family",
    "handle_get_person",
    "handle_get_stats",
    "handle_load_file",
    "handle_search_persons",
]
