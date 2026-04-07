<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->

# OPNsense API Schema Probe — Output Directory

> **Purpose:** Stores raw JSON probe output per OPNsense firmware version.
> Each subdirectory is named after the probed version (e.g. `26.1.5/`, `25.1.12/`).

## Directory Layout

```
docs/api/data/
  latest -> 26.1.5            # symlink to most recent probe
  26.1.5/                     # OPNsense 26.1.5 probe output
    version.json              # firmware version + probe metadata
    manifest.jsonl            # one JSON line per probed endpoint
    {label}__{type}.json      # response body (schema/search/global)
    {label}__{type}.http      # HTTP status code
    {label}__{type}.request.json  # request body (for POST searches)
    probe-{timestamp}.log     # human-readable probe log
  25.1.12/                    # previous versions kept for comparison
    ...
```

## Version Tracking

Every probe run auto-detects the OPNsense firmware version by calling
`GET /api/core/firmware/info` before probing. The version is stored in:

1. **`version.json`** — machine-readable metadata per probe run
2. **`manifest.jsonl`** — each line includes the probe context

### version.json schema

```json
{
  "opnsense_version": "26.1.5",
  "product": "OPNsense",
  "arch": "amd64",
  "host": "https://opnsense.example.com",
  "probe_timestamp": "2026-04-05T10:24:10Z",
  "probe_script": "probe-api-schemas.sh"
}
```

## How to Re-probe After Upgrade

```bash
# 1. Run the probe (auto-detects version, creates new subdir)
cd scripts
./probe-api-schemas.sh

# 2. Check what changed
git diff docs/api/data/

# 3. Compare two versions side-by-side
diff docs/api/data/25.1.12/manifest.jsonl \
     docs/api/data/26.1.5/manifest.jsonl
```

## Idempotency

The probe is **fully idempotent and read-only**:
- Schema probes: `GET /api/{controller}/get_{entity}` (no UUID = empty schema)
- Search probes: `POST /api/{controller}/search_{entity}` (read-only search)
- Global probes: `GET /api/{controller}/get` or `/status` (read-only)

No configuration is created, modified, or deleted. Safe to re-run at any time.

## Probe History

| Version | Date | Endpoints | OK | Failed |
|---------|------|-----------|----|--------|
| 25.1.12 | 2026-04-04 | 205 | 192 | 13 |
| 25.7.0 | 2026-04-05 | 205 | 192 | 13 |
| 25.7.11 | 2026-04-05 | 205 | 198 | 7 |
| 26.1.5 | 2026-04-05 | 200 | 200 | 0 |

## Minimum Version Requirement

> **OPNsense >= 26.1 is required for full API coverage.**
>
> Versions before 26.1 are missing critical MVC controllers for NAT, interface
> settings, and other core features. These are **not** plugin issues — the
> controllers were migrated from legacy PHP to MVC/API across the 25.x → 26.1 cycle.

### Endpoints that fail on < 26.1

| Endpoint | Controller | Available from |
|----------|-----------|----------------|
| `firewall/d_nat/*` | D-NAT (Port Forward) | **26.1** |
| `interfaces/settings/get` | Interface settings | **26.1** |
| `captiveportal/service/status` | Captive Portal status | **25.7.11+** |
| `radvd/*` | Router Advertisements | Removed — moved to core in 25.7 |
| `ntpd/*` | NTPd | Removed — replaced by `os-chrony` plugin |
| `hostdiscovery/*` | Host Discovery | Removed — no replacement |
| `firewall/filter_base/get` | Abstract base controller | Not a real endpoint |

### Required plugins (install via `System > Firmware > Plugins` or API)

| Plugin | Provides | Install command |
|--------|----------|-----------------|
| `os-chrony` | `chrony/general/get`, `chrony/service/status` | `POST /api/core/firmware/install/os-chrony` |
| `os-lldpd` | `lldpd/general/get`, `lldpd/service/status` | `POST /api/core/firmware/install/os-lldpd` |

> After installing plugins, a firmware update + reboot may be required for
> controllers to become active.
