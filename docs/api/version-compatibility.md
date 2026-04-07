<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->
# OPNsense API Version Compatibility Matrix

> **Purpose:** Track which API endpoints are available on which OPNsense version.
> Generated from cross-referencing probe results across 25.1.12, 25.7.11, and 26.1.5.
>
> **Minimum version for full API coverage: OPNsense >= 26.1**

## Summary

| Version | Date | Endpoints | OK | Failed | Delta |
|---------|------|-----------|----|--------|-------|
| 25.1.12 | 2026-04-04 | 205 | 192 | 13 | Baseline |
| 25.7.11 | 2026-04-05 | 205 | 198 | 7 | +6 (radvd, ntpd, hostdisc, cp-service) |
| 26.1.5 | 2026-04-05 | 200 | 200 | 0 | +6 (d_nat, if-settings, chrony, lldpd) |

## Endpoints Not Available Before 26.1

These endpoints return 404 on OPNsense < 26.1. Any lib-opnsense manager that
depends on these controllers **requires OPNsense >= 26.1**.

| Endpoint | Controller | Type | Reason | Impact |
|----------|-----------|------|--------|--------|
| `firewall/d_nat/get_rule` | D-NAT (Port Forward) | schema | MVC migration in 26.1 | **Cannot CRUD port forward rules** |
| `firewall/d_nat/search_rule` | D-NAT (Port Forward) | search | MVC migration in 26.1 | Cannot list port forward rules |
| `interfaces/settings/get` | Interface settings | global | MVC migration in 26.1 | Cannot read interface settings via API |
| `chrony/general/get` | Chrony NTP | global | Requires `os-chrony` plugin | No NTP config via API |
| `chrony/service/status` | Chrony NTP | global | Requires `os-chrony` plugin | No NTP status via API |
| `lldpd/general/get` | LLDP | global | Requires `os-lldpd` plugin | No LLDP config via API |
| `lldpd/service/status` | LLDP | global | Requires `os-lldpd` plugin | No LLDP status via API |

## Endpoints Not Available Before 25.7

These were added or fixed in the 25.7 cycle:

| Endpoint | Controller | Reason |
|----------|-----------|--------|
| `captiveportal/service/status` | Captive Portal | Service status endpoint added |
| `radvd/settings/*` | Router Advertisements | Moved from plugin to core |
| `ntpd/service/*` | NTPd | Service API added (later replaced by chrony) |
| `hostdiscovery/settings/*` | Host Discovery | Settings API added |

## Endpoints Removed / Replaced

| Endpoint | Removed in | Replacement |
|----------|-----------|-------------|
| `ntpd/*` | 26.1 | `chrony/*` (requires `os-chrony` plugin) |
| `radvd/*` | 26.1 | Moved to core router advertisement settings |
| `hostdiscovery/*` | 26.1 | No direct replacement |
| `firewall/filter_base/get` | N/A | Abstract base controller — not callable, inherited by filter/d_nat/source_nat/etc. |

## All Endpoints — Full Version Matrix

> 183 endpoints available since 25.1 (not listed — all return 200 across all versions).
> Only endpoints with version-specific behavior are shown below.

| Endpoint | 25.1.12 | 25.7.11 | 26.1.5 | Since |
|----------|---------|---------|--------|-------|
| `firewall/d_nat/get_rule` | 404 | 404 | 200 | 26.1 |
| `firewall/d_nat/search_rule` | 404 | 404 | 200 | 26.1 |
| `interfaces/settings/get` | 404 | 404 | 200 | 26.1 |
| `chrony/general/get` | — | — | 200 | 26.1 (plugin) |
| `chrony/service/status` | — | — | 200 | 26.1 (plugin) |
| `lldpd/general/get` | — | — | 200 | 26.1 (plugin) |
| `lldpd/service/status` | — | — | 200 | 26.1 (plugin) |
| `captiveportal/service/status` | 404 | 200 | 200 | 25.7 |
| `radvd/settings/get_entry` | 404 | 200 | — | 25.7 (removed in 26.1) |
| `radvd/settings/search_entry` | 404 | 200 | — | 25.7 (removed in 26.1) |
| `radvd/settings/get` | 404 | 200 | — | 25.7 (removed in 26.1) |
| `radvd/service/status` | 404 | 200 | — | 25.7 (removed in 26.1) |
| `ntpd/service/status` | 404 | 200 | — | 25.7 (removed in 26.1) |
| `ntpd/service/meta` | 404 | 200 | — | 25.7 (removed in 26.1) |
| `hostdiscovery/settings/get` | 404 | 200 | — | 25.7 (removed in 26.1) |
| `hostdiscovery/service/status` | 404 | 200 | — | 25.7 (removed in 26.1) |

---

> Generated: 2026-04-05 from probe data across 3 versions.
> Source: `lib-opnsense/docs/api/data/{25.1.12,25.7.11_9,26.1.5}/` (cross-repo)
