# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Tests for GEDCOM builder (record -> model conversion)."""

from __future__ import annotations

from pathlib import Path

from gedcom_mcp.parser import parse_file


def test_minimal_fixture(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "minimal.ged").read_bytes()
    db = parse_file(raw)
    assert len(db.individuals) == 3
    assert len(db.families) == 1
    assert db.header.gedcom_version == "5.5.1"
    assert db.header.charset == "UTF-8"


def test_minimal_individuals(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "minimal.ged").read_bytes()
    db = parse_file(raw)
    john = db.individuals["@I1@"]
    assert john.names[0].given == "John"
    assert john.names[0].surname == "Smith"
    assert john.sex == "M"
    assert john.birth is not None
    assert john.birth.date is not None
    assert john.birth.date.year == 1900
    assert john.birth.date.month == 1
    assert john.birth.date.day == 1
    assert john.birth.place is not None
    assert john.birth.place.name == "London, England"
    assert john.death is not None
    assert john.death.date is not None
    assert john.death.date.year == 1970
    assert john.family_spouse_xrefs == ["@F1@"]


def test_minimal_family(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "minimal.ged").read_bytes()
    db = parse_file(raw)
    fam = db.families["@F1@"]
    assert fam.husband_xref == "@I1@"
    assert fam.wife_xref == "@I2@"
    assert fam.children_xrefs == ["@I3@"]
    assert fam.marriage is not None
    assert fam.marriage.date is not None
    assert fam.marriage.date.year == 1924


def test_child_famc_link(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "minimal.ged").read_bytes()
    db = parse_file(raw)
    james = db.individuals["@I3@"]
    assert james.family_child_xref == "@F1@"


def test_empty_fixture(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "empty.ged").read_bytes()
    db = parse_file(raw)
    assert len(db.individuals) == 0
    assert len(db.families) == 0
    assert db.header.gedcom_version == "5.5.1"


def test_edge_cases_cont_conc(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "edge_cases.ged").read_bytes()
    db = parse_file(raw)
    assert len(db.individuals) >= 3


def test_approximate_date(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "edge_cases.ged").read_bytes()
    db = parse_file(raw)
    indi2 = db.individuals["@I2@"]
    assert indi2.birth is not None
    assert indi2.birth.date is not None
    assert indi2.birth.date.modifier == "ABT"
    assert indi2.birth.date.year == 1850
    assert indi2.birth.date.is_approximate is True


def test_range_date(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "edge_cases.ged").read_bytes()
    db = parse_file(raw)
    indi3 = db.individuals["@I3@"]
    assert indi3.birth is not None
    assert indi3.birth.date is not None
    assert indi3.birth.date.modifier == "BET"
    assert indi3.birth.date.year == 1900
    assert indi3.birth.date.year2 == 1910


def test_medium_fixture(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "medium.ged").read_bytes()
    db = parse_file(raw)
    assert len(db.individuals) == 15
    assert len(db.families) == 5
    assert len(db.sources) == 1
    assert len(db.notes) == 1


def test_medium_source(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "medium.ged").read_bytes()
    db = parse_file(raw)
    src = db.sources["@SRC1@"]
    assert src.title == "Massachusetts Vital Records"
    assert src.author == "Commonwealth of Massachusetts"


def test_non_ascii_names(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "non_ascii.ged").read_bytes()
    db = parse_file(raw)
    rene = db.individuals["@I1@"]
    assert rene.names[0].given == "Ren\u00e9"
    assert rene.names[0].surname == "Descartes"
    maria = db.individuals["@I2@"]
    assert maria.names[0].given == "Mar\u00eda"
    assert maria.names[0].surname == "Garc\u00eda"


def test_header_fields(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "medium.ged").read_bytes()
    db = parse_file(raw)
    assert db.header.source_system == "Test"
    assert db.header.filename == "medium.ged"
