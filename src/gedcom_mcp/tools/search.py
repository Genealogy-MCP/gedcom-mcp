# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Ariel Castagnini
"""Search meta-tool for operation discovery (MCP-31)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from gedcom_mcp.tools._registry import OperationDef, search_operations


def _format_operation(op: OperationDef) -> str:
    """Format a single operation for the search result.

    Args:
        op: Operation definition to format.

    Returns:
        Formatted string with name, summary, and parameters.
    """
    lines = [f"  {op.name}: {op.summary}"]
    if op.params:
        for p in op.params:
            req_marker = " (required)" if p.required else ""
            default = f" [default: {p.default}]" if p.default else ""
            lines.append(f"    - {p.name} ({p.param_type}{req_marker}{default}): {p.description}")
    return "\n".join(lines)


def register(mcp: FastMCP) -> None:
    """Register the search meta-tool on the given FastMCP server.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    async def search(query: str = "") -> str:
        """Discover available GEDCOM operations.

        Search for operations by keyword. Returns matching operation names,
        summaries, and parameter details. Use an empty query to list all
        available operations.

        After finding the operation you need, use the execute tool to run it.
        """
        results = search_operations(query)

        if not results:
            return (
                f"No operations found matching '{query}'. "
                "Try a broader search or use an empty query to list all operations."
            )

        header = f"Found {len(results)} operation(s)"
        if query:
            header += f" matching '{query}'"
        header += ":\n"

        formatted = [_format_operation(op) for op in results]
        return header + "\n".join(formatted)
