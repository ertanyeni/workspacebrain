# WorkspaceBrain

A CLI tool for managing multiple projects from a single place. Creates a central "brain" across your projects and automatically adds rule files for AI assistants (Claude, Cursor, Windsurf, etc.).

## What Does It Do?

If you have multiple projects in a workspace (frontend, backend, mobile, etc.), WorkspaceBrain:

1. **Creates a central `brain/` folder** - all decisions, rules, contracts, and logs in one place
2. **Auto-detects projects** - recognizes Python, Node.js, Rust, Go, Java projects
3. **Adds AI rule files to each project** - for Claude, Cursor, Windsurf, and other AI assistants
4. **Links projects together** - each project connects to the central brain via symlink
5. **Tracks work history** - daily logs for progress tracking

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
3. Adds `.brain` symlink and AI rule files to each project

## Commands

| Command | Description |
| ------- | ----------- |
| `wbrain setup` | One-command init + scan + link (fastest start) |
| `wbrain init` | Creates the brain folder |
| `wbrain scan` | Detects projects |
| `wbrain link` | Links projects to brain |
| `wbrain doctor` | Health check |
| `wbrain log "msg"` | Add work log entry |
| `wbrain logs` | Show recent work logs |
| `wbrain uninstall` | Remove all generated files |

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
│   ├── RULES/                  # Coding standards
│   └── LOGS/                   # Daily work logs
│       └── 2025-01-05.md
│
├── frontend/
│   ├── .brain -> ../brain      # Symlink to central brain
│   ├── CLAUDE.md               # Claude Code instructions
│   ├── .cursorrules            # Cursor IDE rules
│   ├── .windsurfrules          # Windsurf rules
│   ├── AI.md                   # Generic AI instructions
│   └── ... (project files)
│
└── backend/
    ├── .brain -> ../brain
    ├── CLAUDE.md
    ├── .cursorrules
    ├── .windsurfrules
    ├── AI.md
    └── ... (project files)
```

## AI Rule Files

Files created in the **project root** for each AI tool to auto-detect:

| File | AI Tool | Auto-Read |
|------|---------|-----------|
| `CLAUDE.md` | Claude Code | Yes |
| `.cursorrules` | Cursor IDE | Yes |
| `.windsurfrules` | Windsurf/Codeium | Yes |
| `AI.md` | Generic | Manual |

These files are auto-generated and can be customized from the central `brain/RULES/` folder.

## Work Logging

Track your work progress with simple log commands:

```bash
# Log from inside a project (auto-detects project name)
cd frontend
wbrain log "Added user authentication"

# Log with explicit project name
wbrain log "Fixed API bug" -p backend

# View recent logs
wbrain logs

# View last 30 days
wbrain logs -d 30
```

Logs are stored in `brain/LOGS/YYYY-MM-DD.md` files.

## Supported Project Types

| Type | Detection Signals |
| ---- | ----------------- |
| **Node.js Frontend** | `package.json` + (`vite.config.*`, `next.config.*`, `src/App.tsx`) |
| **Python Backend** | `pyproject.toml`, `requirements.txt`, `setup.py` |
| **Rust** | `Cargo.toml` |
| **Go** | `go.mod` |
| **Java** | `pom.xml`, `build.gradle` |
| **Mobile** | `app.json` (Expo), React Native |

## Example Usage

```bash
# 1. Navigate to workspace
cd ~/Documents/GitHub

# 2. Setup brain
wbrain setup

# 3. Health check
wbrain doctor

# 4. Log your work
wbrain log "Initial setup complete"

# 5. If new projects are added, scan and link again
wbrain scan
wbrain link
```

## Uninstall

To completely remove WorkspaceBrain:

```bash
# Remove all generated files from workspace
wbrain uninstall

# Then remove the CLI tool
pipx uninstall workspacebrain
```

Options:
- `--keep-brain` - Keep the brain/ directory, only remove project files
- `--force` - Skip confirmation prompt

## Health Check

```bash
wbrain doctor
```

Output:

```text
╭───────────────────────────────╮
│ Brain Health Check            │
│ /Users/you/Documents/GitHub   │
╰───────────────────────────────╯

                Brain Directory
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Check           ┃ Status ┃ Details           ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ Brain Directory │   ✓    │ Found             │
│ MANIFEST.yaml   │   ✓    │ Valid (3 projects)│
│ README.md       │   ✓    │ Present           │
└─────────────────┴────────┴───────────────────┘

              frontend (node-fe)
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check          ┃ Status ┃ Details                ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ .brain         │   ✓    │ OK: symlink (../brain) │
│ CLAUDE.md      │   ✓    │ In sync (claude)       │
│ .cursorrules   │   ✓    │ In sync (cursor)       │
│ .windsurfrules │   ✓    │ In sync (windsurf)     │
│ AI.md          │   ✓    │ In sync (generic)      │
└────────────────┴────────┴────────────────────────┘

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
