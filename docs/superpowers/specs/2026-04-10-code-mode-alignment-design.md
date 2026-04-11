# Refactor: Align Code Mode Internals with gramps-mcp Canonical Pattern

**Issue:** [gedcom-mcp#6](https://gitlab.com/genealogy-mcp/gedcom-mcp/-/work_items/6)
**Date:** 2026-04-10
**Status:** Approved

## Context

gedcom-mcp and gramps-mcp both implement MCP-ORG-1 (Code Mode: 2 meta-tools + operation
registry), but their internal structures have diverged across several dimensions:

- Registry dataclass: `OperationDef` (gedcom) vs `OperationEntry` (gramps)
- Handler binding: separate `HANDLER_MAP` dict vs handler embedded in registry entry
- Parameter validation: separate `PARAM_MODELS` dict vs `params_schema` on entry
- File organization: single `_handlers.py` vs domain-grouped handler files
- Search algorithm: simple token-in-searchable vs weighted scoring (+3/+2/+1)
- Return types: handlers return `str` vs `list[TextContent]`

This refactor aligns gedcom-mcp with the canonical gramps-mcp pattern while preserving
the identical external MCP interface (2 tools, 7 operations). No version bump required.

## Architecture After Refactor

```
src/gedcom_mcp/
  __init__.py         # unchanged
  __main__.py         # unchanged
  settings.py         # unchanged
  server.py           # updated: _META_TOOLS dict, dynamic registration
  operations.py       # NEW: OperationEntry, OPERATION_REGISTRY, search_operations, summarize_params
  parser/             # unchanged (entire directory)
  tools/
    __init__.py       # updated: re-export handler functions (not meta-tools)
    _errors.py        # unchanged
    _formatting.py    # unchanged
    meta_search.py    # RENAMED from search.py; updated imports + uses summarize_params
    meta_execute.py   # RENAMED from execute.py; handler from registry entry, no HANDLER_MAP
    setup.py          # NEW: handle_load_file (from _handlers.py)
    search_ops.py     # NEW: handle_search_persons (from _handlers.py)
    read_ops.py       # NEW: handle_get_person, handle_get_family (from _handlers.py)
    analysis.py       # NEW: handle_get_ancestors, handle_get_descendants, handle_get_stats (from _handlers.py)
```

**Deleted files:**
- `tools/_registry.py` (consolidated into `operations.py`)
- `tools/_handlers.py` (split into domain files)

## Component Design

### 1. `operations.py` (root-level, ~300 lines)

The single source of truth for all operations.

```python
@dataclass(frozen=True)
class OperationEntry:
    name: str
    summary: str
    description: str
    category: str              # "setup" | "search" | "read" | "analysis"
    params_schema: type        # Pydantic BaseModel subclass
    handler: Callable[..., Any]  # async (ctx, **params) -> list[TextContent]
    read_only: bool
    destructive: bool
    token_warning: str | None = None
```

**OPERATION_REGISTRY** maps operation name to `OperationEntry`. Handler function
references are imported from domain files and bound directly:

```python
from gedcom_mcp.tools.setup import handle_load_file
from gedcom_mcp.tools.search_ops import handle_search_persons
from gedcom_mcp.tools.read_ops import handle_get_person, handle_get_family
from gedcom_mcp.tools.analysis import handle_get_ancestors, handle_get_descendants, handle_get_stats

OPERATION_REGISTRY: dict[str, OperationEntry] = {
    "load_file": OperationEntry(
        name="load_file",
        ...
        handler=handle_load_file,
        ...
    ),
    ...
}
```

**Pydantic param models** remain in this file (co-located with registry entries).

**`search_operations(query, category=None, max_results=10)`** uses weighted scoring:
- +3: exact operation name match
- +2: query token found in operation name
- +1: query token found in summary or description
- Optional category filter
- Returns sorted `list[OperationEntry]`

**`summarize_params(schema)`** introspects `model_fields` to produce LLM-friendly
parameter descriptions (name, type, required, description).

### 2. Handler Domain Files

Each handler is an async function with signature:
```python
async def handle_<name>(ctx: Context[Any, Any, Any], **params) -> list[TextContent]
```

Handlers return `list[TextContent]` (from `mcp.types`) instead of `str`.
The wrapping is trivial: `[TextContent(type="text", text=formatted_string)]`.

| File | Handlers | Category |
|---|---|---|
| `tools/setup.py` | `handle_load_file` | setup |
| `tools/search_ops.py` | `handle_search_persons` | search |
| `tools/read_ops.py` | `handle_get_person`, `handle_get_family` | read |
| `tools/analysis.py` | `handle_get_ancestors`, `handle_get_descendants`, `handle_get_stats` | analysis |

Internal logic (filtering, formatting, BFS traversal) remains unchanged.
Only the return type changes from `str` to `list[TextContent]`.

### 3. `tools/meta_search.py` (renamed from `search.py`)

- Exports `SearchOperationsParams` (Pydantic model) and `search_operations_tool` (async handler)
- No more `register(mcp)` pattern — server.py handles registration via `_META_TOOLS`
- Imports `search_operations` and `summarize_params` from `operations.py`
- Uses `summarize_params(entry.params_schema)` to format parameter info
- Handler signature: `async def search_operations_tool(arguments: dict) -> list[TextContent]`
- Accepts optional `category` filter parameter
- Returns formatted markdown showing matching operations

### 4. `tools/meta_execute.py` (renamed from `execute.py`)

- Exports `ExecuteOperationParams` (Pydantic model) and `execute_operation_tool` (async handler)
- No more `register(mcp)` pattern — server.py handles registration via `_META_TOOLS`
- Imports `OPERATION_REGISTRY` from `operations.py`
- No more `HANDLER_MAP` or `PARAM_MODELS` — both come from `OperationEntry`
- Two-stage validation:
  1. Top-level: operation name exists in registry
  2. Per-operation: `entry.params_schema(**params)` validates parameters
- Dispatch: `await entry.handler(ctx, **validated.model_dump(exclude_none=True))`
- Close-match suggestions on unknown operation (using `difflib.get_close_matches`)

### 5. `server.py` Updates

Adopts `_META_TOOLS` dict pattern:
```python
from gedcom_mcp.tools.meta_search import SearchOperationsParams, search_operations_tool
from gedcom_mcp.tools.meta_execute import ExecuteOperationParams, execute_operation_tool
from gedcom_mcp.operations import OPERATION_REGISTRY

_META_TOOLS = {
    "search": {
        "schema": SearchOperationsParams,
        "handler": search_operations_tool,
        "description": "...",
        "annotations": ToolAnnotations(readOnlyHint=True, ...),
    },
    "execute": {
        "schema": ExecuteOperationParams,
        "handler": execute_operation_tool,
        "description": "...",
        "annotations": ToolAnnotations(readOnlyHint=False, ...),
    },
}
```

Tool count derived at runtime: `len(_META_TOOLS)`, `len(OPERATION_REGISTRY)`.

### 6. `tools/__init__.py`

Re-exports handler functions only (not meta-tools) to avoid circular imports:
```python
from .setup import handle_load_file
from .search_ops import handle_search_persons
from .read_ops import handle_get_person, handle_get_family
from .analysis import handle_get_ancestors, handle_get_descendants, handle_get_stats
```

`operations.py` imports from `tools/` submodules directly (not via `__init__`).

## Test Plan

### Test file mapping

| Current | New | Purpose |
|---|---|---|
| `test_registry.py` | `test_operations.py` | Registry completeness, search scoring, summarize_params |
| `test_search.py` | `test_meta_search.py` | search meta-tool via FastMCP |
| `test_execute.py` | `test_meta_execute.py` | Dispatch, validation, error handling, close-match suggestions |
| `test_handlers.py` | `test_setup.py` | load_file handler |
| `test_handlers.py` | `test_search_ops.py` | search_persons handler |
| `test_handlers.py` | `test_read_ops.py` | get_person, get_family handlers |
| `test_handlers.py` | `test_analysis.py` | get_ancestors, get_descendants, get_stats handlers |

### Unchanged test files

- `test_parser_*.py` (5 files) — parser is untouched
- `test_settings.py` — settings are untouched
- `test_errors.py` — error utilities are untouched
- `conftest.py` — shared fixtures unchanged
- `tests/fixtures/` — all .ged files unchanged

### Key test assertions for `test_operations.py`

- Registry contains exactly 7 operations
- Every entry has callable handler and valid Pydantic params_schema
- Every entry has non-empty summary, description, valid category
- `read_only` and `destructive` flags are correctly set
- `search_operations("")` returns all 7 operations
- `search_operations("ancestor")` returns `get_ancestors` first (highest score)
- `summarize_params(GetPersonParams)` returns correct field metadata
- Category filter works: `search_operations("", category="read")` returns 2 ops

## Verification

1. `make lint` — passes (ruff check + format)
2. `make typecheck` — passes (pyright strict)
3. `make test` — passes with >= 80% branch coverage
4. `make ci` — full pipeline passes
5. Manual smoke test: `make run-stdio`, call `search` then `execute` with each operation

## Risk Assessment

- **Low risk**: External interface unchanged, no version bump
- **Circular import prevention**: `operations.py` imports from `tools/<domain>.py`;
  `meta_search.py`/`meta_execute.py` import from `operations.py`;
  `tools/__init__.py` re-exports domain handlers only (not meta-tools)
- **Coverage**: Splitting `test_handlers.py` into 4 files maintains same assertion
  count; no test logic removed
