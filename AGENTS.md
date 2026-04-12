# AGENTS.md -- lib-opnsense

Async Python library for OPNsense REST API -- auth user/group/privilege CRUD with ensure() idempotency.

## Always Read First

Before touching anything in this repo:

1. [`README.md`](README.md) -- library overview, usage, architecture
2. [`CLAUDE.md`](CLAUDE.md) -- agent-specific constraints, API quirks, hard rules
3. `platform-setup/tools/opnsense/docs/api-developer-guide.md` -- OPNsense API behaviour reference
4. [`src/opnsense/`](src/opnsense/) -- library source

## Mandatory reading before acting

Before writing, editing, or reviewing any file in this repo, read:

### doc-platform-core repo (sibling clone):
1. `../doc-platform-core/docs/standards/` -- all standards files
2. `../doc-platform-core/docs/adr/` -- all Accepted ADRs
3. ADR template: `../doc-platform-core/docs/templates/adr-template-lib.md`

### lib repos (lib-opnsense, this repo):
1. `docs/adr/` -- lib-scoped ADRs (when created)
2. Platform standards are NOT binding on lib repos -- but lib CISO sections must reference them

### Rules:
- Do NOT infer. Do NOT invent policy. If a standard or ADR covers it -- follow it.
- If you would override a standard -- flag it with `[OVERRIDE REQUIRED]`, do NOT do it silently.
- Cross-ADR dependencies are FORBIDDEN. Each ADR is self-contained.

## Coding & Commit Standards

- **Python style:** PEP 8, type hints on all public methods, docstrings on all public classes/methods
- **Async/await:** All client and manager methods are async. Use `async def` and `await`.
- **Linting:** `ruff` -- must be clean before commit
- **Type checking:** `mypy` -- must be clean before commit
- **Conventional Commits** -- `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `test`, `ci`, `refactor`, `chore`
  - Examples:
    - `feat(auth): add privilege assignment manager`
    - `fix(client): handle timeout on reconfigure endpoint`
    - `test(unit): add AuthGroupManager ensure tests`
    - `docs(readme): update manager table`
- **Branch naming:** `feat/{issue-id}-{description}` or `fix/{issue-id}-{description}`
- **All new managers** must implement `ensure(state=present|absent)` idempotent pattern
- **httpx only** -- ADR-0029 decision: async-first design with httpx

## Project Health Rules (mandatory)

- **Test fails -> open issue immediately.** Never fix silently. Issue first -> fix -> close with comment + commit ref.
- **Issue closed = CI green + specific test covers the fix.** No exceptions.
- **CI failure on main** that isn't already tracked -> create a GitHub issue before anything else.
- **Every open issue** has a label, is on the Project board, has a linked commit or PR when closed.
- README reflects actual state -- not aspirational. Update after every release.
- AGENTS.md + CLAUDE.md updated after every non-trivial change.

## What NOT To Do

> Also read `CLAUDE.md` HARD RULES -- architectural decisions enforced there. AGENTS.md and CLAUDE.md are both authoritative. When in doubt, CLAUDE.md wins.

- Do NOT run live integration tests without first setting OPN_HOST/OPN_KEY/OPN_SECRET
- Do NOT publish to PyPI without explicit instruction from @yboujraf
- Do NOT use urllib, requests, or aiohttp -- httpx only
- Do NOT hardcode credentials in source or tests

## Test Device

**OPNsense 26.1.5** at `opnsense.example.com` (port 443).

### `svc-rune` -- API executor
- API key stored in `.env` (gitignored)
- Full API access for integration tests
- Environment variables: `OPN_HOST`, `OPN_KEY`, `OPN_SECRET`

## GitHub Repo

<https://github.com/by-openclaw/lib-opnsense>

## Agent: Rune

Maintained by Rune (DevOps familiar) for the BY-SYSTEMS PoC platform.
Owner: @yboujraf

---

## Project Stats

> Auto-updated on every release. Last updated: 2026-04-11

| Metric | Value |
|---|---|
| Version | v1.0.0 |
| Tagged releases | 1 |
| Unit tests | 1,207 |
| Integration tests | ~360 (49 files across 10 scopes) |
| Python source files | 144 |
| Managers | 54 (all integration tested) |
| Models | 50 frozen dataclasses |
| Open issues | 0 |
| CI workflows | ruff + mypy + bandit + pytest (3.10-3.13) |
| Pre-commit hooks | Active |
| Dev container | Active |
| mypy | Clean |
