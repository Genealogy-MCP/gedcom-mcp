# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Line-level parsing of GEDCOM text into structured GedcomLine objects."""

from __future__ import annotations

import re
from dataclasses import dataclass

_LINE_RE = re.compile(
    r"^(\d+)"  # level number
    r"(?:\s+(@[^@]+@))?"  # optional xref (e.g. @I1@)
    r"\s+(\w+)"  # tag
    r"(?:\s(.*))?$"  # optional value (rest of line)
)


@dataclass(frozen=True, slots=True)
class GedcomLine:
    """A single parsed GEDCOM line."""

    level: int
    xref: str | None
    tag: str
    value: str | None
    line_number: int


def parse_lines(text: str) -> list[GedcomLine]:
    """Parse GEDCOM text into a flat list of GedcomLine objects.

    Args:
        text: Unicode GEDCOM text.

    Returns:
        Ordered list of parsed lines, skipping blank lines.
    """
    result: list[GedcomLine] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        match = _LINE_RE.match(stripped)
        if not match:
            continue
        level = int(match.group(1))
        xref = match.group(2)
        tag = match.group(3)
        value = match.group(4)
        if value is not None:
            value = value.strip() or None
        result.append(
            GedcomLine(level=level, xref=xref, tag=tag, value=value, line_number=line_number)
        )
    return result
