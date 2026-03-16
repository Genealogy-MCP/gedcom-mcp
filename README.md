# gedcom-mcp

MCP server for querying local [GEDCOM](https://en.wikipedia.org/wiki/GEDCOM) genealogy files through AI assistants. Load any `.ged` file and search, browse, and traverse your family tree without leaving your AI workflow.

Part of the [Genealogy-MCP](https://github.com/Genealogy-MCP) organization.

## Available Tools

| Tool | Description |
|---|---|
| `load_file` | Load and parse a GEDCOM (.ged) file into memory |
| `search_persons` | Search individuals by name, dates, place, sex |
| `get_person` | Retrieve a specific individual by cross-reference ID |
| `get_family` | Retrieve a family record (accepts family or individual xref) |
| `get_ancestors` | Get the ancestor tree for an individual |
| `get_descendants` | Get the descendant tree for an individual |
| `get_stats` | Get statistics about the loaded GEDCOM file |

## Configuration

All settings are optional with sensible defaults.

| Environment Variable | Default | Description |
|---|---|---|
| `GEDCOM_MAX_FILE_SIZE_MB` | `100` | Maximum allowed GEDCOM file size in MB |
| `GEDCOM_DEFAULT_ANCESTOR_DEPTH` | `5` | Default ancestor traversal depth |
| `GEDCOM_DEFAULT_DESCENDANT_DEPTH` | `5` | Default descendant traversal depth |
| `GEDCOM_MAX_TREE_DEPTH` | `50` | Hard ceiling on traversal depth |
| `GEDCOM_MAX_SEARCH_RESULTS` | `100` | Maximum search results returned |
| `GEDCOM_ALLOWED_BASE_DIRS` | _(empty)_ | Comma-separated allowed directories for file loading |

## Setup: Claude Desktop

Add to your `claude_desktop_config.json`:

### Using uv (local)

```json
{
  "mcpServers": {
    "gedcom": {
      "command": "uv",
      "args": ["--directory", "/path/to/gedcom-mcp", "run", "gedcom-mcp"],
      "env": {
        "GEDCOM_ALLOWED_BASE_DIRS": "/path/to/your/gedcom/files"
      }
    }
  }
}
```

### Using Docker

```json
{
  "mcpServers": {
    "gedcom": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/your/gedcom/files:/data:ro",
        "-e", "GEDCOM_ALLOWED_BASE_DIRS=/data",
        "ghcr.io/genealogy-mcp/gedcom-mcp"
      ]
    }
  }
}
```

## Setup: Claude Code

### Using uv (local)

```bash
claude mcp add gedcom -- uv --directory /path/to/gedcom-mcp run gedcom-mcp
```

### Using Docker

```bash
claude mcp add gedcom -- docker run -i --rm \
  -v /path/to/your/gedcom/files:/data:ro \
  -e GEDCOM_ALLOWED_BASE_DIRS=/data \
  ghcr.io/genealogy-mcp/gedcom-mcp
```

## Development

```bash
# Install dependencies
make install

# Run tests with coverage
make test

# Run all checks (lint + type-check + test + audit)
make ci

# Format code
make format

# Run via stdio transport
make run-stdio

# Run via streamable-http on port 8000
make run
```

## License

AGPL-3.0-only
