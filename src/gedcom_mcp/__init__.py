# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
from gedcom_mcp.server import create_server


def main() -> None:
    """Entry point for the gedcom-mcp CLI."""
    mcp = create_server()
    mcp.run()


__all__ = ["main", "create_server"]
