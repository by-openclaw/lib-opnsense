<!--
Copyright BY-SYSTEMS SRL
SPDX-License-Identifier: MIT
https://github.com/by-systems/lib-opnsense
-->

# DNS Scope — lib-opnsense

## Overview
6 managers for Unbound DNS: UbHostOverrideManager, UbHostAliasManager, UbForwardManager, UbAclManager, UbDotManager, UbDiagnosticsManager (read-only).
All require unbound/service/reconfigure after CRUD (except diagnostics).
Host overrides support A, AAAA, MX, TXT record types.

## Network Diagram
```
  Rune VM (10.100.0.101)
       │
       │ DNS queries
       ▼
  ┌──────────────────────────────────┐
  │  OPNsense Unbound DNS           │
  │  Listening: all interfaces       │
  │                                  │
  │  Host overrides:                 │
  │    inttest.example.com → A/AAAA  │
  │    inttest-mx.example.com → MX   │
  │                                  │
  │  Forwarding: 1.1.1.1, 8.8.8.8  │
  │  DoT: upstream over TLS         │
  │  ACLs: allow/deny per subnet    │
  └──────────────────────────────────┘
```

## Managers

### UbHostOverrideManager (unbound/settings)
- Endpoint: unbound/settings, suffix: HostOverride
- Match key: hostname + domain (composite)
- Apply: unbound/service/reconfigure
- Types: A, AAAA, MX (with mxprio+mx), TXT (with txtdata)
- Module: `opnsense.managers.dns.ub_host_override`

### UbHostAliasManager (unbound/settings)
- Endpoint: unbound/settings, suffix: HostAlias
- Match key: host + domain (composite)
- Note: create + read only on 26.1.5 (update not reliable)
- Module: `opnsense.managers.dns.ub_host_alias`

### UbForwardManager (unbound/settings)
- Endpoint: unbound/settings, suffix: Forward (plural search: searchForwards)
- Match key: domain
- Module: `opnsense.managers.dns.ub_forward`

### UbAclManager (unbound/settings)
- Endpoint: unbound/settings, suffix: Acl (plural search: searchAcls)
- Match key: name
- Module: `opnsense.managers.dns.ub_acl`

### UbDotManager (unbound/settings)
- Endpoint: unbound/settings, suffix: Dot (plural search: searchDots)
- Match key: domain
- Module: `opnsense.managers.dns.ub_dot`

### UbDiagnosticsManager (unbound/diagnostics)
- Read-only: cache stats, top queries
- Module: `opnsense.managers.dns.ub_diagnostics`

## Use Cases

### UbHostOverrideManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create A record | hostname=inttest, domain=example.com, server=10.11.1.99, rr=A | created | A record |
| 02 | Create AAAA | rr=AAAA, server=fd11:1::99 | created | IPv6 |
| 03 | Create MX | rr=MX, mxprio=10, mx=mail.example.com | created | MX fields |
| 04 | Create TXT | rr=TXT, txtdata=v=spf1 | created | TXT field |
| 05 | Idempotent noop | same as 01 | noop | composite match |
| 06 | Delete all | | deleted | cleanup |
| 07 | Error: missing hostname | omit hostname | validation error | |
| 08 | **Duplicate: same hostname+domain** | hostname=inttest, domain=example.com (exists) | AmbiguousMatchError | composite key guard |

### UbHostAliasManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create alias | host=inttest-alias, domain=example.com | created | |
| 02 | Read back | list | found | create+read only |

### UbForwardManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create forward | domain=inttest.example.com, server=1.1.1.1 | created | |
| 02 | Delete | | deleted | |

### UbAclManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create ACL | name=inttest-acl | created | |
| 02 | Delete | | deleted | |

### UbDotManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create DoT | domain=inttest.example.com | created | |
| 02 | Delete | | deleted | |

### UbDiagnosticsManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Get cache stats | | dict with stats | read-only |

## Bill of Materials
- OPNsense with Unbound DNS enabled on all interfaces
- No LXC required for CRUD tests
- E2E DNS resolution test: needs LXC or Rune VM nslookup

## Safety Boundaries
- inttest prefix on all hostnames/domains
- example.com domain only
- NEVER modify production DNS forwarding
- Diagnostics: read-only, no mutations

## CRUD Verification

API CRUD must be confirmed on the device, not just by API response.

| After CRUD | Verify with | From | Expected |
|---|---|---|---|
| Create host override (A) | `dig inttest.example.com @10.6.239.114` | Rune VM | A record → 10.11.1.99 |
| Create host override (AAAA) | `dig AAAA inttest.example.com @10.6.239.114` | Rune VM | AAAA → fd11:1::99 |
| Create host override (MX) | `dig MX inttest-mx.example.com @10.6.239.114` | Rune VM | MX 10 mail.example.com |
| Create host override (TXT) | `dig TXT inttest-txt.example.com @10.6.239.114` | Rune VM | TXT "v=spf1..." |
| Delete host override | `dig inttest.example.com @10.6.239.114` | Rune VM | NXDOMAIN |
| Create forward | `dig external-domain.com @10.6.239.114` (if forward set) | Rune VM | resolved via forwarder |
| Reconfigure applied | `ssh root@10.6.239.114 "configctl unbound reconfigure"` | OPNsense SSH | Unbound reloaded |
| Cache stats | `ssh root@10.6.239.114 "unbound-control stats_noreset"` | OPNsense SSH | stats returned |

## Logging

Logger path follows package structure for Loki/Promtail filtering:
```
opnsense.managers.dns.ub_host_override  → UbHostOverrideManager
opnsense.managers.dns.ub_host_alias     → UbHostAliasManager
opnsense.managers.dns.ub_forward        → UbForwardManager
opnsense.managers.dns.ub_acl            → UbAclManager
opnsense.managers.dns.ub_dot            → UbDotManager
opnsense.managers.dns.ub_diagnostics    → UbDiagnosticsManager
```

Filter in Loki: `{job="opnsense"} |= "opnsense.managers.dns"`

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All 6 managers |
| Integration tests | PASS | Full lifecycle |
