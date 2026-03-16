# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""GEDCOM file parser -- converts .ged files into an in-memory database."""

from __future__ import annotations

from gedcom_mcp.parser.builder import build_database
from gedcom_mcp.parser.encoding import decode_gedcom
from gedcom_mcp.parser.lines import parse_lines
from gedcom_mcp.parser.models import GedcomDatabase
from gedcom_mcp.parser.records import build_records

__all__ = ["parse_file"]


def parse_file(raw: bytes) -> GedcomDatabase:
    """Parse raw GEDCOM bytes into an in-memory database.

    Args:
        raw: Raw bytes from a .ged file.

    Returns:
        Fully constructed GedcomDatabase with all records indexed by xref.
    """
    text = decode_gedcom(raw)
    lines = parse_lines(text)
    records = build_records(lines)
    return build_database(records)
