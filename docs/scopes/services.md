<!--
  Copyright BY-SYSTEMS SRL
  SPDX-License-Identifier: MIT
  https://github.com/by-openclaw/lib-opnsense
-->

# Services Scope — lib-opnsense

## Overview
5 managers: CronJobManager, SyslogDestManager, CpZoneManager, DdnsAccountManager, PluginManager (custom).
Mixed responsibilities — system services that don't fit other scopes.

## Managers
- CronJobManager: cron/settings, suffix=Job (search: searchJobs). Match: description. Module: `opnsense.managers.services.cron_job`
- SyslogDestManager: syslog/settings, suffix=Destination (search: searchDestinations). Match: description. Module: `opnsense.managers.services.syslog_dest`
- CpZoneManager: captiveportal/settings, suffix=Zone (search: searchZones). Match: description. Module: `opnsense.managers.services.cp_zone`
- DdnsAccountManager: dyndns/accounts, suffix=Item. Match: description. Redact: password. Built-in 26.1 (not os-ddclient plugin). Module: `opnsense.managers.services.ddns_account`
- PluginManager: custom (not BaseManager). list_plugins(), list_installed(), is_installed(), install(), remove(). Module: `opnsense.managers.services.plugin`

## Use Cases

### CronJobManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create job (disabled) | description=inttest-cron, command=firmware auto-update, enabled=0 | created | |
| 02 | Idempotent noop | same | noop | |
| 03 | Update schedule | minutes=30, hours=4 | updated | drift |
| 04 | Delete | | deleted | |
| 05 | **Duplicate: same description** | description=inttest-cron (exists) | AmbiguousMatchError | duplicate guard |

### SyslogDestManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create dest | description=inttest-syslog, transport=udp4, hostname=10.11.1.99, port=514 | created | |
| 02 | Delete | | deleted | |
| 03 | **Port: boundary min** | port=1 | created | min port |
| 04 | **Port: boundary max** | port=65535 | created | max port |
| 05 | **Error: port > 65535** | port=125657 | FieldValidationError | above range |
| 06 | **Error: port 0** | port=0 | FieldValidationError | below range |

### CpZoneManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create zone | description=inttest-portal | created | guest networks |
| 02 | Delete | | deleted | |

### DdnsAccountManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create account (disabled) | description=inttest-ddns, service=cloudflare, username=inttest@example.com, hostnames=inttest.example.com, checkip=web_cloudflare, enabled=0 | created | |
| 02 | Idempotent noop | same | noop | |
| 03 | Delete | | deleted | |

### PluginManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | List installed | list_installed() | list of plugins | |
| 02 | Check installed | is_installed("os-ddclient") | bool | |
| 03 | List all plugins | list_plugins() | full catalog | |

## Bill of Materials
- OPNsense test device
- os-ddclient plugin installed (for plugin manager tests)
- configctl webgui restart via SSH needed after plugin install
- No LXC required

## Safety Boundaries
- inttest- prefix on all objects
- Cron jobs always disabled (enabled=0)
- DynDNS accounts always disabled
- example.com domain only for DynDNS
- Never install/remove production plugins
- Captive portal zones: test only, no interface binding

## Logging

Logger path follows package structure for Loki/Promtail filtering:
```
opnsense.managers.services.cron_job      → CronJobManager
opnsense.managers.services.syslog_dest   → SyslogDestManager
opnsense.managers.services.cp_zone       → CpZoneManager
opnsense.managers.services.ddns_account  → DdnsAccountManager
opnsense.managers.services.plugin        → PluginManager
```

Filter in Loki: `{job="opnsense"} |= "opnsense.managers.services"`

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All 5 managers |
| Integration tests | PASS | Full lifecycle |
