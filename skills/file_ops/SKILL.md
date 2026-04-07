---
name: file_ops
description: Perform file system operations including reading, writing, listing, and searching files. Use when user needs to work with files or directories.
version: 1.0.0
---

# File Operations

## Usage
When the user asks to:
- Read file contents
- Write to files
- List directory contents
- Search for files
- Get file information

## Examples
- User: "Read the contents of config.yaml"
- User: "List all Python files in the current directory"
- User: "Create a new file called notes.txt"

## Constraints
- Only access files in allowed directories
- No deletion operations
- Maximum file read size: 1MB
- No access to system files or hidden files
