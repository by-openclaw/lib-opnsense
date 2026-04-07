<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->
# API Discovery Methodology — Reproducible Pattern

> **Purpose:** Teach any agent or developer how to discover, probe, and document
> a REST API for any product — not just OPNsense. This is the template for
> building `lib-*` libraries (lib-opnsense, lib-synology-dsm, lib-arista, etc.).
>
> **This file is the process. The other docs are the output.**

---

## Overview: Two-Step Discovery

Every API automation project starts with two distinct steps:

| Step | Input | Output | Needs live device? |
|------|-------|--------|--------------------|
| **1. Route discovery** | Vendor docs, WebUI, Swagger/OpenAPI | Endpoint catalog (paths + methods) | No |
| **2. Schema probe** | Live device + credentials | Field-level data model (types, enums, defaults) | Yes |

**Why two steps?**
- Step 1 tells you **what exists** — every endpoint, method, and URL pattern.
- Step 2 tells you **how it works** — actual field names, value types, enum options, defaults.
- Vendor docs are often incomplete or wrong. The live probe is ground-truth.

---

## Step 1: Route Discovery (no device needed)

### Goal

Build a complete catalog of every API endpoint: method, path, description, parameters.

### Sources (in priority order)

| Source | Reliability | How to access |
|--------|-------------|---------------|
| **Swagger / OpenAPI spec** | High | Check `/api/docs`, `/swagger.json`, `/openapi.yaml` |
| **Official API docs** | Medium | Vendor documentation site |
| **WebUI network inspector** | High | Browser DevTools > Network tab while clicking through UI |
| **Source code** (if open) | Highest | GitHub/GitLab repo, grep for route definitions |
| **Community wikis / forums** | Low | Google, Reddit, vendor forums |

### Process

1. **Check for Swagger/OpenAPI first.** If the product exposes a spec, download it —
   this gives you routes, methods, parameters, and response schemas in one shot.
   Most modern products do. OPNsense does not (which is why we built the probe).

2. **Scrape official docs.** Parse the vendor's API reference page. Extract:
   - HTTP method (GET, POST, PUT, DELETE)
   - URL path pattern (e.g. `/api/firewall/alias/get_item/{uuid}`)
   - Description / purpose
   - Required parameters

3. **Inspect WebUI traffic.** Open the product's web interface, open browser DevTools
   (Network tab), and click through every configuration page. Filter by XHR/Fetch.
   This reveals:
   - Undocumented endpoints the UI uses internally
   - Actual request/response payloads
   - Auth headers and token patterns

4. **Organize by domain.** Group endpoints into topics (auth, firewall, dns, vpn, etc.)
   and write them into a route catalog markdown file.

### Output

A file like `docs/api-route-catalog.md` with one table per domain:

```markdown
## Firewall — Alias

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/firewall/alias/get_item/{uuid} | Get alias by UUID |
| GET | /api/firewall/alias/get_item | Get empty alias schema |
| POST | /api/firewall/alias/search_item | Search/list aliases |
| POST | /api/firewall/alias/add_item | Create alias |
| POST | /api/firewall/alias/set_item/{uuid} | Update alias |
| POST | /api/firewall/alias/del_item/{uuid} | Delete alias |
| POST | /api/firewall/alias_util/reconfigure | Apply staged changes |
```

### Confidence model

Tag each route with how it was discovered:

| Tag | Meaning |
|-----|---------|
| `DOC` | Found in official vendor documentation |
| `UI_OBSERVED` | Seen in WebUI network traffic |
| `LIVE_TESTED` | Confirmed working against a live device |
| `INFERRED` | Guessed from naming pattern (not yet confirmed) |

---

## Step 2: Schema Probe (live device required)

### Goal

For every endpoint from Step 1, capture the **actual data model**: field names,
value types, enum options, default values, and response structure.

### The Key Insight

Many REST APIs return an **empty schema** when you call the "get" endpoint
without a UUID. This reveals every field, its type, and default value — without
creating or modifying anything.

```
GET /api/{controller}/get_{entity}         → empty schema (all fields + enums)
GET /api/{controller}/get_{entity}/{uuid}  → populated record
POST /api/{controller}/search_{entity}     → list of existing records (row shape)
```

This pattern works for:
- **OPNsense** — `get_item`, `get_rule`, `get_server` (no UUID = empty schema)
- **Synology DSM** — `SYNO.{API}.get` with `version=1` returns field definitions
- **Any CRUD API** — try calling the "get one" endpoint without an ID

If the product doesn't support empty-schema GET, fall back to:
- Creating a dummy record and immediately reading it back
- Parsing the Swagger/OpenAPI spec from Step 1
- Reading the WebUI form fields from the HTML source

### Probe Script Pattern

The probe script follows this structure for any product:

```bash
#!/usr/bin/env bash
# 1. Detect product version (for tracking)
# 2. Create versioned output directory
# 3. For each endpoint in registry:
#    a. Call the endpoint (read-only only!)
#    b. Save response JSON + HTTP status
#    c. Write manifest entry
# 4. Generate markdown audit from JSON
```

**Safety rules:**
- NEVER call mutation endpoints (add, set, del, toggle, restart, etc.)
- Only call read-only endpoints (get, search, list, status, info)
- Use a deny-regex to block unsafe paths
- Use an allow-regex for POST endpoints that are actually read-only (search)

### Adaptation Guide — What to Change Per Product

| Component | OPNsense | Synology DSM | Arista EOS |
|-----------|----------|--------------|------------|
| **Auth** | HTTP Basic (API key:secret) | `SYNO.API.Auth` session token | eAPI JSON-RPC with Basic auth |
| **Version endpoint** | `GET /api/core/firmware/info` | `SYNO.DSM.Info` | `show version \| json` via eAPI |
| **Schema discovery** | `GET get_{entity}` (no UUID) | `SYNO.{API}.get` | Swagger at `/swagger.json` |
| **Search/list** | `POST search_{entity}` | `SYNO.{API}.list` | `show running-config \| json` |
| **Safety deny regex** | `/add\|set\|del\|toggle/` | `/create\|delete\|set\|apply/` | `configure` commands |
| **Payload key** | Top-level key wraps entity (e.g. `{"alias": {...}}`) | `data` key in response | `result` array |

### Version Tracking

Every probe run MUST record:

```json
{
  "product_version": "25.7",
  "product": "OPNsense",
  "arch": "amd64",
  "probe_timestamp": "2026-04-05T10:24:10Z",
  "probe_script": "probe-api-schemas.sh"
}
```

**Why:** Without version tracking, you can't tell if a 404 is a missing plugin
or a version gap. You waste time re-probing the same version. And you can't
diff schemas across upgrades.

**Directory structure:**
```
docs/api/data/
  latest -> 26.1.5        # symlink to current
  26.1.5/                  # one subdir per version
    version.json
    manifest.jsonl
    *.json, *.http
  25.1.12/                # previous versions kept for comparison
    ...
```

### Output

A file like `docs/api-schema-audit.md` — the ground-truth for lib development:
- Version metadata table in header
- Per-endpoint sections with field tables (name, default, type)
- Enum values listed inline
- Search row samples
- Failed endpoint summary with HTTP codes

---

## Step 3: Build the Library

With the route catalog (Step 1) and schema audit (Step 2), you have everything
needed to build a `lib-*` Python library:

1. **Client class** — wraps HTTP calls, auth, retry, error mapping
2. **Manager classes** — one per domain, implements `ensure(state, params, check_mode)`
3. **Exception hierarchy** — typed errors mapped from HTTP status codes
4. **Models** — `EnsureResult` dataclass with changed/action/uuid/before/after

The schema audit is your **test fixture source** — use real field names, enum values,
and defaults from the probe to build realistic unit tests.

See:
- `lib-opnsense/` for the reference implementation
- ADR-0029 for the Python library design standard
- ADR-0030 for naming conventions

---

## Checklist — Reproducing for a New Product

- [ ] **Step 1a:** Check if Swagger/OpenAPI spec exists
- [ ] **Step 1b:** Scrape official API docs into route catalog
- [ ] **Step 1c:** Inspect WebUI network traffic for undocumented endpoints
- [ ] **Step 1d:** Write `docs/api-route-catalog.md` with confidence tags
- [ ] **Step 2a:** Write probe script adapted from OPNsense template
- [ ] **Step 2b:** Customize: auth method, version endpoint, safety regex
- [ ] **Step 2c:** Build endpoint registry array
- [ ] **Step 2d:** Run probe, generate `docs/api-schema-audit.md`
- [ ] **Step 2e:** Verify version.json written with correct metadata
- [ ] **Step 3a:** Create `lib-{product}` repo following ADR-0029
- [ ] **Step 3b:** Build client, managers, exceptions from schema audit
- [ ] **Step 3c:** Write unit tests using schema audit as fixture source
- [ ] **Step 3d:** Achieve 80%+ coverage, CI green

---

## File Map — Where Everything Lives

```
tools/{product}/
  docs/
    api-route-catalog.md       # Step 1 output — all endpoints
    api-schema-audit.md        # Step 2 output — field-level data model
    api-developer-guide.md     # Consumer docs — how to CRUD any resource
    api-discovery-methodology.md  # This file — how to reproduce
    rest-api-reference.md      # Deep reference — types, conventions, gaps
  scripts/
    probe-api-schemas.sh       # Step 2 script — probe live device
    build-api-schema-audit.sh  # Step 2 script — JSON to markdown
  log/
    api-schema-probe/          # Step 2 raw output (gitignored)
      {version}/
        version.json
        manifest.jsonl
        *.json, *.http
  config/
    api-env.sh                 # Credentials (gitignored)
    api-env.sh.example         # Template for credentials
```

---

> This methodology was developed during the OPNsense automation project (2026-04).
> It produced 192/205 successful endpoint probes and became the foundation for
> lib-opnsense and ansible-opnsense.
