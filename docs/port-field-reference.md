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

These accept numeric ports, ranges, comma-separated, or OPNsense alias names.
The API validates server-side. The lib keeps `str` to match MVC model.

| Manager | Field | Validator type | Accepts |
|---|---|---|---|
| FwFilterManager | `source_port` | `str` | port, range, alias name |
| FwFilterManager | `destination_port` | `str` | port, range, alias name |
| FwSourceNatManager | `source_port` | `str` | port, range, alias name |
| FwSourceNatManager | `destination_port` | `str` | port, range, alias name |
| FwSourceNatManager | `target_port` | `str` | port, range, alias name |
| FwDnatManager | `source.port` (nested) | `str` | port, range, alias name |
| FwDnatManager | `destination.port` (nested) | `str` | port, range, alias name |
| TsRuleManager | `src_port` | `str` | port, range, alias name |
| TsRuleManager | `dst_port` | `str` | port, range, alias name |
| UbForwardManager | `port` | `str` | numeric port |
| UbDotManager | `port` | `str` | numeric port |

## What the API accepts (from MVC model)

OPNsense `PortField` validates:
- Single port: `443`
- Port range: `80:443`
- Comma-separated: `80,443,8080`
- Alias name: `MyPorts`, `inttest_web_ports`

OPNsense `IntegerField` (for service ports like WireGuard, syslog):
- Single integer: `51820`
- Range: 1-65535

## What the API rejects

- Port 0 (reserved)
- Port > 65535 (e.g. 125657)
- Negative numbers
- Non-numeric strings on strict port fields (wg, ovpn, syslog)
- Empty string on required port fields

## Integration test coverage needed

Every port field must be tested with:

| # | Test case | Input | Expected API response |
|---|---|---|---|
| P01 | Valid port | `443` | accepted |
| P02 | Valid range | `80:443` | accepted (where supported) |
| P03 | Valid comma | `80,443,8080` | accepted (where supported) |
| P04 | Valid alias | `inttest_web_ports` | accepted (FW/shaper only) |
| P05 | Port 0 | `0` | rejected |
| P06 | Port > 65535 | `125657` | rejected |
| P07 | Negative port | `-1` | rejected |
| P08 | Random string | `not_a_port!` | rejected |
| P09 | Empty on required | `""` | rejected |
| P10 | Port 1 (min) | `1` | accepted |
| P11 | Port 65535 (max) | `65535` | accepted |

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
