<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->

# Port Field Reference — lib-opnsense

> **Purpose:** Identify every port field across all managers. The lib stores
> field types as `str` to match the OPNsense MVC data model exactly.
> Port boundary validation (1-65535) is a **test concern**, not a type override.
> If the API re-scopes a field, the lib stays in sync.

## Port fields inventory

### Fields typed as `"port"` (strict numeric, 1-65535)

These are pure port fields — the API only accepts numeric values.

| Manager | Field | Validator type | Accepts |
|---|---|---|---|
| FwDnatManager | `local-port` | `port` | 1-65535, range (80:443) |
| WgServerManager | `port` | `port` | 1-65535 (e.g. 51820) |
| WgClientManager | `serverport` | `port` | 1-65535 |
| OvpnInstanceManager | `port` | `port` | 1-65535 (e.g. 1194) |
| SyslogDestManager | `port` | `port` | 1-65535 (e.g. 514) |

### Fields typed as `"str"` (port OR alias name)

The API validates server-side. The lib keeps `str` to match MVC model.

**IMPORTANT — tested on OPNsense 26.1.5:**
Filter rule port fields (`source_port`, `destination_port`) accept ONLY:
- Single numeric port: `443`
- Alias name: `inttest_web_ports`
- **NOT ranges** (`80:443` → rejected)
- **NOT comma-separated** (`80,443` → rejected)

To use multiple ports or ranges in a filter rule, create a **port alias** first:
```
alias content: "80\n443\n8080"   (multi-port)
alias content: "8000:8999"       (range)
→ reference alias name in rule destination_port field
```

| Manager | Field | Validator type | Single port | Alias name | Range | Comma-list |
|---|---|---|---|---|---|---|
| FwFilterManager | `source_port` | `str` | YES | YES | **NO** | **NO** |
| FwFilterManager | `destination_port` | `str` | YES | YES | **NO** | **NO** |
| FwSourceNatManager | `source_port` | `str` | YES | YES | **NO** | **NO** |
| FwSourceNatManager | `destination_port` | `str` | YES | YES | **NO** | **NO** |
| FwSourceNatManager | `target_port` | `str` | YES | YES | **NO** | **NO** |
| FwDnatManager | `source.port` (nested) | `str` | YES | YES | TBD | TBD |
| FwDnatManager | `destination.port` (nested) | `str` | YES | YES | TBD | TBD |
| TsRuleManager | `src_port` | `str` | YES | YES | TBD | TBD |
| TsRuleManager | `dst_port` | `str` | YES | YES | TBD | TBD |
| UbForwardManager | `port` | `str` | YES | NO | NO | NO |
| UbDotManager | `port` | `str` | YES | NO | NO | NO |

## What the API accepts — verified on 26.1.5

### Filter/SNAT rule port fields (FwFilterManager, FwSourceNatManager)

| Format | Accepted? | Tested? |
|---|---|---|
| Single port `443` | **YES** | P01 PASS |
| Alias name `inttest_web_ports` | **YES** | P04 PASS |
| Port alias with range content `8000:8999` | **YES** (via alias) | P04b PASS |
| Inline range `80:443` | **NO** — `OpnsenseValidationError` | P02 PASS (rejected) |
| Inline comma `80,443,8080` | **NO** — `OpnsenseValidationError` | P03 PASS (rejected) |
| Port 1 (min) | **YES** | P05 PASS |
| Port 65535 (max) | **YES** | P06 PASS |
| Port 0 | **NO** — `OpnsenseValidationError` | P07 PASS (rejected) |
| Negative `-1` | **NO** — `OpnsenseValidationError` | P08 PASS (rejected) |
| Port 125657 (>65535) | **NO** — `OpnsenseValidationError` | P09 PASS (rejected) |

### D-NAT local-port field (FwDnatManager)

| Format | Accepted? |
|---|---|
| Single port `8080` | YES |
| Range `80:443` | YES (D-NAT supports ranges) |

### Service port fields (WG, OVPN, Syslog)

| Format | Accepted? |
|---|---|
| Single integer `51820` | YES |
| Range/comma/alias | NO — strict IntegerField |

## Pattern: multiple ports in a filter rule

OPNsense filter rules do NOT accept inline port lists or ranges.
The correct pattern is:

1. Create a port alias with the ports/ranges you need
2. Reference the alias name in the rule's port field

```python
# Step 1: port alias with multiple ports
await alias_mgr.ensure("present", {
    "name": "web_ports", "type": "port",
    "content": "80\n443\n8080",
})

# Step 2: filter rule references alias by name
await filter_mgr.ensure("present", {
    "description": "allow-web",
    "destination_port": "web_ports",  # alias name, not inline ports
    ...
})
```

## Integration test results

All tests run on OPNsense 26.1.5 via `tests/integration/firewall/test_port_validation.py`:

| # | Test | Input | Result | Notes |
|---|---|---|---|---|
| P01 | Single port | `443` | PASS (created) | Universally accepted |
| P02 | Inline range | `80:443` | PASS (rejected) | API rejects — use alias |
| P03 | Inline comma-list | `80,443,8080` | PASS (rejected) | API rejects — use alias |
| P04 | Port alias (multi) | `inttest_web_ports` | PASS (created) | Alias has `80\n443\n8080` |
| P04b | Port alias (range) | `inttest_range_ports` | PASS (created) | Alias has `8000:8999` |
| P05 | Boundary min | `1` | PASS (created) | |
| P06 | Boundary max | `65535` | PASS (created) | |
| P07 | Port 0 | `0` | PASS (rejected) | API rejects below range |
| P08 | Negative | `-1` | PASS (rejected) | API rejects |
| P09 | Too high | `125657` | PASS (rejected) | API rejects above range |

## Utility validator

The lib provides `port_or_alias` and `port` validators in `core/validation.py`
for consumers who want client-side checking before API call:

```python
from opnsense.core.validation import ValidatorRegistry

registry = ValidatorRegistry()
# Strict numeric port (1-65535)
registry.validate_params({"port": "51820"}, {"port": {"type": "port"}})
# Port or alias name
registry.validate_params({"port": "inttest_web"}, {"port": {"type": "port_or_alias"}})
```

These are NOT wired into manager `_validators` (those match MVC types exactly).
Use them in Ansible modules, scripts, or test harnesses.
