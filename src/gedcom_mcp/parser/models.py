# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Pydantic domain models for parsed GEDCOM data."""

from __future__ import annotations

from pydantic import BaseModel


class GedcomDate(BaseModel):
    """A parsed GEDCOM date with original text and extracted components."""

    original: str
    modifier: str | None = None
    day: int | None = None
    month: int | None = None
    year: int | None = None
    day2: int | None = None
    month2: int | None = None
    year2: int | None = None
    is_approximate: bool = False


class GedcomPlace(BaseModel):
    """A parsed GEDCOM place with hierarchical parts."""

    name: str
    parts: list[str] = []
    latitude: str | None = None
    longitude: str | None = None


class GedcomName(BaseModel):
    """A parsed GEDCOM personal name."""

    full: str
    given: str | None = None
    surname: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    nickname: str | None = None


class GedcomEvent(BaseModel):
    """A GEDCOM event (birth, death, marriage, etc.)."""

    event_type: str
    date: GedcomDate | None = None
    place: GedcomPlace | None = None
    description: str | None = None


class Individual(BaseModel):
    """A GEDCOM individual (INDI record)."""

    xref: str
    names: list[GedcomName] = []
    sex: str | None = None
    birth: GedcomEvent | None = None
    death: GedcomEvent | None = None
    other_events: list[GedcomEvent] = []
    family_spouse_xrefs: list[str] = []
    family_child_xref: str | None = None
    note_xrefs: list[str] = []
    source_xrefs: list[str] = []


class Family(BaseModel):
    """A GEDCOM family (FAM record)."""

    xref: str
    husband_xref: str | None = None
    wife_xref: str | None = None
    children_xrefs: list[str] = []
    marriage: GedcomEvent | None = None
    divorce: GedcomEvent | None = None
    other_events: list[GedcomEvent] = []
    note_xrefs: list[str] = []
    source_xrefs: list[str] = []


class GedcomSource(BaseModel):
    """A GEDCOM source (SOUR record)."""

    xref: str
    title: str | None = None
    author: str | None = None
    publication: str | None = None
    abbreviation: str | None = None
    text: str | None = None
    repository_xref: str | None = None


class GedcomNote(BaseModel):
    """A GEDCOM note (NOTE record)."""

    xref: str
    text: str


class GedcomHeader(BaseModel):
    """Metadata from the GEDCOM HEAD record."""

    source_system: str | None = None
    gedcom_version: str | None = None
    charset: str | None = None
    filename: str | None = None
    submitter: str | None = None


class GedcomDatabase(BaseModel):
    """In-memory database of all parsed GEDCOM records."""

    header: GedcomHeader = GedcomHeader()
    individuals: dict[str, Individual] = {}
    families: dict[str, Family] = {}
    sources: dict[str, GedcomSource] = {}
    notes: dict[str, GedcomNote] = {}
