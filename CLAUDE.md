# gedcom-mcp -- Development Reference

## Commands

```bash
make               # show help (default target)
make install       # uv sync --group dev
make test          # coverage run + report (branch coverage >= 80%)
make lint          # ruff check src tests scripts
make format        # ruff format src tests scripts + ruff check --fix
make typecheck     # pyright src (strict mode)
make audit         # pip-audit
make ci            # lint + typecheck + test + audit
make run           # streamable-http on port 8000
make run-stdio     # stdio transport
```

## Architecture

This server uses the Code Mode architecture (MCP-29): exactly 2 meta-tools
(`search` + `execute`) instead of individual per-operation tools. The LLM
discovers operations via `search` and runs them via `execute`.

```
src/gedcom_mcp/
  __init__.py       # main() entry point + create_server()
  __main__.py       # python -m gedcom_mcp
  settings.py       # pydantic-settings; all env vars prefixed GEDCOM_
  server.py         # AppContext (holds parsed database), app_lifespan, create_server
  parser/
    __init__.py     # parse_file() pipeline: decode -> parse_lines -> build_records -> build_database
    encoding.py     # Charset detection (BOM + CHAR tag), decode to Unicode
    lines.py        # GedcomLine dataclass + parse_lines() regex parser
    records.py      # GedcomRecord tree builder + CONT/CONC merging
    models.py       # Pydantic models: Individual, Family, GedcomSource, GedcomNote, etc.
    builder.py      # Record-to-model construction + date/name/place parsing
  tools/
    _errors.py      # McpToolError, raise_tool_error, get_app_context, require_database
    _formatting.py  # Pure helpers: matchers, formatters, BFS traversals, path validation
    _handlers.py    # 7 handle_*() async functions (orchestration + error handling)
    _registry.py    # OperationDef + OPERATION_REGISTRY + Pydantic param models + search_operations()
    search.py       # search meta-tool: operation discovery by keyword (MCP-31)
    execute.py      # execute meta-tool: validated dispatch to handlers (MCP-32)
```

### Tools (2 meta-tools, 7 operations)

Tools: `search` (operation discovery), `execute` (operation dispatch)

Operations: `load_file`, `search_persons`, `get_person`, `get_family`,
`get_ancestors`, `get_descendants`, `get_stats`

### Data Flow

```
Raw .ged bytes -> encoding.py (detect charset, decode)
  -> lines.py (parse each line into GedcomLine)
  -> records.py (group into hierarchical tree, merge CONT/CONC)
  -> builder.py (construct Pydantic models, parse dates/names/places)
  -> GedcomDatabase (in-memory dict[str, Model] keyed by xref)
```

### Statefulness

Unlike wikitree-mcp (stateless API proxy), gedcom-mcp is stateful:
- `AppContext.database` starts as `None`
- The `load_file` operation populates it by parsing a `.ged` file
- All other operations guard with `require_database()` which raises `McpToolError` if no file is loaded
- Calling `load_file` again replaces the previously loaded database

## Key Settings

| Var | Default | Notes |
|---|---|---|
| `GEDCOM_MAX_FILE_SIZE_MB` | `100` | OOM protection |
| `GEDCOM_DEFAULT_ANCESTOR_DEPTH` | `5` | Overridable per-call |
| `GEDCOM_DEFAULT_DESCENDANT_DEPTH` | `5` | Overridable per-call |
| `GEDCOM_MAX_TREE_DEPTH` | `50` | Hard ceiling for traversal |
| `GEDCOM_MAX_SEARCH_RESULTS` | `100` | MCP-24 ceiling |
| `GEDCOM_ALLOWED_BASE_DIRS` | _(empty)_ | Comma-separated; empty = allow all paths |

No required env vars. This server is fully offline -- no network calls, no authentication.

## GEDCOM Format Quirks

- **CONT/CONC**: Multi-line text uses `CONT` (newline + text) and `CONC` (concatenation without newline)
- **Date modifiers**: ABT, CAL, EST (approximate), BEF, AFT (bounded), BET...AND (range), FROM...TO (period)
- **Name format**: Surnames delimited by slashes: `John /Smith/`
- **Cross-references**: All entities identified by xrefs like `@I1@`, `@F1@`, `@S1@`
- **Encodings**: UTF-8 (with/without BOM), ANSEL (mapped to Latin-1), ANSI, ASCII, UNICODE, IBMPC, MACINTOSH

## Testing

### Test structure
- `tests/test_parser_*.py` -- Parser unit tests (lines, records, encoding, builder, models)
- `tests/test_settings.py` -- Settings validation
- `tests/test_errors.py` -- Error utility tests
- `tests/test_registry.py` -- Registry completeness, search matching, param validation
- `tests/test_search.py` -- `search` meta-tool integration tests via FastMCP
- `tests/test_execute.py` -- `execute` meta-tool: dispatch, validation, error handling
- `tests/test_handlers.py` -- Handler functions called directly (no MCP framework)

### Fixtures (`tests/fixtures/`)
- `minimal.ged` -- 3 individuals, 1 family (happy path)
- `medium.ged` -- 15 individuals, 5 families, 4 generations, source, note
- `empty.ged` -- Valid HEAD+TRLR, no data records
- `edge_cases.ged` -- CONT/CONC, missing fields, ABT/BET dates
- `non_ascii.ged` -- Latin-1 encoded with accented names

### Mock approach
Handler and tool tests create `MagicMock` contexts with `AppContext` containing parsed
fixture databases. No network mocking needed (offline server). Helper: `_find_tool(mcp, name)`
extracts tools from the FastMCP internal registry for integration tests.

## CI

GitHub Actions: 3-job pipeline (lint+typecheck, test matrix py3.10-3.13, security audit).
No live tests -- everything is local file parsing.

## Security

- File paths validated: must be absolute, `.ged` extension, within `allowed_base_dirs`
- Path traversal (`..`) rejected after resolution
- File size checked against `max_file_size_mb` before reading
- Only file basename exposed in responses (MCP-19)
- No secrets, no network calls, no external dependencies at runtime
