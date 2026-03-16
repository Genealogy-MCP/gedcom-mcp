# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""File loading tool for GEDCOM files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.parser import parse_file
from gedcom_mcp.tools._errors import McpToolError, get_app_context, raise_tool_error


def _validate_path(file_path: str, allowed_base_dirs: str, max_size_mb: int) -> Path:
    """Validate and resolve a file path securely.

    Args:
        file_path: User-provided file path string.
        allowed_base_dirs: Comma-separated allowed base directories (empty = allow all).
        max_size_mb: Maximum file size in megabytes.

    Returns:
        Resolved Path object.

    Raises:
        McpToolError: If validation fails.
    """
    path = Path(file_path)

    if not path.is_absolute():
        raise McpToolError(
            f"Path must be absolute: '{file_path}'. Provide the full path to the .ged file."
        )

    resolved = path.resolve()

    if ".." in resolved.parts:
        raise McpToolError("Path traversal is not allowed.")

    if resolved.suffix.lower() != ".ged":
        raise McpToolError(
            f"File must have a .ged extension, got '{resolved.suffix}'. "
            "Only GEDCOM files are supported."
        )

    if allowed_base_dirs:
        allowed = [Path(d.strip()).resolve() for d in allowed_base_dirs.split(",") if d.strip()]
        if allowed and not any(str(resolved).startswith(str(base)) for base in allowed):
            raise McpToolError(
                "File is outside allowed directories. Check GEDCOM_ALLOWED_BASE_DIRS configuration."
            )

    if not resolved.exists():
        raise McpToolError(
            f"File not found: '{resolved.name}'. Verify the path is correct and the file exists."
        )

    size_mb = resolved.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise McpToolError(
            f"File size ({size_mb:.1f} MB) exceeds the {max_size_mb} MB limit. "
            "Adjust GEDCOM_MAX_FILE_SIZE_MB if needed."
        )

    return resolved


def register(mcp: FastMCP) -> None:
    """Register file management tools."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    async def load_file(ctx: Context[Any, Any, Any], file_path: str) -> str:
        """Load and parse a GEDCOM (.ged) file into memory.

        This must be called before any other tool. Loads the file, parses all
        records, and makes them available for querying. Calling again replaces
        the previously loaded file.

        Requires an absolute file path. Returns a summary with the filename,
        GEDCOM version, and record counts.
        """
        app_ctx = get_app_context(ctx)
        try:
            resolved = _validate_path(
                file_path,
                app_ctx.settings.allowed_base_dirs,
                app_ctx.settings.max_file_size_mb,
            )
            raw = resolved.read_bytes()
            database = parse_file(raw)
            app_ctx.database = database

            basename = resolved.name
            version = database.header.gedcom_version or "unknown"
            lines = [
                f"Loaded: {basename}",
                f"GEDCOM version: {version}",
                f"Individuals: {len(database.individuals)}",
                f"Families: {len(database.families)}",
                f"Sources: {len(database.sources)}",
                f"Notes: {len(database.notes)}",
            ]
            return "\n".join(lines)
        except McpToolError:
            raise
        except Exception as e:
            raise_tool_error(e, "file load")
