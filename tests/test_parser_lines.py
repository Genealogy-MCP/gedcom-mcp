# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for GEDCOM line parsing."""

from __future__ import annotations

from gedcom_mcp.parser.lines import GedcomLine, parse_lines


def test_simple_line() -> None:
    lines = parse_lines("0 HEAD\n")
    assert lines == [GedcomLine(level=0, xref=None, tag="HEAD", value=None, line_number=1)]


def test_line_with_value() -> None:
    lines = parse_lines("1 CHAR UTF-8\n")
    assert lines == [GedcomLine(level=1, xref=None, tag="CHAR", value="UTF-8", line_number=1)]


def test_line_with_xref() -> None:
    lines = parse_lines("0 @I1@ INDI\n")
    assert lines == [GedcomLine(level=0, xref="@I1@", tag="INDI", value=None, line_number=1)]


def test_line_with_xref_and_value() -> None:
    lines = parse_lines("0 @N1@ NOTE This is a note\n")
    assert lines == [
        GedcomLine(level=0, xref="@N1@", tag="NOTE", value="This is a note", line_number=1)
    ]


def test_multiple_lines() -> None:
    text = "0 HEAD\n1 SOUR Test\n2 VERS 1.0\n"
    lines = parse_lines(text)
    assert len(lines) == 3
    assert lines[0].tag == "HEAD"
    assert lines[1] == GedcomLine(level=1, xref=None, tag="SOUR", value="Test", line_number=2)
    assert lines[2] == GedcomLine(level=2, xref=None, tag="VERS", value="1.0", line_number=3)


def test_empty_lines_skipped() -> None:
    text = "0 HEAD\n\n1 SOUR Test\n\n"
    lines = parse_lines(text)
    assert len(lines) == 2
    assert lines[0].line_number == 1
    assert lines[1].line_number == 3


def test_carriage_return_handling() -> None:
    text = "0 HEAD\r\n1 SOUR Test\r\n"
    lines = parse_lines(text)
    assert len(lines) == 2
    assert lines[0].tag == "HEAD"
    assert lines[1].value == "Test"


def test_value_with_spaces() -> None:
    text = "1 NAME John /Smith/\n"
    lines = parse_lines(text)
    assert lines[0].value == "John /Smith/"


def test_name_with_pointer_value() -> None:
    text = "1 HUSB @I1@\n"
    lines = parse_lines(text)
    assert lines[0] == GedcomLine(level=1, xref=None, tag="HUSB", value="@I1@", line_number=1)


def test_level_numbers() -> None:
    text = "0 HEAD\n1 SOUR Test\n2 VERS 1.0\n"
    lines = parse_lines(text)
    assert [line.level for line in lines] == [0, 1, 2]


def test_empty_input() -> None:
    assert parse_lines("") == []
    assert parse_lines("\n\n\n") == []
