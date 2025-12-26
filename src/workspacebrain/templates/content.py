"""Template content for brain initialization files."""


def get_readme_template(workspace_name: str) -> str:
    """Generate README.md content for the brain directory."""
    return f"""# {workspace_name} Brain

This is the central knowledge repository for the **{workspace_name}** workspace.

## Purpose

The brain directory serves as a single source of truth for:

- **Decisions**: Architectural and design decisions made across projects
- **Contracts**: API contracts, interfaces, and agreements between projects
- **Handoffs**: Documentation for transitioning work between team members or AI agents
- **Rules**: Coding standards, linting rules, and conventions for the workspace

## Structure

```
brain/
├── README.md          # This file
├── MANIFEST.yaml      # Workspace metadata and detected projects
├── DECISIONS.md       # Decision log (ADRs)
├── CONTRACTS/         # API contracts and interfaces
├── HANDOFFS/          # Work transition documentation
└── RULES/             # Coding standards and conventions
```

## Usage

### For Developers

1. Before starting work, review relevant decisions and contracts
2. Document new decisions in DECISIONS.md
3. Update contracts when APIs change
4. Create handoff documents when transitioning work

### For AI Agents

1. Read MANIFEST.yaml to understand workspace structure
2. Follow rules in RULES/ directory
3. Reference contracts for API integration
4. Use handoffs for context when continuing work

## Maintained By

WorkspaceBrain CLI - `workspacebrain doctor` to check health
"""


def get_decisions_template() -> str:
    """Generate DECISIONS.md content."""
    return """# Architectural Decision Records

This document tracks important decisions made for this workspace.

## Template

When adding a new decision, use this format:

```markdown
## [DECISION-XXX] Title

**Date**: YYYY-MM-DD
**Status**: Proposed | Accepted | Deprecated | Superseded
**Deciders**: Who made this decision

### Context

What is the issue that we're seeing that is motivating this decision?

### Decision

What is the change that we're proposing and/or doing?

### Consequences

What becomes easier or more difficult because of this change?
```

---

## Decisions

<!-- Add new decisions below this line -->

## [DECISION-001] Adopt WorkspaceBrain for Knowledge Management

**Date**: Auto-generated
**Status**: Accepted
**Deciders**: Workspace maintainers

### Context

Managing knowledge, decisions, and conventions across multiple projects
in a workspace is challenging without a centralized system.

### Decision

Use WorkspaceBrain to maintain a central `brain/` directory that
contains shared knowledge, decisions, contracts, and rules.

### Consequences

- Easier: Finding workspace-wide conventions and decisions
- Easier: Onboarding new team members or AI agents
- Harder: Requires discipline to keep brain updated
"""


def get_rules_index_template() -> str:
    """Generate RULES/INDEX.md content."""
    return """# Workspace Rules Index

This directory contains coding standards and conventions for the workspace.

## How to Use

1. Each rule file should focus on a specific topic
2. Name files descriptively: `python-style.md`, `api-conventions.md`
3. Reference rules from project-level configurations

## Rule Categories

### Code Style

- Language-specific formatting rules
- Naming conventions
- File organization

### Architecture

- Project structure patterns
- Module boundaries
- Dependency rules

### Process

- Git workflow
- Code review guidelines
- Testing requirements

## Rule Files

<!-- Add rule files below as you create them -->

- `INDEX.md` - This file

## Template for New Rules

```markdown
# Rule: [Topic]

## Scope

Which projects/languages does this apply to?

## Rules

1. Rule one
2. Rule two

## Examples

Good:
```code
...
```

Bad:
```code
...
```

## Exceptions

When can this rule be bypassed?
```
"""


def get_contract_template(name: str) -> str:
    """Generate a contract template."""
    return f"""# Contract: {name}

## Version

1.0.0

## Parties

- Provider: [Service/Project name]
- Consumer: [Service/Project name]

## Interface

### Endpoints / Methods

```
[Define API endpoints or method signatures]
```

### Data Models

```
[Define shared data structures]
```

## Guarantees

- [ ] Backward compatibility policy
- [ ] Versioning strategy
- [ ] Deprecation notice period

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0   | TBD  | Initial contract |
"""


def get_handoff_template(title: str) -> str:
    """Generate a handoff document template."""
    return f"""# Handoff: {title}

## Date

[YYYY-MM-DD]

## From

[Name/Agent]

## To

[Name/Agent]

## Context

What was being worked on? What's the current state?

## Completed

- [ ] Task 1
- [ ] Task 2

## In Progress

- [ ] Current task with notes on where it stands

## Remaining

- [ ] Pending task 1
- [ ] Pending task 2

## Key Files

- `path/to/file.py` - Description
- `path/to/other.py` - Description

## Notes

Any additional context, gotchas, or suggestions for the next person.

## Questions

Open questions that need answers.
"""
