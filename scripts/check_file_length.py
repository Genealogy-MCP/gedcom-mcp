# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Federico Castagnini
"""Pre-commit hook to check that Python files don't exceed 500 lines."""

from __future__ import annotations

import sys
from pathlib import Path


def check_file_length(file_path: Path, max_lines: int = 500) -> bool:
    """
    Check if a file exceeds the maximum line count.

    Args:
        file_path: Path to the file to check.
        max_lines: Maximum allowed lines (default 500).

    Returns:
        True if file is within limits, False otherwise.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
            line_count = len(lines)

        if line_count > max_lines:
            print(f"ERROR: {file_path} has {line_count} lines (max: {max_lines})")
            print("Consider refactoring into smaller modules.")
            return False

        return True
    except Exception as e:
        print(f"ERROR: Could not read {file_path}: {e}")
        return False


def main() -> int:
    """
    Check all provided files for length compliance.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if len(sys.argv) < 2:
        print("Usage: python check_file_length.py <file1> [file2] ...")
        return 1

    all_passed = True

    for file_path_str in sys.argv[1:]:
        file_path = Path(file_path_str)

        if file_path.suffix != ".py":
            continue

        if not check_file_length(file_path):
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
