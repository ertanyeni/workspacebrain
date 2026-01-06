# WorkspaceBrain

A CLI tool that creates a shared "brain" across your projects, enabling **automatic context sharing between AI assistants**. When an AI works on your backend, the AI on your frontend automatically knows about it.

## The Problem

You have multiple projects (frontend, backend, mobile). You're using AI assistants (Claude, Cursor, Windsurf). But:

- AI in frontend doesn't know what AI did in backend
- You have to manually explain context every time you switch projects
- No central place for decisions, contracts, and rules

## The Solution

WorkspaceBrain creates a central `brain/` folder that all your projects share. AI assistants automatically:

1. **Read recent activity** from other projects before starting work
2. **Log their sessions** with reasoning and decisions
3. **Share context** without you doing anything

```
┌─────────────┐     logs session     ┌─────────────────────┐
│   Backend   │ ──────────────────▶  │  brain/CONTEXT/     │
│   (Claude)  │                      │  RECENT_ACTIVITY.md │
└─────────────┘                      └──────────┬──────────┘
                                                │
                                     reads context
                                                │
┌─────────────┐                      ┌──────────▼──────────┐
│  Frontend   │ ◀──────────────────  │  "Backend added     │
│  (Cursor)   │    knows about it    │   auth endpoint"    │
└─────────────┘                      └─────────────────────┘
```

## Installation

```bash
# With pipx (recommended)
pipx install git+https://github.com/USER/workspacebrain.git

# Or with pip
pip install git+https://github.com/USER/workspacebrain.git
```

## Quick Start

```bash
cd ~/my-projects    # Your workspace with multiple projects
wbrain setup        # Creates brain, detects projects, links everything
```

That's it. Your AI assistants now have:
- `.brain` symlink in each project pointing to central brain
- `CLAUDE.md`, `.cursorrules`, `.windsurfrules`, `AI.md` with instructions
- Automatic cross-project context sharing

## Commands

| Command | Description |
| ------- | ----------- |
| `wbrain setup` | One-command setup (init + scan + link) |
| `wbrain doctor` | Health check - verify everything works |
| `wbrain status` | Show recent activity across all projects |
| `wbrain ai-log` | Log AI session (called by AI assistants) |
| `wbrain context` | Manually refresh context files |
| `wbrain log "msg"` | Simple human log entry |
| `wbrain logs` | View recent logs |
| `wbrain scan` | Detect new projects |
| `wbrain link` | Re-link projects (after adding new ones) |
| `wbrain uninstall` | Remove all generated files |

## Cross-Project AI Context

### How It Works

1. **AI starts working** on backend project
2. **AI reads** `.brain/CONTEXT/RECENT_ACTIVITY.md` (sees what happened in other projects)
3. **AI completes work** and logs it:
   ```bash
   wbrain ai-log -p backend -t claude -s "Added JWT auth endpoint" \
     -r "Chose JWT for mobile app compatibility" \
     --related "frontend:needs to implement token storage"
   ```
4. **Context auto-updates** - `RECENT_ACTIVITY.md` now includes this info
5. **AI in frontend** reads context and knows about the new endpoint

### What Gets Logged

```markdown
## Session: 14:30 - backend (claude)

### Summary
Added JWT authentication endpoint

### What Was Done
- Created /api/auth/login endpoint
- Added token validation middleware

### AI Reasoning
Chose JWT over session cookies because:
- Frontend is a SPA (different origin)
- Mobile app planned (needs stateless auth)

### Related Projects
- **frontend**: Will need to implement token storage and refresh

### Open Questions
- Should we use refresh tokens?
- What token expiry time?

### Key Files
- `api/auth/routes.py`
- `api/auth/jwt_handler.py`
```

### View Cross-Project Status

```bash
wbrain status
```

Output:
```
╭──────────────────╮
│ Workspace Status │
│ Last 3 days      │
╰──────────────────╯

Recent Activity

backend
  2026-01-06 14:30 (claude) Added JWT authentication endpoint
  2026-01-06 10:00 (claude) Set up project structure

frontend
  2026-01-06 16:00 (cursor) Started login form implementation

Project Relationships
  backend ↔ frontend

Open Questions
  ? [backend] Should we use refresh tokens?
  ? [backend] Token expiry time?
```

## Generated Structure

```
workspace/
├── brain/                          # Central brain (single copy)
│   ├── MANIFEST.yaml               # Detected projects
│   ├── DECISIONS.md                # Architectural decisions
│   ├── CONTRACTS/                  # API contracts between projects
│   ├── HANDOFFS/                   # Work transition documents
│   ├── RULES/                      # Coding standards
│   ├── LOGS/                       # Daily work logs
│   │   └── 2026-01-06.md           # Structured AI session logs
│   └── CONTEXT/                    # Auto-generated (AI reads these)
│       ├── RECENT_ACTIVITY.md      # Last 3 days summary
│       └── OPEN_QUESTIONS.md       # Aggregated questions
│
├── backend/
│   ├── .brain -> ../brain          # Symlink to central brain
│   ├── CLAUDE.md                   # Claude instructions (auto-generated)
│   ├── .cursorrules                # Cursor rules (auto-generated)
│   ├── .windsurfrules              # Windsurf rules (auto-generated)
│   └── AI.md                       # Generic AI instructions
│
└── frontend/
    ├── .brain -> ../brain
    ├── CLAUDE.md
    ├── .cursorrules
    ├── .windsurfrules
    └── AI.md
```

## AI Rule Files

Each AI tool has its own auto-detected file:

| File | AI Tool | Auto-Read |
| ---- | ------- | --------- |
| `CLAUDE.md` | Claude Code | Yes |
| `.cursorrules` | Cursor IDE | Yes |
| `.windsurfrules` | Windsurf/Codeium | Yes |
| `AI.md` | Generic | Manual |

These files include:
- Mandatory session logging instructions
- Cross-project context reading instructions
- Project-specific coding standards
- Links to brain resources

To customize, create templates in `brain/RULES/`:
- `brain/RULES/CLAUDE.md` - Custom Claude template
- `brain/RULES/CLAUDE.python-be.md` - Python backend specific

## Supported Project Types

| Type | Detection Signals |
| ---- | ----------------- |
| **Node.js Frontend** | `package.json` + (`vite.config.*`, `next.config.*`, `src/App.tsx`) |
| **Python Backend** | `pyproject.toml`, `requirements.txt`, `setup.py` |
| **Rust** | `Cargo.toml` |
| **Go** | `go.mod` |
| **Java** | `pom.xml`, `build.gradle` |
| **Mobile** | `app.json` (Expo), React Native |

## Example Workflow

```bash
# Initial setup
cd ~/Documents/GitHub
wbrain setup

# Check health
wbrain doctor

# Work on backend (AI logs automatically via ai-log)
cd backend
# ... AI does work and logs it ...

# Switch to frontend - AI automatically knows about backend changes
cd ../frontend
# AI reads .brain/CONTEXT/RECENT_ACTIVITY.md

# Check what's happening across projects
wbrain status

# Add new project and re-link
cd ..
mkdir new-service && cd new-service
echo '{"name": "new-service"}' > package.json
cd ..
wbrain scan
wbrain link
```

## Health Check

```bash
wbrain doctor
```

```
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

          backend (python-be)
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check          ┃ Status ┃ Details                ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ .brain         │   ✓    │ OK: symlink (../brain) │
│ CLAUDE.md      │   ✓    │ In sync                │
│ .cursorrules   │   ✓    │ In sync                │
│ .windsurfrules │   ✓    │ In sync                │
│ AI.md          │   ✓    │ In sync                │
└────────────────┴────────┴────────────────────────┘

╭──────────────────────────────────────╮
│ All checks passed! Brain is healthy. │
╰──────────────────────────────────────╯
```

## Uninstall

```bash
# Remove all generated files from workspace
wbrain uninstall

# Options:
#   --keep-brain  Keep brain/ directory, only remove project files
#   --force       Skip confirmation

# Remove the CLI tool
pipx uninstall workspacebrain
```

## Development

```bash
git clone https://github.com/USER/workspacebrain.git
cd workspacebrain

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=workspacebrain
```

## License

MIT
