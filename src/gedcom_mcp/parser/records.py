# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Group flat GEDCOM lines into a hierarchical tree of records."""

from __future__ import annotations

from dataclasses import dataclass, field

from gedcom_mcp.parser.lines import GedcomLine


@dataclass
class GedcomRecord:
    """A hierarchical GEDCOM record with children."""

    tag: str
    value: str | None
    xref: str | None
    children: list[GedcomRecord] = field(default_factory=lambda: list[GedcomRecord]())
    line_number: int = 0

    def find(self, tag: str) -> GedcomRecord | None:
        """Find first child with the given tag."""
        for child in self.children:
            if child.tag == tag:
                return child
        return None

    def find_all(self, tag: str) -> list[GedcomRecord]:
        """Find all children with the given tag."""
        return [child for child in self.children if child.tag == tag]

    def find_value(self, tag: str) -> str | None:
        """Find the value of the first child with the given tag."""
        child = self.find(tag)
        return child.value if child else None


def _append_continuation(record: GedcomRecord, tag: str, value: str | None) -> None:
    """Merge CONT/CONC lines into the parent record's value."""
    text = value or ""
    if tag == "CONT":
        record.value = (record.value or "") + "\n" + text
    else:  # CONC
        record.value = (record.value or "") + text


def build_records(lines: list[GedcomLine]) -> list[GedcomRecord]:
    """Build a hierarchical record tree from flat GEDCOM lines.

    Handles CONT/CONC continuation lines by merging them into the parent value.

    Args:
        lines: Flat list of parsed GEDCOM lines.

    Returns:
        List of top-level (level 0) records.
    """
    if not lines:
        return []

    root: list[GedcomRecord] = []
    stack: list[GedcomRecord] = []

    for line in lines:
        if line.tag in ("CONT", "CONC") and stack:
            _append_continuation(stack[-1], line.tag, line.value)
            continue

        record = GedcomRecord(
            tag=line.tag,
            value=line.value,
            xref=line.xref,
            line_number=line.line_number,
        )

        if line.level == 0:
            root.append(record)
            stack = [record]
        else:
            while len(stack) > line.level:
                stack.pop()
            if stack:
                stack[-1].children.append(record)
            stack.append(record)

    return root
