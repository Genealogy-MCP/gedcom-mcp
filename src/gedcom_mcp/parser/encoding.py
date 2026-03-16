# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Charset detection and decoding for GEDCOM files."""

from __future__ import annotations

import re

_CHAR_TAG_RE = re.compile(rb"^\d+\s+CHAR\s+(.+?)[\r\n]", re.MULTILINE)

_CHARSET_MAP: dict[str, str] = {
    "UTF-8": "utf-8",
    "UNICODE": "utf-8",
    "ASCII": "ascii",
    "ANSI": "latin-1",
    "ANSEL": "latin-1",
    "IBMPC": "cp437",
    "MACINTOSH": "mac-roman",
}


def _detect_encoding(raw: bytes) -> tuple[str, int]:
    """Detect encoding from BOM or CHAR tag.

    Args:
        raw: Raw bytes from a .ged file.

    Returns:
        Tuple of (encoding_name, bom_length_to_skip).
    """
    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8", 3
    if raw[:2] == b"\xff\xfe":
        return "utf-16-le", 2
    if raw[:2] == b"\xfe\xff":
        return "utf-16-be", 2

    match = _CHAR_TAG_RE.search(raw[:2048])
    if match:
        charset = match.group(1).decode("ascii", errors="ignore").strip().upper()
        encoding = _CHARSET_MAP.get(charset, "utf-8")
        return encoding, 0

    return "utf-8", 0


def decode_gedcom(raw: bytes) -> str:
    """Detect encoding from BOM or CHAR tag, then decode to Unicode.

    Args:
        raw: Raw bytes from a .ged file.

    Returns:
        Decoded Unicode text.
    """
    encoding, bom_skip = _detect_encoding(raw)
    return raw[bom_skip:].decode(encoding, errors="replace")
