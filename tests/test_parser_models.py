# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Tests for GEDCOM Pydantic models."""

from __future__ import annotations

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


def test_gedcom_date_simple() -> None:
    d = GedcomDate(original="1 JAN 1900", year=1900, month=1, day=1)
    assert d.year == 1900
    assert d.is_approximate is False


def test_gedcom_date_approximate() -> None:
    d = GedcomDate(original="ABT 1850", modifier="ABT", year=1850, is_approximate=True)
    assert d.modifier == "ABT"
    assert d.is_approximate is True


def test_gedcom_date_range() -> None:
    d = GedcomDate(
        original="BET 1 JAN 1900 AND 31 DEC 1910",
        modifier="BET",
        year=1900,
        month=1,
        day=1,
        year2=1910,
        month2=12,
        day2=31,
    )
    assert d.year2 == 1910


def test_gedcom_place() -> None:
    p = GedcomPlace(name="London, England", parts=["London", "England"])
    assert len(p.parts) == 2


def test_gedcom_place_with_coords() -> None:
    p = GedcomPlace(name="London", latitude="51.5074", longitude="-0.1278")
    assert p.latitude == "51.5074"


def test_gedcom_name() -> None:
    n = GedcomName(full="John /Smith/", given="John", surname="Smith")
    assert n.full == "John /Smith/"
    assert n.surname == "Smith"


def test_individual_defaults() -> None:
    i = Individual(xref="@I1@")
    assert i.names == []
    assert i.sex is None
    assert i.birth is None
    assert i.death is None
    assert i.family_spouse_xrefs == []
    assert i.family_child_xref is None


def test_family_defaults() -> None:
    f = Family(xref="@F1@")
    assert f.husband_xref is None
    assert f.wife_xref is None
    assert f.children_xrefs == []


def test_source_defaults() -> None:
    s = GedcomSource(xref="@SRC1@")
    assert s.title is None
    assert s.author is None


def test_note() -> None:
    n = GedcomNote(xref="@N1@", text="Some note text")
    assert n.text == "Some note text"


def test_header_defaults() -> None:
    h = GedcomHeader()
    assert h.source_system is None
    assert h.gedcom_version is None


def test_database_defaults() -> None:
    db = GedcomDatabase()
    assert db.individuals == {}
    assert db.families == {}
    assert db.sources == {}
    assert db.notes == {}


def test_database_dict_keyed_by_xref() -> None:
    db = GedcomDatabase(
        individuals={"@I1@": Individual(xref="@I1@")},
        families={"@F1@": Family(xref="@F1@")},
    )
    assert "@I1@" in db.individuals
    assert "@F1@" in db.families


def test_individual_serialization() -> None:
    i = Individual(
        xref="@I1@",
        names=[GedcomName(full="John /Smith/", given="John", surname="Smith")],
        sex="M",
        birth=GedcomEvent(
            event_type="BIRT",
            date=GedcomDate(original="1 JAN 1900", year=1900, month=1, day=1),
            place=GedcomPlace(name="London", parts=["London"]),
        ),
    )
    data = i.model_dump()
    assert data["xref"] == "@I1@"
    assert data["names"][0]["surname"] == "Smith"
    assert data["birth"]["date"]["year"] == 1900
