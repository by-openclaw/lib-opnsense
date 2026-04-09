<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->

# lib-opnsense — OOP Refactor Scope of Work

> **Status:** Complete (PRs #29, #30, #31 merged)
> **Date:** 2026-04-08 (completed 2026-04-08)
> **Driver:** ADR-0029 compliance — separation of concerns, reusable components

---

## Problem

BaseManager is a 707-line god class. Eight concerns are mixed into one file.
Components cannot be reused independently. Flat validators, no interfaces,
cross-cutting concerns embedded in business logic.

---

## 1. Concerns to Separate

| # | Concern | Current location | Problem |
|---|---|---|---|
| 1 | Identity resolution | base.py _find_existing, _match_keys | Can't test or reuse without full manager |
| 2 | Diff computation | base.py _compute_diff | OPNsense enum normalization buried in god class |
| 3 | Redaction | base.py _redact + logging.py _redact_value | Two implementations, not unified |
| 4 | Validation | validators.py flat functions | Not extensible, FieldValidationError in wrong file |
| 5 | CRUD operations | base.py list/get/create/update/delete | 30-50 lines each mixing HTTP + logging + redaction |
| 6 | Ensure orchestration | base.py ensure() | 70 lines tightly coupled to all concerns |
| 7 | Logging / observability | 20+ logger calls scattered in base.py | 40% of line count is log dict construction |
| 8 | Error handling | try/except blocks in every method | Identical boilerplate in every CRUD method |

---

## 2. Proposed File Structure

```
src/opnsense/
├── __init__.py                    # Public API exports
├── client.py                      # Transport only (unchanged)
├── credentials.py                 # Credential providers (unchanged)
├── exceptions.py                  # ALL exceptions (+ FieldValidationError moved here)
├── logging.py                     # Structlog config (delegates to core/redaction)
│
├── core/                          # Extracted cross-cutting concerns
│   ├── __init__.py
│   ├── identity.py                # IdentityResolver — match keys + find_existing
│   ├── diff.py                    # DiffEngine — state comparison + enum normalization
│   ├── redaction.py               # Redactor — unified field redaction
│   ├── validation.py              # FieldValidator protocol + registry + built-ins
│   ├── endpoint.py                # EndpointResolver — URL construction from config
│   └── logging_helpers.py         # ManagerLogBuilder — structured log construction
│
├── managers/
│   ├── __init__.py
│   ├── base.py                    # BaseManager — thin orchestrator (~150 lines)
│   ├── protocols.py               # Manager protocol (typing.Protocol)
│   ├── auth_user.py               # Config only (~30 lines)
│   ├── auth_group.py
│   ├── auth_priv.py               # Standalone (not BaseManager)
│   ├── auth_api_key.py            # Standalone (not BaseManager)
│   ├── fw_alias.py
│   ├── fw_filter.py
│   ├── fw_dnat.py
│   ├── fw_source_nat.py
│   ├── fw_category.py
│   ├── fw_group.py
│   ├── fw_one_to_one.py
│   ├── if_vlan.py
│   ├── if_vip.py
│   └── ts_pipe.py
│
├── models/
│   ├── __init__.py
│   ├── base.py                    # EnsureResult
│   ├── auth_user.py               # Typed frozen dataclass
│   └── auth_group.py              # Typed frozen dataclass
│
└── _types.py                      # Shared type aliases
```

---

## 3. What Each Class Owns

### core/identity.py — IdentityResolver

Owns: match key resolution, composite identity lookup, AmbiguousMatchError.

Accepts a `list_fn: Callable` — no coupling to BaseManager. Usable with any data source.

### core/diff.py — DiffEngine

Owns: field comparison, OPNsense enum dict normalization. Stateless, no dependencies.

### core/redaction.py — Redactor

Owns: unified redaction with configurable rules. Replaces both BaseManager._redact()
and logging.py._redact_value(). logging.py delegates to this.

### core/validation.py — FieldValidator protocol + registry

Owns: all client-side validation. Each type is a class implementing FieldValidator protocol.
Registry allows custom validators without modifying source.

### core/endpoint.py — EndpointResolver

Owns: URL construction from EndpointConfig dataclass. Replaces inline f-strings.

### core/logging_helpers.py — ManagerLogBuilder

Owns: structured log dict construction, timing, severity mapping. Encapsulates the logging
contract table.

### managers/protocols.py — ManagerProtocol

Owns: typing.Protocol defining what a manager looks like. Consumers depend on this, not concrete class.

### managers/base.py — BaseManager (~150 lines)

Owns: orchestration only. Composes all core/ components. ensure() is ~30 lines.

### Concrete managers — config only (~30 lines each)

Own: endpoint config, match keys, validators, redact fields. Zero logic.

---

## 4. Unit Test Use Cases Per Concern

### Identity Resolution (core/identity.py)
- Single match key resolves correctly
- Composite match keys (2+ fields) resolve correctly
- Zero matches returns None
- Single match returns that row
- Multiple matches raises AmbiguousMatchError with UUIDs
- match_label produces "key1=val1 key2=val2"

### Diff Engine (core/diff.py)
- Identical dicts returns None
- Single field difference returns that field
- Fields in desired but missing from current are skipped
- OPNsense enum dict {"selected": "1"} normalizes correctly
- OPNsense enum dict {key: {"value": "X", "selected": 1}} normalizes correctly
- Extra fields in current are ignored

### Redaction (core/redaction.py)
- Full redaction (0, 0) replaces entire value
- Partial reveal start/end/both
- Value shorter than reveal window → full redaction
- Field not in rules passes through
- redact_dict deep-copies

### Validation (core/validation.py)
- Required field missing/empty raises error
- Optional field missing passes
- Each of 11 types: valid input passes, invalid raises FieldValidationError
- Custom validator registered via registry works
- FieldValidationError carries field, value, rule

### Endpoint Resolution (core/endpoint.py)
- Each CRUD action constructs correct URL per suffix
- Custom suffixes (Item, Rule, Pipe, bare)

### Logging Helpers (core/logging_helpers.py)
- Correct severity per action (INFO/WARNING/DEBUG/ERROR)
- duration_ms calculated correctly
- All fields present in extra dict

### BaseManager Orchestration (thin)
- ensure(present) + not found → create
- ensure(present) + found + no diff → noop
- ensure(present) + found + diff → update
- ensure(absent) + found → delete
- ensure(absent) + not found → noop
- ensure(uuid=) bypasses find_existing
- Validation runs before API call (present only)

---

## 5. Integration Test Use Cases

Per domain, on live OPNsense device:
- Auth: user/group/priv/apikey CRUD lifecycle + idempotency
- Firewall: alias/filter/dnat/snat/category/group/onetoone CRUD + disabled rules
- Interfaces: vlan/vip CRUD + composite key identity
- Traffic shaper: pipe CRUD + custom search endpoint
- Cross-cutting: check_mode, AmbiguousMatchError, concurrent ensure via asyncio.gather

---

## 6. Error Handling Test Use Cases (per ADR-0029 §10)

### Per manager (mandatory)
- create/update/delete failure: logs ERROR, re-raises unchanged
- Exception type preserved through manager layer
- FieldValidationError raised before API call

### Consumer pattern
- Typed exception caught by most-specific handler
- finally block runs on success AND failure

### Transport-level
- 401 → OpnsenseAuthError
- 403 → OpnsensePermissionError
- 404 → OpnsenseEndpointMissingError
- 400 → OpnsenseValidationError with validations dict
- 500 → retries then OpnsenseServerError
- Connection refused → OpnsenseConnectionError
- Timeout → OpnsenseTimeoutError

---

## 7. Reusability Matrix

| Component | Usable without | Standalone use case |
|---|---|---|
| core/diff.py | Everything | Compare any two dicts (Ansible diff, CI drift) |
| core/redaction.py | Everything | Redact fields in any context |
| core/validation.py | Everything | Validate input in CLI tools, Ansible, Terraform |
| core/identity.py | Manager (needs list_fn) | Find resource in any list of dicts |
| core/endpoint.py | Everything | Generate API URLs for docs, curl scripts |
| exceptions.py | Everything | Catch typed errors in any consumer |
| models/base.py | Everything | EnsureResult usable in any ensure-style function |

---

## 8. Implementation Sequence

| Phase | What | Breaking? | Status |
|---|---|---|---|
| 1 | Extract core/ pure utilities (diff, redaction, validation, endpoint, identity, logging_helpers) | No — internal refactor | Done (PR #29) |
| 2 | Wire core/ into BaseManager, add protocols, extract logging | No — same public API | Done (PR #30) |
| 3 | Clean up validators.py shim, export ManagerProtocol | No — same public API | Done (PR #31) |
| 4 | Unit tests per core/ module + update existing tests | No | Done (110 new tests, 377 total) |
| 5 | Integration tests verify no regression + docs update | No | Done (133 integration tests unchanged) |

Public API surface (ensure, list, get, create, update, delete) stays identical.
All 377 unit tests + 133 integration tests pass with zero regressions.
