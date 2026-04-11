# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Tests for GEDCOM encoding detection."""

from __future__ import annotations

from pathlib import Path

from gedcom_mcp.parser.encoding import decode_gedcom


def test_utf8_no_bom() -> None:
    text = "0 HEAD\n1 CHAR UTF-8\n0 TRLR\n"
    result = decode_gedcom(text.encode("utf-8"))
    assert "HEAD" in result
    assert "TRLR" in result


def test_utf8_with_bom() -> None:
    text = "0 HEAD\n1 CHAR UTF-8\n0 TRLR\n"
    raw = b"\xef\xbb\xbf" + text.encode("utf-8")
    result = decode_gedcom(raw)
    assert result.startswith("0 HEAD")


def test_utf16_le_bom() -> None:
    text = "0 HEAD\n1 CHAR UNICODE\n0 TRLR\n"
    raw = b"\xff\xfe" + text.encode("utf-16-le")
    result = decode_gedcom(raw)
    assert "HEAD" in result


def test_utf16_be_bom() -> None:
    text = "0 HEAD\n1 CHAR UNICODE\n0 TRLR\n"
    raw = b"\xfe\xff" + text.encode("utf-16-be")
    result = decode_gedcom(raw)
    assert "HEAD" in result


def test_latin1_via_char_tag() -> None:
    text = "0 HEAD\n1 CHAR ANSI\n0 @I1@ INDI\n1 NAME Ren\u00e9 /Descartes/\n0 TRLR\n"
    raw = text.encode("latin-1")
    result = decode_gedcom(raw)
    assert "Ren\u00e9" in result


def test_ascii_default() -> None:
    text = "0 HEAD\n1 CHAR ASCII\n0 TRLR\n"
    result = decode_gedcom(text.encode("ascii"))
    assert "HEAD" in result


def test_no_char_tag_defaults_utf8() -> None:
    text = "0 HEAD\n1 SOUR Test\n0 TRLR\n"
    result = decode_gedcom(text.encode("utf-8"))
    assert "HEAD" in result


def test_non_ascii_fixture(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "non_ascii.ged").read_bytes()
    result = decode_gedcom(raw)
    assert "Ren\u00e9" in result
    assert "Garc\u00eda" in result
    assert "M\u00fcller" in result
