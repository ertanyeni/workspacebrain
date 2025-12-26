# WorkspaceBrain

A CLI tool for managing workspace brain - centralized knowledge and rules for multi-project workspaces.

## Installation

```bash
# From source
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

## Usage

### Initialize a Brain

```bash
workspacebrain init /path/to/workspace

# Or use the short alias
wbrain init /path/to/workspace

# Force re-initialization
wbrain init --force /path/to/workspace
```

### Scan for Projects

```bash
wbrain scan /path/to/workspace
```

### Link Projects to Brain

```bash
wbrain link /path/to/workspace
```

### Check Brain Health

```bash
wbrain doctor /path/to/workspace
```

## Brain Structure

After initialization, your workspace will have:

```
workspace/
├── brain/
│   ├── README.md          # Brain documentation
│   ├── MANIFEST.yaml      # Workspace metadata
│   ├── DECISIONS.md       # Architectural decisions
│   ├── CONTRACTS/         # API contracts
│   ├── HANDOFFS/          # Work transitions
│   └── RULES/             # Coding standards
│       └── INDEX.md
├── project-a/
│   └── .brain             # Pointer to brain (after link)
└── project-b/
    └── .brain
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=workspacebrain

# Type checking
mypy src

# Linting
ruff check src tests
```

## License

MIT
