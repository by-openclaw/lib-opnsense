# Contributing to lib-opnsense

## Development setup

**Choose one path. Do not mix them.**

| Path | When to use |
|---|---|
| [A — Native Python + venv](#path-a--native-python--venv) | Any OS — Python installed locally, prefer terminal |
| [B — VS Code Dev Container](#path-b--vs-code-dev-container) | Any OS — Docker Desktop installed, prefer VS Code IDE |

---

## Path A — Native Python + venv

No Docker required. Python 3.10+ must be installed.

```bash
git clone https://github.com/by-openclaw/lib-opnsense.git
cd lib-opnsense

# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate

# Install with dev extras
pip install -e ".[dev]"

# Copy and fill in credentials
cp .env.example .env
# Edit .env with your OPNsense API key/secret
```

### Run tests

```bash
# Unit tests (no OPNsense device required)
pytest tests/unit/ -v

# Integration tests (live OPNsense required)
pytest tests/integration/ -m integration -v
```

---

## Path B — VS Code Dev Container

Docker Desktop must be installed and running.

### Prerequisites

| Tool | Download |
|---|---|
| Docker Desktop | <https://www.docker.com/products/docker-desktop> |
| VS Code | <https://code.visualstudio.com> |
| Dev Containers extension | VS Code -> Extensions -> `ms-vscode-remote.remote-containers` |

### Setup

1. Clone the repo: `git clone https://github.com/by-openclaw/lib-opnsense.git`
2. Open in VS Code: `File -> Open Folder -> lib-opnsense`
3. Reopen in container: `Ctrl+Shift+P` -> `Dev Containers: Rebuild and Reopen in Container`

The container will:
1. Pull `mcr.microsoft.com/devcontainers/python:3.13`
2. Create a venv at `/home/vscode/.venv`
3. Install the project with `pip install -e '.[container]'`

### Run tests in the container terminal

```bash
pytest tests/unit/ -v
```

---

## Linting and type checking

```bash
# Lint
ruff check src/opnsense/ tests/unit/

# Format check
ruff format --check src/opnsense/ tests/unit/

# Auto-fix lint issues
ruff check --fix src/opnsense/ tests/unit/

# Type check
mypy src/opnsense/
```

---

## Pre-commit hooks

Install once on the host:

```bash
pip install pre-commit
pre-commit install
```

Hooks configured: `detect-secrets` (credential scanner) + `ruff` (lint + format).

---

## Commit and version standard

All commits MUST follow Conventional Commits format:

```
<type>[optional scope]: <description>

[optional body]
[optional footer: BREAKING CHANGE: ...]
```

| Type | Version bump | When |
|---|---|---|
| `fix:` | patch (0.0.x) | Bug fixes |
| `feat:` | minor (0.x.0) | New features |
| `fix!:` / `feat!:` / `BREAKING CHANGE:` | major (x.0.0) | Breaking changes |
| `docs:` `test:` `refactor:` `chore:` | none | Non-functional changes |

**Never:**
- Manual version edits in files
- `git tag` manually
- Non-conventional commit messages

---

## PR checklist

Before declaring any feature/fix done:

- [ ] All public methods have docstrings
- [ ] ensure() / idempotent pattern where applicable
- [ ] dry_run=True mode where applicable
- [ ] Unit tests — happy path + error codes
- [ ] Integration test — live or mocked
- [ ] PEP 8 + PEP 257 clean (ruff)
- [ ] Type hints on all public API (mypy clean)
- [ ] CHANGELOG entry with semantic version
- [ ] CLAUDE.md updated if state changed

---

## Release process

Never edit version numbers manually.

```
push commits with conventional messages -> release-please opens PR -> merge it -> done
```
