# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-03-16

### Added

- GEDCOM 5.5.1/7.0 parser pipeline: encoding detection, line parsing, record tree
  builder, CONT/CONC merging, and Pydantic model construction
- 7 MCP tools: `load_file`, `search_persons`, `get_person`, `get_family`,
  `get_ancestors`, `get_descendants`, `get_stats`
- Stateful `AppContext` holding the parsed in-memory `GedcomDatabase`; all tools
  guard with `require_database()` before use
- Path security: absolute-path enforcement, `.ged` extension check, optional
  `GEDCOM_ALLOWED_BASE_DIRS` allowlist, path-traversal rejection, file-size limit
- Multi-encoding support: UTF-8 (BOM + BOM-less), ANSEL, ANSI, ASCII, UNICODE,
  IBMPC, MACINTOSH via charset detection from BOM and CHAR tag
- Full test suite: 109 tests, 92% branch coverage across 5 fixture files
- CI pipeline: lint+typecheck, pytest matrix (py3.10–3.13), pip-audit security audit
- Dockerfile (multi-stage, streamable-HTTP on port 8000) and stdio transport
- Pre-commit hooks: ruff, copyright-header, file-length, no-emojis
