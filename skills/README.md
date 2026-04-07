# AgentScope Skills

This directory contains skills for the AgentScope agent system.

## Skill Structure

Each skill is a directory containing:
- `SKILL.md` - Skill description and metadata (YAML frontmatter)
- `assets/` - Directory containing Python scripts with skill functions

## SKILL.md Format

```markdown
---
name: skill_name
description: Brief description of what this skill does
version: 1.0.0
---

# Skill Name

## Usage
When to use this skill and how the agent should invoke it.

## Examples
- User request examples showing when this skill should be used

## Constraints
Any limitations or safety constraints
```

## Adding New Skills

1. Create a new directory under `skills/`
2. Add `SKILL.md` with YAML frontmatter
3. Add Python scripts in `assets/` directory
4. Skills are automatically loaded on server start
5. Use `POST /api/skills/reload` to reload skills at runtime

## Built-in Skills

- **code_executor** - Execute Python code snippets safely
- **file_ops** - File system operations (read, write, search)
- **web_search** - Web search functionality
