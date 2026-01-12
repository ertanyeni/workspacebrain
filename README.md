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
wbrain setup        # One command: creates brain, detects projects, links everything
```

That's it! Your AI assistants now have:
- `.brain` symlink in each project pointing to central brain
- `CLAUDE.md`, `.cursorrules`, `.windsurfrules`, `AI.md` with instructions
- Automatic cross-project context sharing

**Check security:**
```bash
wbrain security     # Scans and analyzes vulnerabilities automatically
```

**View status:**
```bash
wbrain status       # See recent activity across all projects
wbrain doctor       # Health check
```

## Commands

### Main Commands

| Command | Description |
| ------- | ----------- |
| `wbrain setup` | One-command setup (initializes brain, scans projects, links everything) |
| `wbrain status` | Show recent activity across all projects |
| `wbrain ai-log` | Log AI session (called by AI assistants) |
| `wbrain security` | Security scan + risk analysis (does both automatically) |
| `wbrain doctor` | Health check - verify everything works |
| `wbrain uninstall` | Remove all generated files |

### Utility Commands

| Command | Description |
| ------- | ----------- |
| `wbrain context` | Manually refresh context files |
| `wbrain log "msg"` | Simple human log entry |
| `wbrain logs` | View recent logs |
| `wbrain relationships` | Show and manage project relationships |

### Security Commands

| Command | Description |
| ------- | ----------- |
| `wbrain security` | **Default**: Scan + analyze vulnerabilities (does both automatically) |
| `wbrain security --scan-only` | Only scan for vulnerabilities (skip analysis) |
| `wbrain security --analyze-only` | Only analyze existing scan results (skip scan) |
| `wbrain security status` | Show security status summary by project |
| `wbrain security list` | List all security issues with detailed information |
| `wbrain security list --compact` | Compact table view of all issues |
| `wbrain security list --priority CRITICAL` | Filter by priority level |
| `wbrain security list --action FIX_NOW` | Filter by action type |
| `wbrain security fix-now` | List critical issues requiring immediate fix |

**Security Workflow:**
```bash
# Simple: one command does everything
wbrain security

# Advanced: step-by-step control
wbrain security --scan-only      # Step 1: Just scan
wbrain security --analyze-only    # Step 2: Just analyze
wbrain security status           # Check results
wbrain security list              # See all details
```

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

### Security Context

WorkspaceBrain also provides security context to AI assistants:

```bash
# Run security analysis
wbrain security

# AI assistants automatically read:
# - .brain/CONTEXT/SECURITY.md (global security summary)
# - .brain/CONTEXT/projects/{project}.md (project-specific security alerts)
```

AI assistants can now:
- See which security issues need immediate attention
- Understand risk priorities (FIX_NOW, FIX_SOON, MONITOR)
- Get recommended fixes for vulnerabilities
- Know about exploit availability and CVSS scores

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
│   ├── SECURITY/                   # Security analysis data
│   │   ├── ALERTS.yaml             # Security alerts
│   │   └── RISK_ASSESSMENT.yaml    # Risk assessments
│   └── CONTEXT/                    # Auto-generated (AI reads these)
│       ├── RECENT_ACTIVITY.md      # Last 3 days summary
│       ├── SECURITY.md              # Security context for AI
│       ├── OPEN_QUESTIONS.md        # Aggregated questions
│       └── projects/               # Project-specific context
│           ├── backend.md          # Filtered context for backend
│           └── frontend.md         # Filtered context for frontend
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
# Initial setup (one command does everything)
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

# Check security vulnerabilities (scan + analyze automatically)
wbrain security

# View detailed security issues
wbrain security list

# See critical issues that need immediate attention
wbrain security fix-now

# Add new project - just run setup again
cd ..
mkdir new-service && cd new-service
echo '{"name": "new-service"}' > package.json
cd ..
wbrain setup  # Re-scans and links new project
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

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
wbrain --version
wbrain --help

# Run tests
pytest

# With coverage
pytest --cov=workspacebrain
```

### Requirements

- Python 3.9 or higher
- pip (latest version recommended)

## License

MIT
