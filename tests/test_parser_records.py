# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for GEDCOM record tree building."""

from __future__ import annotations

from gedcom_mcp.parser.lines import parse_lines
from gedcom_mcp.parser.records import GedcomRecord, build_records


def test_single_record() -> None:
    lines = parse_lines("0 HEAD\n")
    records = build_records(lines)
    assert len(records) == 1
    assert records[0].tag == "HEAD"


def test_nested_children() -> None:
    text = "0 HEAD\n1 SOUR Test\n2 VERS 1.0\n"
    lines = parse_lines(text)
    records = build_records(lines)
    assert len(records) == 1
    head = records[0]
    assert head.tag == "HEAD"
    assert len(head.children) == 1
    sour = head.children[0]
    assert sour.tag == "SOUR"
    assert sour.value == "Test"
    assert len(sour.children) == 1
    assert sour.children[0].tag == "VERS"
    assert sour.children[0].value == "1.0"


def test_multiple_top_level_records() -> None:
    text = "0 HEAD\n1 CHAR UTF-8\n0 @I1@ INDI\n1 NAME John\n0 TRLR\n"
    lines = parse_lines(text)
    records = build_records(lines)
    assert len(records) == 3
    assert records[0].tag == "HEAD"
    assert records[1].tag == "INDI"
    assert records[1].xref == "@I1@"
    assert records[2].tag == "TRLR"


def test_cont_continuation() -> None:
    text = "0 @N1@ NOTE First line\n1 CONT Second line\n1 CONT Third line\n"
    lines = parse_lines(text)
    records = build_records(lines)
    assert len(records) == 1
    assert records[0].value == "First line\nSecond line\nThird line"


def test_conc_concatenation() -> None:
    text = "0 @N1@ NOTE First part\n1 CONC second part\n"
    lines = parse_lines(text)
    records = build_records(lines)
    assert len(records) == 1
    assert records[0].value == "First partsecond part"


def test_cont_on_child() -> None:
    text = "0 @I1@ INDI\n1 NOTE Line one\n2 CONT Line two\n2 CONT Line three\n"
    lines = parse_lines(text)
    records = build_records(lines)
    indi = records[0]
    note = indi.children[0]
    assert note.value == "Line one\nLine two\nLine three"


def test_find_methods() -> None:
    record = GedcomRecord(
        tag="INDI",
        value=None,
        xref="@I1@",
        children=[
            GedcomRecord(tag="NAME", value="John", xref=None),
            GedcomRecord(tag="SEX", value="M", xref=None),
            GedcomRecord(tag="NOTE", value="note 1", xref=None),
            GedcomRecord(tag="NOTE", value="note 2", xref=None),
        ],
    )
    assert record.find("NAME") is not None
    assert record.find("NAME").value == "John"  # type: ignore[union-attr]
    assert record.find("MISSING") is None
    assert record.find_value("SEX") == "M"
    assert record.find_value("MISSING") is None
    notes = record.find_all("NOTE")
    assert len(notes) == 2


def test_empty_records() -> None:
    records = build_records([])
    assert records == []


def test_cont_with_no_initial_value() -> None:
    text = "0 @N1@ NOTE\n1 CONT Some text\n"
    lines = parse_lines(text)
    records = build_records(lines)
    assert records[0].value == "\nSome text"
