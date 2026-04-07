"""File operations skill - safe file system operations"""

import os
from pathlib import Path
from typing import List, Optional


# Allowed base directories (relative to project root)
ALLOWED_DIRS = ["./uploads", "./skills", "./data"]


def read_file(file_path: str, max_lines: int = 100) -> str:
    """Read contents of a file safely.

    Args:
        file_path: Path to the file to read
        max_lines: Maximum number of lines to read (default 100)

    Returns:
        File contents or error message
    """
    try:
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            return f"Error: File '{file_path}' does not exist"

        # Check if it's a file
        if not path.is_file():
            return f"Error: '{file_path}' is not a file"

        # Check if in allowed directories
        if not _is_allowed_path(path):
            return f"Error: Access to '{file_path}' is not allowed"

        # Read file
        with open(path, 'r', encoding='utf-8') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... (truncated, showing first {max_lines} lines)")
                    break
                lines.append(line)

        return ''.join(lines)

    except PermissionError:
        return f"Error: Permission denied reading '{file_path}'"
    except UnicodeDecodeError:
        return f"Error: '{file_path}' is not a text file"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def write_file(file_path: str, content: str) -> str:
    """Write content to a file safely.

    Args:
        file_path: Path to the file to write
        content: Content to write

    Returns:
        Success or error message
    """
    try:
        path = Path(file_path)

        # Check if in allowed directories
        if not _is_allowed_path(path):
            return f"Error: Writing to '{file_path}' is not allowed"

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Successfully wrote {len(content)} bytes to '{file_path}'"

    except PermissionError:
        return f"Error: Permission denied writing to '{file_path}'"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def list_directory(dir_path: str, max_items: int = 50) -> str:
    """List contents of a directory safely.

    Args:
        dir_path: Path to the directory to list
        max_items: Maximum number of items to list (default 50)

    Returns:
        Directory listing or error message
    """
    try:
        path = Path(dir_path)

        # Check if directory exists
        if not path.exists():
            return f"Error: Directory '{dir_path}' does not exist"

        # Check if it's a directory
        if not path.is_dir():
            return f"Error: '{dir_path}' is not a directory"

        # Check if in allowed directories
        if not _is_allowed_path(path):
            return f"Error: Access to '{dir_path}' is not allowed"

        # List directory
        items = []
        for i, item in enumerate(path.iterdir()):
            if i >= max_items:
                items.append(f"... (truncated, showing first {max_items} items)")
                break
            prefix = "[DIR] " if item.is_dir() else "[FILE] "
            items.append(f"{prefix}{item.name}")

        return '\n'.join(items) if items else "Directory is empty"

    except PermissionError:
        return f"Error: Permission denied accessing '{dir_path}'"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def _is_allowed_path(path: Path) -> bool:
    """Check if path is in allowed directories"""
    abs_path = path.resolve()
    for allowed_dir in ALLOWED_DIRS:
        abs_allowed = Path(allowed_dir).resolve()
        if str(abs_path).startswith(str(abs_allowed)):
            return True
    return False
