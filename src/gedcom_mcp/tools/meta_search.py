# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Search meta-tool for operation discovery (MCP-ORG-3)."""

from __future__ import annotations

from mcp.types import TextContent
from pydantic import BaseModel

from gedcom_mcp.operations import search_operations, summarize_params


class SearchOperationsParams(BaseModel):
    """Parameters for the search meta-tool."""

    query: str = ""
    category: str | None = None


def _format_operation_entry(op: object, params_summary: list[dict[str, str | bool]]) -> str:
    """Format a single operation for the search result.

    Args:
        op: OperationEntry to format.
        params_summary: Output of summarize_params for this operation.

    Returns:
        Formatted markdown string.
    """
    # Access attributes directly (avoids importing OperationEntry here)
    lines = [f"  {op.name} [{op.category}]: {op.summary}"]  # type: ignore[attr-defined]
    if op.token_warning:  # type: ignore[attr-defined]
        lines.append(f"    Note: {op.token_warning}")  # type: ignore[attr-defined]
    if params_summary:
        for p in params_summary:
            req_marker = " (required)" if p["required"] else ""
            default = f" [default: {p['default']}]" if "default" in p else ""
            lines.append(
                f"    - {p['name']} ({p['type']}{req_marker}{default}): {p['description']}"
            )
    return "\n".join(lines)


async def search_operations_tool(arguments: dict[str, object]) -> list[TextContent]:
    """Discover available GEDCOM operations.

    Search for operations by keyword. Returns matching operation names,
    summaries, and parameter details. Use an empty query to list all
    available operations.

    After finding the operation you need, use the execute tool to run it.

    Args:
        arguments: Dict with 'query' (str) and optional 'category' (str).

    Returns:
        Formatted operation listings.
    """
    validated = SearchOperationsParams.model_validate(arguments)
    results = search_operations(validated.query, category=validated.category)

    if not results:
        text = (
            f"No operations found matching '{validated.query}'. "
            "Try a broader search or use an empty query to list all operations."
        )
        return [TextContent(type="text", text=text)]

    header = f"Found {len(results)} operation(s)"
    if validated.query:
        header += f" matching '{validated.query}'"
    if validated.category:
        header += f" in category '{validated.category}'"
    header += ":\n"

    formatted = [_format_operation_entry(op, summarize_params(op.params_schema)) for op in results]
    return [TextContent(type="text", text=header + "\n".join(formatted))]
