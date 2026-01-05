# WorkspaceBrain

A CLI tool for managing multiple projects from a single place. Creates a central "brain" across your projects and automatically adds rule files for AI assistants (Claude, Cursor, etc.).

## What Does It Do?

If you have multiple projects in a workspace (frontend, backend, mobile, etc.), WorkspaceBrain:

1. **Creates a central `brain/` folder** - all decisions, rules, and contracts in one place
2. **Auto-detects projects** - recognizes Python, Node.js, Rust, Go, Java projects
3. **Adds AI rule files to each project** - for Claude, Cursor, and other AI assistants
4. **Links projects together** - each project connects to the central brain via symlink

## Installation

```bash
# Install with pipx (recommended)
pipx install git+https://github.com/USER/workspacebrain.git

# Or with pip
pip install git+https://github.com/USER/workspacebrain.git
```

## Quick Start

```bash
# Navigate to your projects folder
cd ~/my-projects

# Setup everything with one command
wbrain setup
```

This command:

1. Creates the `brain/` folder
2. Scans and detects all projects
3. Adds `.brain` symlink and `.wbrain/` folder to each project

## Commands

| Command | Description |
| ------- | ----------- |
| `wbrain setup` | One-command init + scan + link (fastest start) |
| `wbrain init` | Creates the brain folder |
| `wbrain scan` | Detects projects |
| `wbrain link` | Links projects to brain |
| `wbrain doctor` | Health check |

All commands work in the current directory. You can also specify a path:

```bash
wbrain setup ~/another/folder
```

## Generated Structure

```text
workspace/
├── brain/                      # Central brain (single copy)
│   ├── README.md               # Brain documentation
│   ├── MANIFEST.yaml           # Detected projects
│   ├── DECISIONS.md            # Architectural decisions
│   ├── CONTRACTS/              # API contracts
│   ├── HANDOFFS/               # Work transitions
│   └── RULES/                  # Coding standards
│
├── frontend/
│   ├── .brain -> ../brain      # Symlink (to central brain)
│   ├── .wbrain/                # AI rule files
│   │   ├── CLAUDE.md
│   │   ├── CURSOR_RULES.md
│   │   └── AI.md
│   └── ... (project files)
│
└── backend/
    ├── .brain -> ../brain
    ├── .wbrain/
    │   ├── CLAUDE.md
    │   ├── CURSOR_RULES.md
    │   └── AI.md
    └── ... (project files)
```

## Supported Project Types

| Type | Detection Signals |
| ---- | ----------------- |
| **Node.js Frontend** | `package.json` + (`vite.config.*`, `next.config.*`, `src/App.tsx`) |
| **Python Backend** | `pyproject.toml`, `requirements.txt`, `setup.py` |
| **Rust** | `Cargo.toml` |
| **Go** | `go.mod` |
| **Java** | `pom.xml`, `build.gradle` |
| **Mobile** | `app.json` (Expo), React Native |

## AI Rule Files

Files created in the `.wbrain/` folder of each project:

- **CLAUDE.md** - Project context and rules for Claude AI
- **CURSOR_RULES.md** - Rules for Cursor IDE
- **AI.md** - General guide for AI assistants

These files are auto-generated and can be customized from the central `brain/RULES/` folder.

## Example Usage

```bash
# 1. Navigate to workspace
cd ~/Documents/GitHub

# 2. Setup brain
wbrain setup

# 3. Health check
wbrain doctor

# 4. If new projects are added, scan and link again
wbrain scan
wbrain link
```

## Health Check

```bash
wbrain doctor
```

Output:

```text
╭─────────────────────────────╮
│ Brain Health Check          │
╰─────────────────────────────╯

Brain Directory
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check           ┃ Status ┃ Details              ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Brain Directory │   ✓    │ Found                │
│ MANIFEST.yaml   │   ✓    │ Valid (3 projects)   │
│ README.md       │   ✓    │ Present              │
└─────────────────┴────────┴──────────────────────┘

frontend (node-fe)
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check                   ┃ Status ┃ Details                ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ .brain                  │   ✓    │ OK: symlink (../brain) │
│ .wbrain/CLAUDE.md       │   ✓    │ In sync                │
│ .wbrain/CURSOR_RULES.md │   ✓    │ In sync                │
│ .wbrain/AI.md           │   ✓    │ In sync                │
└─────────────────────────┴────────┴────────────────────────┘

╭──────────────────────────────────────╮
│ All checks passed! Brain is healthy. │
╰──────────────────────────────────────╯
```

## Development

```bash
# Clone the repo
git clone https://github.com/USER/workspacebrain.git
cd workspacebrain

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=workspacebrain
```

## License

MIT
