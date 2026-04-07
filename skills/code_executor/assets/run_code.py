"""Code executor skill - safely execute Python code snippets"""

import ast
import sys
from io import StringIO
from contextlib import redirect_stdout
from typing import Any


# Safe modules that can be imported
SAFE_MODULES = {
    'math', 'random', 'string', 'json', 're', 'datetime',
    'collections', 'itertools', 'functools', 'typing',
    'statistics', 'decimal', 'fractions', 'operator',
}

# Dangerous modules that are forbidden
DANGEROUS_MODULES = {
    'os', 'sys', 'subprocess', 'shutil', 'pathlib',
    'socket', 'http', 'requests', 'urllib',
    'pickle', 'marshal', 'ctypes',
}


def execute_code(code: str) -> str:
    """Execute Python code safely in a sandboxed environment.

    Args:
        code: Python code to execute

    Returns:
        Execution result or error message
    """
    # Validate code safety
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax Error: {e}"

    # Check for dangerous imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] in DANGEROUS_MODULES:
                    return f"Error: Import of '{alias.name}' is not allowed for safety reasons"
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] in DANGEROUS_MODULES:
                return f"Error: Import of '{node.module}' is not allowed for safety reasons"

    # Execute code with restricted globals
    safe_globals = {
        '__builtins__': {
            name: getattr(__builtins__, name)
            for name in dir(__builtins__)
            if not name.startswith('_') and name not in ['eval', 'exec', 'compile', '__import__']
        }
    }

    # Add safe modules
    for module_name in SAFE_MODULES:
        try:
            safe_globals[module_name] = __import__(module_name)
        except ImportError:
            pass

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        result = exec(code, safe_globals, {})
        output = sys.stdout.getvalue()
        return output if output else "Code executed successfully (no output)"
    except Exception as e:
        return f"Execution Error: {type(e).__name__}: {e}"
    finally:
        sys.stdout = old_stdout
