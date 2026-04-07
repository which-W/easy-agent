---
name: code_executor
description: Execute Python code snippets safely in a sandboxed environment. Use when user asks to run code, calculate expressions, or test Python logic.
version: 1.0.0
---

# Code Executor

## Usage
When the user asks to:
- Execute Python code
- Calculate mathematical expressions
- Test Python logic
- Run data processing scripts

## Examples
- User: "Calculate 2^10"
- User: "Write a function to reverse a string"
- User: "What is the result of [1,2,3] + [4,5,6] in Python?"

## Constraints
- Only execute safe operations
- No file system access outside allowed directories
- No network access
- No import of dangerous modules (os, subprocess, shutil, etc.)
- Maximum execution time: 10 seconds
- Maximum output length: 10000 characters
