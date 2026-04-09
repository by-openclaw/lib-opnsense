<!-- Copyright BY-SYSTEMS SRL — SPDX-License-Identifier: MIT -->
<!-- https://github.com/BY-SYSTEMS/lib-opnsense -->

# Routing Scope — lib-opnsense

## Overview

2 managers: RtGatewayManager (read-only in tests), RtRouteManager.
Gateway is read-only tested because modifying gateways can break connectivity.
Routes use Null4 blackhole gateway for safe testing.

## Network Diagram

```
  Rune VM (10.100.0.101)
       │
  ┌────┴────────────────────────────┐
  │  OPNsense (10.6.239.114)       │
  │                                 │
  │  Default GW: WAN DHCP          │
  │  Null4: 127.0.0.1 (blackhole)  │
  │  Null6: ::1 (blackhole)        │
  │                                 │
  │  Static routes for test:        │
  │    10.99.0.0/24 → Null4         │
  │    (traffic dropped, safe)      │
  └─────────────────────────────────┘
```

## Managers

### RtGatewayManager (routing/gateway_settings)

- Endpoint: routing/gateway_settings (search: searchGateway)
- Match key: name
- Read-only tests — never modify default gateway
- Module: `opnsense.managers.routing.gateway`

### RtRouteManager (routing/route)

- Endpoint: routing/route, suffix: Route
- Match key: description
- Apply: routing/routes/reconfigure
- Module: `opnsense.managers.routing.route`

## Use Cases

### RtGatewayManager

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | List gateways | search_phrase="" | >= 1 gateway | search works |
| 02 | Null4 exists | search for Null4 | found, address=127.0.0.1 | blackhole available |

### RtRouteManager

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create route | description=inttest-route, network=10.99.0.0/24, gateway=Null4 | created | safe blackhole route |
| 02 | Idempotent noop | same | noop | diff engine |
| 03 | Delete + idempotent | | deleted then noop | |
| 04 | Error: invalid network | network=bogus | validation error | |
| 05 | **Duplicate: same route** | description=inttest-route (exists) | AmbiguousMatchError | duplicate guard |

## Bill of Materials

- OPNsense test device with Null4/Null6 blackhole gateways (built-in)
- No LXC required

## Safety Boundaries

- NEVER modify WAN_DHCP or default gateway
- Use Null4 (127.0.0.1) blackhole for all test routes
- Test network: 10.99.0.0/24 (unused, safe)
- Gateway manager: READ-ONLY tests only

## CRUD Verification

API CRUD must be confirmed on the device, not just by API response.

| After CRUD | Verify with | From | Expected |
|---|---|---|---|
| Create route | `ssh root@10.6.239.114 "netstat -rn \| grep 10.99.0"` | OPNsense SSH | route to Null4 visible |
| Delete route | same netstat | OPNsense SSH | route gone |
| List gateways | `ssh root@10.6.239.114 "netstat -rn \| grep default"` | OPNsense SSH | default gateway present |
| Blackhole test | `ssh root@10.6.239.114 "ping -c1 -W1 10.99.0.1"` | OPNsense SSH | 100% packet loss (blackhole) |

## Logging

Logger path follows package structure for Loki/Promtail filtering:
```
opnsense.managers.routing.gateway  → RtGatewayManager
opnsense.managers.routing.route    → RtRouteManager
```

Filter in Loki: `{job="opnsense"} |= "opnsense.managers.routing"`

## Test Status

| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | Both managers |
| Integration tests | PASS | Blackhole routes |
