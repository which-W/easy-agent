"""
Custom file operation tools for AgentScope 1.0.18
Wraps built-in tools and adds extras like list_directory, delete_file, etc.
All functions must be async and return ToolResponse.
"""

import os
import shutil
import asyncio
from pathlib import Path
from typing import Optional

from agentscope.tool import ToolResponse
from agentscope.message import TextBlock


def _text(msg: str) -> ToolResponse:
    """Helper: wrap a plain text string into a ToolResponse."""
    return ToolResponse(content=[TextBlock(type="text", text=msg)])


# ---------------------------------------------------------------------------
# File read / write
# ---------------------------------------------------------------------------

async def create_file(file_path: str, content: str) -> ToolResponse:
    """Create a new file (or overwrite an existing one) with the given content.

    Args:
        file_path (`str`): Absolute or relative path of the file to create.
        content (`str`): The text content to write into the file.

    Returns:
        `ToolResponse`: Confirmation message or error description.
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return _text(f"✅ File created: {file_path}  ({len(content)} chars, {content.count(chr(10))+1} lines)")
    except Exception as e:
        return _text(f"❌ Failed to create file '{file_path}': {e}")


async def read_file(file_path: str) -> ToolResponse:
    """Read and return the full content of a text file.

    Args:
        file_path (`str`): Path of the file to read.

    Returns:
        `ToolResponse`: The file content with line numbers, or an error message.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return _text(f"❌ File not found: {file_path}")
        if not path.is_file():
            return _text(f"❌ Not a file: {file_path}")
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        numbered = "\n".join(f"{i+1:4d}: {line}" for i, line in enumerate(lines))
        return _text(
            f"📄 Content of '{file_path}' ({len(lines)} lines):\n\n{numbered}"
        )
    except Exception as e:
        return _text(f"❌ Failed to read '{file_path}': {e}")


async def edit_file(file_path: str, content: str, start_line: int = 1, end_line: Optional[int] = None) -> ToolResponse:
    """Replace a range of lines in an existing file with new content.
    If the file does not exist, it is created.

    Args:
        file_path (`str`): Path of the file to edit.
        content (`str`): New content to replace the specified line range.
        start_line (`int`, defaults to `1`): First line to replace (1-indexed, inclusive).
        end_line (`int | None`, defaults to `None`): Last line to replace (inclusive).
            If None, replaces from start_line to the end of the file.

    Returns:
        `ToolResponse`: Confirmation or error message.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            # create new
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return _text(f"✅ File created (did not exist): {file_path}")

        original_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        total = len(original_lines)
        s = max(1, start_line) - 1                      # 0-indexed
        e = total if end_line is None else min(end_line, total)  # 0-indexed exclusive

        new_chunk = content if content.endswith("\n") else content + "\n"
        merged = original_lines[:s] + [new_chunk] + original_lines[e:]
        path.write_text("".join(merged), encoding="utf-8")
        return _text(
            f"✅ Edited '{file_path}': replaced lines {start_line}–{e} "
            f"(original {total} lines → now {len(merged)} lines)"
        )
    except Exception as e:
        return _text(f"❌ Failed to edit '{file_path}': {e}")


async def append_to_file(file_path: str, content: str) -> ToolResponse:
    """Append text to the end of an existing file (creates it if absent).

    Args:
        file_path (`str`): Path of the file.
        content (`str`): Text to append.

    Returns:
        `ToolResponse`: Confirmation or error message.
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(content)
        return _text(f"✅ Appended {len(content)} chars to '{file_path}'")
    except Exception as e:
        return _text(f"❌ Failed to append to '{file_path}': {e}")


async def delete_file(file_path: str) -> ToolResponse:
    """Delete a file permanently.

    Args:
        file_path (`str`): Path of the file to delete.

    Returns:
        `ToolResponse`: Confirmation or error message.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return _text(f"⚠️ File not found (already deleted?): {file_path}")
        path.unlink()
        return _text(f"✅ Deleted: {file_path}")
    except Exception as e:
        return _text(f"❌ Failed to delete '{file_path}': {e}")


# ---------------------------------------------------------------------------
# Directory operations
# ---------------------------------------------------------------------------

async def list_directory(directory: str = ".", pattern: str = "*") -> ToolResponse:
    """List files and directories at the given path.

    Args:
        directory (`str`, defaults to `"."`): Directory path to list.
        pattern (`str`, defaults to `"*"`): Glob pattern to filter entries (e.g. "*.py").

    Returns:
        `ToolResponse`: A formatted directory listing or error message.
    """
    try:
        path = Path(directory).resolve()
        if not path.exists():
            return _text(f"❌ Directory not found: {directory}")
        if not path.is_dir():
            return _text(f"❌ Not a directory: {directory}")

        entries = sorted(path.glob(pattern))
        if not entries:
            return _text(f"📂 '{path}' is empty (pattern='{pattern}')")

        lines = [f"📂 Listing of '{path}' ({len(entries)} entries):"]
        for entry in entries:
            rel = entry.relative_to(path)
            if entry.is_dir():
                lines.append(f"  📁 {rel}/")
            else:
                size = entry.stat().st_size
                size_str = f"{size:,} B" if size < 1024 else f"{size/1024:.1f} KB"
                lines.append(f"  📄 {rel}  [{size_str}]")
        return _text("\n".join(lines))
    except Exception as e:
        return _text(f"❌ Failed to list directory '{directory}': {e}")


async def make_directory(directory: str) -> ToolResponse:
    """Create a directory (including all parent directories).

    Args:
        directory (`str`): Path of the directory to create.

    Returns:
        `ToolResponse`: Confirmation or error message.
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return _text(f"✅ Directory created: {directory}")
    except Exception as e:
        return _text(f"❌ Failed to create directory '{directory}': {e}")


async def move_file(source: str, destination: str) -> ToolResponse:
    """Move or rename a file or directory.

    Args:
        source (`str`): Source path.
        destination (`str`): Destination path.

    Returns:
        `ToolResponse`: Confirmation or error message.
    """
    try:
        src = Path(source)
        if not src.exists():
            return _text(f"❌ Source not found: {source}")
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), destination)
        return _text(f"✅ Moved '{source}' → '{destination}'")
    except Exception as e:
        return _text(f"❌ Failed to move '{source}' → '{destination}': {e}")


async def copy_file(source: str, destination: str) -> ToolResponse:
    """Copy a file to a new location.

    Args:
        source (`str`): Source file path.
        destination (`str`): Destination file path.

    Returns:
        `ToolResponse`: Confirmation or error message.
    """
    try:
        src = Path(source)
        if not src.exists():
            return _text(f"❌ Source not found: {source}")
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), destination)
        return _text(f"✅ Copied '{source}' → '{destination}'")
    except Exception as e:
        return _text(f"❌ Failed to copy '{source}' → '{destination}': {e}")


# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------

async def run_python_file(file_path: str, timeout: float = 30.0) -> ToolResponse:
    """Execute a Python file and return its stdout / stderr output.

    Args:
        file_path (`str`): Path to the .py file to run.
        timeout (`float`, defaults to `30.0`): Maximum allowed runtime in seconds.

    Returns:
        `ToolResponse`: Combined stdout and stderr from the script, or error info.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return _text(f"❌ Python file not found: {file_path}")

        proc = await asyncio.create_subprocess_exec(
            "python3", str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return _text(f"❌ Execution timed out after {timeout}s: {file_path}")

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        rc = proc.returncode

        parts = [f"▶ Ran '{file_path}' (exit code {rc})"]
        if out:
            parts.append(f"\n📤 stdout:\n{out}")
        if err:
            parts.append(f"\n⚠️ stderr:\n{err}")
        if not out and not err:
            parts.append("\n(no output)")
        return _text("\n".join(parts))
    except Exception as e:
        return _text(f"❌ Failed to run '{file_path}': {e}")


async def run_shell_command(command: str, timeout: float = 30.0) -> ToolResponse:
    """Run an arbitrary shell command and return its output.

    Args:
        command (`str`): The shell command to execute (passed to /bin/sh).
        timeout (`float`, defaults to `30.0`): Maximum allowed runtime in seconds.

    Returns:
        `ToolResponse`: stdout and stderr of the command, or an error message.
    """
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return _text(f"❌ Command timed out after {timeout}s: {command}")

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        rc = proc.returncode

        parts = [f"$ {command}  (exit code {rc})"]
        if out:
            parts.append(f"\n{out}")
        if err:
            parts.append(f"\n⚠️ stderr:\n{err}")
        if not out and not err:
            parts.append("\n(no output)")
        return _text("\n".join(parts))
    except Exception as e:
        return _text(f"❌ Shell command failed: {e}")
