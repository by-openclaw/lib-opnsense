<!--
  Copyright BY-SYSTEMS SRL
  SPDX-License-Identifier: MIT
  https://github.com/by-openclaw/lib-opnsense
-->

# Traffic Shaper Scope — lib-opnsense

## Overview
3 managers: TsPipeManager, TsQueueManager, TsRuleManager.
Queue needs parent pipe UUID. Rule needs target UUID (pipe or queue).
Plural search endpoints (searchPipes, searchQueues, searchRules).

## Network Diagram
```
  Traffic flow through OPNsense
  │
  ├── Pipe (bandwidth limit)
  │   ├── CoDel / PIE QoS algorithms
  │   └── Queue (weighted fair queueing)
  │       └── Rule (match traffic → queue)
  │
  Hierarchy: Pipe → Queue → Rule
  Rule needs target UUID pointing to pipe or queue
```

## Managers
- TsPipeManager: trafficshaper/settings, suffix=Pipe (search: searchPipes). Match: description. Module: `opnsense.managers.shaper.ts_pipe`
- TsQueueManager: trafficshaper/settings, suffix=Queue (search: searchQueues). Match: description. Needs pipe UUID. Module: `opnsense.managers.shaper.ts_queue`
- TsRuleManager: trafficshaper/settings, suffix=Rule (search: searchRules). Match: description. Needs target UUID. Module: `opnsense.managers.shaper.ts_rule`

## Use Cases

### TsPipeManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create pipe | description=inttest-pipe, bandwidth=10, bandwidthMetric=Mbit | created | CoDel/PIE |
| 02 | Idempotent + delete | | noop then deleted | |
| 03 | **Duplicate: same description** | description=inttest-pipe (exists) | AmbiguousMatchError | lib guard (API allows dupes) |

### TsQueueManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create queue | description=inttest-queue, pipe=<pipe-uuid>, weight=50 | created | needs parent |
| 02 | Delete | | deleted | |

### TsRuleManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create rule | description=inttest-rule, target=<pipe-uuid> | created | needs target |
| 02 | Delete | | deleted | |

## Bill of Materials
- OPNsense test device
- No LXC required for CRUD tests
- E2E bandwidth test: lxc-websrv-test-01 + iperf3

## Safety Boundaries
- inttest- prefix on all objects
- Create pipe first, then queue, then rule (dependency chain)
- Delete in reverse order: rule → queue → pipe

## Logging

Logger path follows package structure for Loki/Promtail filtering:
```
opnsense.managers.shaper.ts_pipe   → TsPipeManager
opnsense.managers.shaper.ts_queue  → TsQueueManager
opnsense.managers.shaper.ts_rule   → TsRuleManager
```

Filter in Loki: `{job="opnsense"} |= "opnsense.managers.shaper"`

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All 3 managers |
| Integration tests | PASS | Full chain |
