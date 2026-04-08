> **Mandatory -- read before any work:**
> 1. `workspace/OPERATING-STANDARD.md` -- platform rules, quality gates, compliance
> 2. This file -- repo-specific context

# CLAUDE.md -- lib-opnsense

> **Scope:** `lib` | **Component:** `opnsense`
> **GitHub:** `by-openclaw/lib-opnsense`
> **Layer:** Layer 0 -- Edge & Routing

AI agent context. Read before touching any file.

---

## What This Repo Does

Async Python library for the OPNsense REST API -- CRUD for users, groups, privileges, and future firewall/DNS/VPN domains.
Published as a versioned package; consumed as a dependency by platform-setup and Ansible modules.

**NOT for:** direct deployment, VM provisioning, or any infra changes.

---

## HARD RULES -- Non-negotiable. Read before touching any file.

These are architectural decisions. They are NOT suggestions. Do not override them.

### HTTP client -- httpx only (ADR-0029)
- **ALWAYS use `httpx` with `async/await`.** No `urllib`, `requests`, or `aiohttp`.
- `httpx.AsyncClient` provides HTTP/2, connection pooling, and native async support.
- Rationale: ADR-0029 in doc-platform-core promotes async-first design for all new libraries.
- If you think urllib is simpler -- it doesn't matter. The decision is made.

### ensure() pattern on all managers (ADR-0029 promotes lib-synology-dsm ADR-0002)
- Every manager MUST implement `ensure()` with fetch-diff-noop semantics.
- `ensure()` must return `EnsureResult(changed=False, action="noop")` when state already matches -- never re-apply.
- `check_mode=True` must be supported on all destructive methods.
- All managers inherit from `BaseManager` (except `AuthPrivManager` which uses assignment semantics).

### Credential providers -- no hardcoded credentials (ADR-0029)
- Never hardcode credentials in source. Use `EnvCredentialProvider` or `get_credentials()`.
- Environment variables: `OPN_HOST`, `OPN_KEY`, `OPN_SECRET`, `OPN_PORT`, `OPN_VERIFY_SSL`.
- Vault integration is Phase 2 -- blocked until Vault is deployed.

### Commit and version discipline
- All commits MUST follow Conventional Commits format.
- Release Please is the canonical release path.
- Never manually edit version strings. Never run `cz bump` if Release Please is active.

---

## Current State (v0.2.0)

| Component | Status |
|---|---|
| OpnsenseClient (httpx async, retry, exception mapping) | Done |
| core/identity.py -- IdentityResolver (composite match keys) | Done |
| core/diff.py -- DiffEngine (state comparison + enum normalization) | Done |
| core/redaction.py -- Redactor (unified field redaction) | Done |
| core/validation.py -- FieldValidator protocol + ValidatorRegistry | Done |
| core/endpoint.py -- EndpointConfig + EndpointResolver | Done |
| core/logging_helpers.py -- ManagerLogBuilder (structured logs) | Done |
| managers/base.py -- BaseManager (thin orchestrator, composes core/) | Done |
| managers/protocols.py -- ManagerProtocol (typing.Protocol for DI) | Done |
| Auth managers (user, group, priv, api_key) | Done |
| Firewall managers (alias, filter, dnat, snat, onetoone, category, group) | Done |
| Interface managers (vlan, vip) | Done |
| Traffic shaper (pipe) | Done |
| Exception hierarchy (OpnsenseError -> 8 typed exceptions + FieldValidationError) | Done |
| Credential provider (env vars + .env) | Done |
| EnsureResult frozen dataclass | Done |
| Unit tests (377 tests) | Done |
| Integration tests (133 tests on live OPNsense 26.1.5) | Done |
| CI: ruff + mypy + bandit + pytest (Python 3.10-3.13) | Done |
| Dev container (.devcontainer/) | Done |
| Ansible collection | Phase 2 |
| Vault AppRole auth | Phase 2 -- blocked until Vault deployed |

---

## Key Files

| File | Why |
|---|---|
| `README.md` | Install, quickstart, API reference |
| `src/opnsense/client.py` | Async REST client -- httpx, retry, exception mapping |
| `src/opnsense/exceptions.py` | ALL exceptions (OpnsenseError hierarchy + FieldValidationError) |
| `src/opnsense/credentials.py` | Credential providers (env, future Vault) |
| `src/opnsense/logging.py` | Structlog config (delegates to core/redaction) |
| `src/opnsense/validators.py` | Backward-compat shim (delegates to core/validation) |
| `src/opnsense/core/` | Cross-cutting concerns -- independently reusable, zero manager coupling |
| `src/opnsense/core/identity.py` | IdentityResolver -- composite match key lookup |
| `src/opnsense/core/diff.py` | DiffEngine -- state comparison + OPNsense enum normalization |
| `src/opnsense/core/redaction.py` | Redactor -- unified field redaction with partial reveal |
| `src/opnsense/core/validation.py` | FieldValidator protocol + ValidatorRegistry + 11 built-in types |
| `src/opnsense/core/endpoint.py` | EndpointConfig + EndpointResolver -- URL construction |
| `src/opnsense/core/logging_helpers.py` | ManagerLogBuilder -- structured log dict construction |
| `src/opnsense/managers/base.py` | BaseManager -- thin orchestrator composing core/ components |
| `src/opnsense/managers/protocols.py` | ManagerProtocol -- typing.Protocol for consumer DI |
| `src/opnsense/managers/auth_user.py` | AuthUserManager -- local user CRUD (~30 lines, config only) |
| `src/opnsense/managers/auth_group.py` | AuthGroupManager -- local group CRUD |
| `src/opnsense/managers/auth_priv.py` | AuthPrivManager -- privilege assignment (standalone) |
| `src/opnsense/managers/auth_api_key.py` | AuthApiKeyManager -- API key CRUD (standalone) |
| `src/opnsense/managers/fw_filter.py` | FwFilterManager -- firewall filter rules |
| `src/opnsense/models/base.py` | EnsureResult frozen dataclass |
| `tests/unit/` | Unit tests (377 tests) |
| `tests/unit/core/` | Core module tests (110 tests) |
| `tests/integration/` | Integration tests (133 tests, live OPNsense device) |
| `CHANGELOG.md` | Semantic versioning history |

---

## API gotchas (read before touching any manager code)

These are confirmed behaviours from OPNsense 26.1.5. Source: `platform-setup/tools/opnsense/docs/api-developer-guide.md`.

> **Minimum version: OPNsense >= 26.1.** Versions before 26.1 are missing MVC
> controllers for D-NAT (Port Forward), interface settings, and other core
> features. These were migrated from legacy PHP across the 25.x → 26.1 cycle.
> See `platform-setup/tools/opnsense/log/api-schema-probe/README.md` for the
> full version compatibility matrix.

- **POST bodies wrap in a payload key** -- the key varies per controller (e.g. `{"user": {...}}`, `{"group": {...}}`). Every manager sets `_payload_key` for this.
- **Booleans are strings "1"/"0"** -- OPNsense API does not use native JSON booleans. Always send `"1"` or `"0"`.
- **Enums are dicts when reading, plain strings when writing** -- a GET returns `{"scope": {"local": {"value": "Local", "selected": 1}}}` but a POST expects `{"scope": "local"}`.
- **Changes are staged until reconfigure/apply** -- most OPNsense modules (Unbound, HAProxy, firewall rules) require an explicit `POST /api/{module}/service/reconfigure` after CRUD operations to apply changes.
- **Auth is immediate** -- user/group/privilege changes take effect without reconfigure. Auth managers set `_apply_endpoint = None`.
- **Search endpoints return paginated results** -- `{"rows": [...], "rowCount": N, "total": N, "current": 1}`. The client `search()` method extracts `rows`.
- **Create returns UUID** -- successful `add*` endpoints return `{"uuid": "..."}`.
- **Validation errors on HTTP 200** -- some endpoints return `{"result": "failed", "validations": {...}}` with a 200 status code. The client detects this and raises `OpnsenseValidationError`.

---

## Error handling pattern

All manager mutations (create, update, delete, priv assign) use:
```python
try:
    result = await client.create(...)
    await self._apply()
except Exception as exc:
    logger.error("create failed ...", extra={...})  # always logged
    raise                                           # always re-raised
```

Consumers MUST use try/except/finally:
```python
try:
    result = await mgr.ensure("present", params)
except OpnsenseValidationError as exc:
    logger.error("Validation: %s", exc.validations)
except OpnsenseAuthError:
    logger.critical("Auth failed — check API key")
except OpnsenseError as exc:
    logger.error("API error: %s", exc)
finally:
    # cleanup, close connections, report status
    pass
```

## Logging

- Uses **structlog** with colorized console + Loki JSON file output
- Redaction: unified in `src/opnsense/core/redaction.py` (logging.py delegates to it)
- Severity: DEBUG=noop, INFO=create/update, WARNING=delete, ERROR=failure, CRITICAL=auth
- Configure: `from opnsense.logging import configure_logging`
- Log file path set by consumer (tests: `tests/integration/logs/inttest.log`)

---

## Constraints

- Never commit OPNsense credentials or API keys
- `tests/` must pass before any merge to `main`
- Breaking changes = MAJOR version bump + migration note in CHANGELOG
- `ruff` linting must be clean before commit
- `mypy` must be clean before commit

---

## Cross-repo References

All paths are relative from sibling repo clones (e.g. `../doc-platform-core/`).

| ADR / Doc | Repo | Relative path |
|-----------|------|---------------|
| ADR-0029: Python Library Design Standard | doc-platform-core | `../doc-platform-core/docs/adr/0029-python-library-design-standard.md` |
| ADR-0030: Automation Naming Convention | doc-platform-core | `../doc-platform-core/docs/adr/0030-automation-naming-convention.md` |
| ADR-0031: CI Token & Identity Standard | doc-platform-core | `../doc-platform-core/docs/adr/0031-ci-token-identity-standard.md` |
| ADR-0010: Naming & Identity Convention | doc-platform-core | `../doc-platform-core/docs/adr/0010-naming-and-identity-convention.md` |
| OPNsense API Developer Guide | platform-setup | `../platform-setup/tools/opnsense/docs/api-developer-guide.md` |
| OPNsense API Schema Audit | platform-setup | `../platform-setup/tools/opnsense/docs/api-schema-audit.md` |
| OPNsense API Route Catalog | platform-setup | `../platform-setup/tools/opnsense/docs/api-route-catalog.md` |

---

## Related

- Platform charter: `../doc-platform-core/docs/adr/0006-platform-charter.md`
- RAID: [`RAID.md`](RAID.md) (this repo)
- GitHub Issues: <https://github.com/by-openclaw/lib-opnsense/issues>
