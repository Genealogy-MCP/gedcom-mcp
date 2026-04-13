# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0] - 2026-04-13

### Changed

- Migrate CI pipeline to shared templates from facastagnini/ci-templates
- Migrate to mcp-codemode library for Code Mode framework (search + execute
  meta-tools, OperationEntry, error handling)

### Removed

- Local OperationEntry, search_operations, summarize_params — now from library
- tools/meta_search.py and tools/meta_execute.py — replaced by library


## [2.0.0] - 2026-03-19

### Changed

- **BREAKING:** Replace 7 individual MCP tools with 2 meta-tools (`search` +
  `execute`) following the Code Mode architecture (MCP-29). All 7 operations
  remain available via the `execute` dispatcher.
- LLM context overhead reduced from ~7K tokens (7 tool schemas) to ~2K tokens
  (2 tool schemas).
- `require_database()` error message updated to reference "Execute the
  'load_file' operation" instead of "Use the load_file tool".

### Added

- Operation registry (`_registry.py`): typed metadata for all 7 operations with
  keyword search and Pydantic parameter validation models.
- `search` tool: discovers operations by keyword matching against name, summary,
  and tags. Empty query returns all operations.
- `execute` tool: validates parameters via Pydantic, checks database guard for
  operations that require it, and dispatches to the appropriate handler.
- `_formatting.py`: extracted pure helper functions (matchers, formatters, BFS
  traversals, path validation) for independent testability.
- `_handlers.py`: 7 standalone async handler functions decoupled from the MCP
  framework.
- 151 tests (up from 109), 92% branch coverage.

### Removed

- Individual tool modules: `file_management.py`, `persons.py`, `families.py`,
  `genealogy.py`, `stats.py`.

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
