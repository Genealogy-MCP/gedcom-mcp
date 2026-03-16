# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Build Pydantic models from parsed GEDCOM records."""

from __future__ import annotations

import re

from gedcom_mcp.parser.models import (
    Family,
    GedcomDatabase,
    GedcomDate,
    GedcomEvent,
    GedcomHeader,
    GedcomName,
    GedcomNote,
    GedcomPlace,
    GedcomSource,
    Individual,
)
from gedcom_mcp.parser.records import GedcomRecord

_MONTH_MAP: dict[str, int] = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

_APPROX_MODIFIERS = {"ABT", "CAL", "EST"}
_RANGE_MODIFIERS = {"BET", "FROM"}
_SINGLE_MODIFIERS = {"BEF", "AFT"}

_DATE_RE = re.compile(
    r"(?:(\d{1,2})\s+)?"  # optional day
    r"(?:(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+)?"  # optional month
    r"(\d{1,4})"  # year
)


def _parse_date_component(text: str) -> tuple[int | None, int | None, int | None]:
    """Extract day, month, year from a date string fragment."""
    match = _DATE_RE.search(text)
    if not match:
        return None, None, None
    day = int(match.group(1)) if match.group(1) else None
    month = _MONTH_MAP.get(match.group(2)) if match.group(2) else None
    year = int(match.group(3)) if match.group(3) else None
    return day, month, year


def parse_date(value: str) -> GedcomDate:
    """Parse a GEDCOM date string into a GedcomDate model.

    Args:
        value: Raw GEDCOM date string (e.g. "1 JAN 1900", "ABT 1850", "BET 1900 AND 1910").

    Returns:
        Parsed GedcomDate with components extracted.
    """
    original = value
    upper = value.upper().strip()

    modifier: str | None = None
    is_approximate = False
    day2: int | None = None
    month2: int | None = None
    year2: int | None = None

    first_word = upper.split()[0] if upper else ""

    if first_word in _APPROX_MODIFIERS:
        modifier = first_word
        is_approximate = True
        upper = upper[len(first_word) :].strip()
    elif first_word in _SINGLE_MODIFIERS:
        modifier = first_word
        upper = upper[len(first_word) :].strip()
    elif first_word in _RANGE_MODIFIERS:
        modifier = first_word
        separator = " AND " if first_word == "BET" else " TO "
        parts = upper[len(first_word) :].strip().split(separator, 1)
        if len(parts) == 2:
            day, month, year = _parse_date_component(parts[0])
            day2, month2, year2 = _parse_date_component(parts[1])
            return GedcomDate(
                original=original,
                modifier=modifier,
                day=day,
                month=month,
                year=year,
                day2=day2,
                month2=month2,
                year2=year2,
                is_approximate=False,
            )
        upper = upper[len(first_word) :].strip()

    day, month, year = _parse_date_component(upper)
    return GedcomDate(
        original=original,
        modifier=modifier,
        day=day,
        month=month,
        year=year,
        day2=day2,
        month2=month2,
        year2=year2,
        is_approximate=is_approximate,
    )


def _parse_place(record: GedcomRecord) -> GedcomPlace | None:
    """Extract place from a PLAC child record."""
    plac = record.find("PLAC")
    if not plac or not plac.value:
        return None
    parts = [p.strip() for p in plac.value.split(",")]
    lat = None
    lon = None
    map_rec = plac.find("MAP")
    if map_rec:
        lat = map_rec.find_value("LATI")
        lon = map_rec.find_value("LONG")
    return GedcomPlace(name=plac.value, parts=parts, latitude=lat, longitude=lon)


def _parse_event(record: GedcomRecord, event_type: str) -> GedcomEvent | None:
    """Parse an event record into a GedcomEvent."""
    date_val = record.find_value("DATE")
    date = parse_date(date_val) if date_val else None
    place = _parse_place(record)
    description = record.find_value("TYPE")
    return GedcomEvent(event_type=event_type, date=date, place=place, description=description)


def _parse_name(record: GedcomRecord) -> GedcomName:
    """Parse a NAME record into a GedcomName model."""
    full = record.value or ""
    given = record.find_value("GIVN")
    surname = record.find_value("SURN")
    prefix = record.find_value("NPFX")
    suffix = record.find_value("NSFX")
    nickname = record.find_value("NICK")

    if not surname and "/" in full:
        start = full.index("/")
        end = full.index("/", start + 1) if full.count("/") >= 2 else len(full)
        surname = full[start + 1 : end].strip() or None

    if not given and full:
        slash_pos = full.find("/")
        if slash_pos > 0:
            given = full[:slash_pos].strip() or None

    return GedcomName(
        full=full, given=given, surname=surname, prefix=prefix, suffix=suffix, nickname=nickname
    )


def _build_individual(record: GedcomRecord) -> Individual:
    """Build an Individual from an INDI record."""
    xref = record.xref or ""
    names = [_parse_name(name_rec) for name_rec in record.find_all("NAME")]
    sex = record.find_value("SEX")

    birth: GedcomEvent | None = None
    death: GedcomEvent | None = None
    other_events: list[GedcomEvent] = []

    birt_rec = record.find("BIRT")
    if birt_rec:
        birth = _parse_event(birt_rec, "BIRT")

    deat_rec = record.find("DEAT")
    if deat_rec:
        death = _parse_event(deat_rec, "DEAT")

    event_tags = {
        "BURI",
        "CREM",
        "ADOP",
        "BAPM",
        "BARM",
        "BASM",
        "CHRA",
        "CONF",
        "FCOM",
        "ORDN",
        "NATU",
        "EMIG",
        "IMMI",
        "CENS",
        "PROB",
        "WILL",
        "GRAD",
        "RETI",
        "EVEN",
        "RESI",
        "OCCU",
        "EDUC",
    }
    for child in record.children:
        if child.tag in event_tags:
            evt = _parse_event(child, child.tag)
            if evt:
                other_events.append(evt)

    fams_xrefs = [rec.value for rec in record.find_all("FAMS") if rec.value]
    famc_rec = record.find("FAMC")
    famc_xref = famc_rec.value if famc_rec else None

    note_xrefs = [
        rec.value for rec in record.find_all("NOTE") if rec.value and rec.value.startswith("@")
    ]
    source_xrefs = [
        rec.value for rec in record.find_all("SOUR") if rec.value and rec.value.startswith("@")
    ]

    return Individual(
        xref=xref,
        names=names,
        sex=sex,
        birth=birth,
        death=death,
        other_events=other_events,
        family_spouse_xrefs=fams_xrefs,
        family_child_xref=famc_xref,
        note_xrefs=note_xrefs,
        source_xrefs=source_xrefs,
    )


def _build_family(record: GedcomRecord) -> Family:
    """Build a Family from a FAM record."""
    xref = record.xref or ""
    husb = record.find_value("HUSB")
    wife = record.find_value("WIFE")
    children = [rec.value for rec in record.find_all("CHIL") if rec.value]

    marriage: GedcomEvent | None = None
    divorce: GedcomEvent | None = None
    other_events: list[GedcomEvent] = []

    marr_rec = record.find("MARR")
    if marr_rec:
        marriage = _parse_event(marr_rec, "MARR")

    div_rec = record.find("DIV")
    if div_rec:
        divorce = _parse_event(div_rec, "DIV")

    for child in record.children:
        if child.tag in ("ENGA", "MARB", "MARC", "MARL", "MARS", "EVEN", "ANUL", "DIVF"):
            evt = _parse_event(child, child.tag)
            if evt:
                other_events.append(evt)

    note_xrefs = [
        rec.value for rec in record.find_all("NOTE") if rec.value and rec.value.startswith("@")
    ]
    source_xrefs = [
        rec.value for rec in record.find_all("SOUR") if rec.value and rec.value.startswith("@")
    ]

    return Family(
        xref=xref,
        husband_xref=husb,
        wife_xref=wife,
        children_xrefs=children,
        marriage=marriage,
        divorce=divorce,
        other_events=other_events,
        note_xrefs=note_xrefs,
        source_xrefs=source_xrefs,
    )


def _build_source(record: GedcomRecord) -> GedcomSource:
    """Build a GedcomSource from a SOUR record."""
    return GedcomSource(
        xref=record.xref or "",
        title=record.find_value("TITL"),
        author=record.find_value("AUTH"),
        publication=record.find_value("PUBL"),
        abbreviation=record.find_value("ABBR"),
        text=record.find_value("TEXT"),
        repository_xref=record.find_value("REPO"),
    )


def _build_note(record: GedcomRecord) -> GedcomNote:
    """Build a GedcomNote from a NOTE record."""
    return GedcomNote(xref=record.xref or "", text=record.value or "")


def _build_header(record: GedcomRecord) -> GedcomHeader:
    """Build a GedcomHeader from a HEAD record."""
    sour = record.find_value("SOUR")
    gedc = record.find("GEDC")
    version = gedc.find_value("VERS") if gedc else None
    char = record.find_value("CHAR")
    filename = record.find_value("FILE")
    subm_rec = record.find("SUBM")
    submitter = subm_rec.value if subm_rec else None
    return GedcomHeader(
        source_system=sour,
        gedcom_version=version,
        charset=char,
        filename=filename,
        submitter=submitter,
    )


def build_database(records: list[GedcomRecord]) -> GedcomDatabase:
    """Construct a GedcomDatabase from hierarchical records.

    Parses dates, names, places, and resolves cross-references.

    Args:
        records: Top-level GEDCOM records from build_records().

    Returns:
        Fully populated GedcomDatabase.
    """
    header = GedcomHeader()
    individuals: dict[str, Individual] = {}
    families: dict[str, Family] = {}
    sources: dict[str, GedcomSource] = {}
    notes: dict[str, GedcomNote] = {}

    for record in records:
        if record.tag == "HEAD":
            header = _build_header(record)
        elif record.tag == "INDI" and record.xref:
            individuals[record.xref] = _build_individual(record)
        elif record.tag == "FAM" and record.xref:
            families[record.xref] = _build_family(record)
        elif record.tag == "SOUR" and record.xref:
            sources[record.xref] = _build_source(record)
        elif record.tag == "NOTE" and record.xref:
            notes[record.xref] = _build_note(record)

    return GedcomDatabase(
        header=header,
        individuals=individuals,
        families=families,
        sources=sources,
        notes=notes,
    )
