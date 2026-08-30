<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->

# API Match Key Reference — lib-opnsense

> **Purpose:** Document how each OPNsense API endpoint identifies resources,
> what fields are available for matching, and where the current `_match_key`
> implementation is insufficient. For team review.
>
> **Device:** OPNsense 26.1.5 at 10.6.239.114
> **Date:** 2026-04-07
>
> **Key finding:** OPNsense uses UUID internally for all CRUD. The pylib uses
> `_match_key` to search by a human-friendly field and extract the UUID.
> Some managers match on `description` which is **not enforced unique** by the API.

---

## Summary

| Manager | Current match key | Unique? | Proposed match keys | Risk |
|---|---|---|---|---|
| M01 — AuthUserManager | `name` | YES | `name` (unique, enforced by API) | none |
| M02 — AuthGroupManager | `name` | YES | `name` (unique, enforced by API) | none |
| M05 — FwAliasManager | `name` | YES | `name` (unique, enforced by API) | none |
| M06 — FwFilterManager | `description` | NO | `description` + `interface` + `direction` | **silent mismatch** |
| M07 — FwDnatManager | `descr` | NO | `descr` + `interface` + `target` | **silent mismatch** |
| M08 — FwSourceNatManager | `description` | NO | `description` + `interface` + `source_net` | **silent mismatch** |
| M11 — FwOneToOneManager | `description` | NO | `description` + `interface` + `source_net` | **silent mismatch** |
| M09 — FwCategoryManager | `name` | YES | `name` (unique, enforced by API) | none |
| M10 — FwGroupManager | `ifname` | YES | `ifname` (unique, enforced by API) | none |
| M12 — TsPipeManager | `description` | NO | `description` (practically unique) | **silent mismatch** |
| M13 — IfVlanManager | `descr` | YES | `tag` + `if` (enforced unique by API) | **silent mismatch** |
| M14 — IfVipManager | `descr` | NO | `address` + `interface` + `mode` | **silent mismatch** |

---

## M01 — AuthUserManager

**Current match key:** `name`
**Proposed match keys:** `name` (unique, enforced by API)
**Problem:** None — `name` is enforced unique by OPNsense.

### Create

```bash
curl -X POST https://10.6.239.114/api/auth/user/add \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"user": {"name": "inttest-apiref", "email": "ref@example.com", "password": "T3stP@ss!"}}'
```

**Response:** `{"uuid": "903c0abc-caa8-4bef-9ccf-5c999c7f31f7"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/auth/user/search \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "903c0abc-caa8-4bef-9ccf-5c999c7f31f7",
  "uid": "2001",
  "name": "inttest-apiref",
  "scope": "user",
  "password": "$2y$11$JqN/K.HVl5Y6RV4G1IJgpebtYyh4gtCHBaO/xWMQf62Yy3uxXW47i",
  "pwd_changed_at": "1775592945.5637",
  "email": "ref@example.com"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/auth/user/get/903c0abc-caa8-4bef-9ccf-5c999c7f31f7 \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "uid": "2001",
  "name": "inttest-apiref",
  "disabled": "0",
  "scope": "user",
  "expires": "",
  "authorizedkeys": "",
  "otp_seed": "",
  "shell": {
    "": {
      "value": "Default (none for all but root)",
      "selected": 1
    },
    "/bin/csh": {
      "value": "/bin/csh",
      "selected": 0
    },
    "/bin/sh": {
      "value": "/bin/sh",
      "selected": 0
    },
    "/bin/tcsh": {
      "value": "/bin/tcsh",
      "selected": 0
    }
  },
  "password": "",
  "scrambled_password": "0",
  "pwd_changed_at": "1775592945.5637",
  "landing_page": "",
  "comment": "",
  "email": "ref@example.com",
  "apikeys": ""
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/auth/user/del/903c0abc-caa8-4bef-9ccf-5c999c7f31f7 \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M02 — AuthGroupManager

**Current match key:** `name`
**Proposed match keys:** `name` (unique, enforced by API)
**Problem:** None — `name` is enforced unique by OPNsense.

### Create

```bash
curl -X POST https://10.6.239.114/api/auth/group/add \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"group": {"name": "inttest-apiref-grp", "description": "API ref"}}'
```

**Response:** `{"uuid": "70a27a08-aa6a-49b9-8add-3a10ac83705a"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/auth/group/search \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "70a27a08-aa6a-49b9-8add-3a10ac83705a",
  "gid": "2000",
  "name": "inttest-apiref-grp",
  "scope": "user",
  "description": "API ref"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/auth/group/get/70a27a08-aa6a-49b9-8add-3a10ac83705a \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "gid": "2000",
  "name": "inttest-apiref-grp",
  "scope": "user",
  "description": "API ref",
  "priv": {
    "page-all": {
      "value": "All pages",
      "selected": 0
    },
    "page-diagnostics-arptable": {
      "value": "Diagnostics: ARP Table",
      "selected": 0
    },
    "page-diagnostics-authentication": {
      "value": "Diagnostics: Authentication",
      "selected": 0
    },
    "...": "(148 options total)"
  },
  "member": {
    "0": {
      "value": "root",
      "selected": 0
    },
    "2000": {
      "value": "svc-rune",
      "selected": 0
    }
  },
  "source_networks": {
    "": {
      "value": "",
      "selected": 1
    }
  }
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/auth/group/del/70a27a08-aa6a-49b9-8add-3a10ac83705a \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M05 — FwAliasManager

**Current match key:** `name`
**Proposed match keys:** `name` (unique, enforced by API)
**Problem:** None — alias `name` is enforced unique by OPNsense.

### Create

```bash
curl -X POST https://10.6.239.114/api/firewall/alias/addItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"alias": {"name": "inttest_apiref", "type": "host", "content": "10.11.1.99", "description": "API ref"}}'
```

**Response:** `{"uuid": "510b2827-200e-4577-9c7a-417ee0fe93d7"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/firewall/alias/searchItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "65a14a6b-e2e7-410e-9c8e-34b394b99389",
  "enabled": "1",
  "name": "inttest_admin_hosts",
  "type": "host",
  "%type": "Host(s)",
  "content": "10.100.0.101\n10.6.239.113",
  "current_items": "2",
  "last_updated": "2026-04-07T17:35:43.737986",
  "eval_match": "2130",
  "in_pass_p": "15960",
  "in_pass_b": "2284472",
  "out_pass_p": "37902",
  "out_pass_b": "32286297",
  "description": "Rune VM + Win11 admin access",
  "categories_uuid": []
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/firewall/alias/getItem/510b2827-200e-4577-9c7a-417ee0fe93d7 \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "enabled": "1",
  "name": "inttest_apiref",
  "type": {
    "host": {
      "value": "Host(s)",
      "selected": 1
    },
    "network": {
      "value": "Network(s)",
      "selected": 0
    },
    "port": {
      "value": "Port(s)",
      "selected": 0
    },
    "...": "(14 options total)"
  },
  "path_expression": "",
  "proto": {
    "IPv4": {
      "value": "IPv4",
      "selected": 0
    },
    "IPv6": {
      "value": "IPv6",
      "selected": 0
    }
  },
  "interface": {
    "": {
      "value": "None",
      "selected": 1
    },
    "lan": {
      "value": "LAN",
      "selected": 0
    },
    "wan": {
      "value": "WAN",
      "selected": 0
    }
  },
  "counters": "0",
  "updatefreq": "",
  "content": {
    "10.11.1.99": {
      "value": "10.11.1.99",
      "selected": 1
    },
    "inttest_admin_hosts": {
      "selected": 0,
      "value": "inttest_admin_hosts",
      "description": "Rune VM + Win11 admin access"
    },
    "inttest_admin_ports": {
      "selected": 0,
      "value": "inttest_admin_ports",
      "description": "SSH + HTTPS admin ports"
    },
    "...": "(11 options total)"
  },
  "password": "",
  "username": "",
  "authtype": {
    "": {
      "value": "None",
      "selected": 1
    },
    "Basic": {
      "value": "Basic",
      "selected": 0
    },
    "Bearer": {
      "value": "Bearer",
      "selected": 0
    },
    "Header": {
      "value": "Header",
      "selected": 0
    }
  },
  "expire": "",
  "categories": [],
  "current_items": ""
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/firewall/alias/delItem/510b2827-200e-4577-9c7a-417ee0fe93d7 \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M06 — FwFilterManager

**Current match key:** `description`
**Proposed match keys:** `description` + `interface` + `direction`
**Problem:** **DUPLICATE ALLOWED.** OPNsense does NOT enforce unique description. Two rules with same description = `ensure()` matches first, ignores second silently.

### Create

```bash
curl -X POST https://10.6.239.114/api/firewall/filter/addRule \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"rule": {"description": "inttest-apiref-rule", "action": "pass", "interface": "lan", "direction": "in", "enabled": "0"}}'
```

**Response:** `{"uuid": "a1b8cc06-604c-4456-9f22-dfa6e2f6b40b"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/firewall/filter/searchRule \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "91021153-2d27-4a9a-9b9e-66dabc746fa8",
  "enabled": "1",
  "statetype": "keep",
  "%statetype": "keep state",
  "sequence": "100",
  "action": "pass",
  "%action": "Pass",
  "quick": "1",
  "interface": "wan",
  "%interface": "WAN",
  "direction": "in",
  "%direction": "In",
  "ipprotocol": "inet",
  "%ipprotocol": "IPv4",
  "protocol": "TCP",
  "source_net": "inttest_admin_hosts",
  "destination_net": "(self)",
  "%destination_net": "This Firewall",
  "destination_port": "inttest_admin_ports",
  "disablereplyto": "1",
  "description": "Allow admin SSH+HTTPS from Rune+Win11"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/firewall/filter/getRule/a1b8cc06-604c-4456-9f22-dfa6e2f6b40b \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "enabled": "0",
  "statetype": {
    "keep": {
      "value": "keep state",
      "selected": 1
    },
    "sloppy": {
      "value": "sloppy state",
      "selected": 0
    },
    "modulate": {
      "value": "modulate state",
      "selected": 0
    },
    "synproxy": {
      "value": "synproxy state",
      "selected": 0
    },
    "none": {
      "value": "no state",
      "selected": 0
    }
  },
  "state-policy": {
    "": {
      "value": "default",
      "selected": 1
    },
    "if-bound": {
      "value": "Bind states to interface",
      "selected": 0
    },
    "floating": {
      "value": "Floating states",
      "selected": 0
    }
  },
  "sequence": "200",
  "sort_order": "400000.0000200",
  "prio_group": "400000",
  "action": {
    "pass": {
      "value": "Pass",
      "selected": 1
    },
    "block": {
      "value": "Block",
      "selected": 0
    },
    "reject": {
      "value": "Reject",
      "selected": 0
    }
  },
  "quick": "1",
  "interfacenot": "0",
  "interface": {
    "lan": {
      "value": "LAN",
      "selected": 1
    },
    "wan": {
      "value": "WAN",
      "selected": 0
    }
  },
  "direction": {
    "in": {
      "value": "In",
      "selected": 1
    },
    "out": {
      "value": "Out",
      "selected": 0
    },
    "any": {
      "value": "Both",
      "selected": 0
    }
  },
  "ipprotocol": {
    "inet": {
      "value": "IPv4",
      "selected": 1
    },
    "inet6": {
      "value": "IPv6",
      "selected": 0
    },
    "inet46": {
      "value": "IPv4+IPv6",
      "selected": 0
    }
  },
  "protocol": {
    "any": {
      "value": "any",
      "selected": 1
    },
    "TCP": {
      "value": "TCP",
      "selected": 0
    },
    "UDP": {
      "value": "UDP",
      "selected": 0
    },
    "...": "(133 options total)"
  },
  "icmptype": {
    "echoreq": {
      "optgroup": "Common",
      "value": "Echo Request",
      "selected": 0
    },
    "echorep": {
      "optgroup": "Common",
      "value": "Echo Rep
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/firewall/filter/delRule/a1b8cc06-604c-4456-9f22-dfa6e2f6b40b \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M07 — FwDnatManager

**Current match key:** `descr`
**Proposed match keys:** `descr` + `interface` + `target`
**Problem:** **DUPLICATE ALLOWED.** Same as filter rules — description is not unique.

### Create

```bash
curl -X POST https://10.6.239.114/api/firewall/d_nat/addRule \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"rule": {"descr": "inttest-apiref-dnat", "interface": "wan", "target": "10.11.2.10", "local-port": "80", "disabled": "1"}}'
```

**Response:** `{"uuid": "None"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/firewall/d_nat/searchRule \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/firewall/d_nat/getRule/None \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/firewall/d_nat/delRule/None \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M08 — FwSourceNatManager

**Current match key:** `description`
**Proposed match keys:** `description` + `interface` + `source_net`
**Problem:** **DUPLICATE ALLOWED.** Same as filter rules.

### Create

```bash
curl -X POST https://10.6.239.114/api/firewall/source_nat/addRule \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"rule": {"description": "inttest-apiref-snat", "interface": "wan", "source_net": "10.11.3.0/24", "target": "wanip", "enabled": "0"}}'
```

**Response:** `{"uuid": "cd8bb727-a6ca-420a-9106-0723bdb67d7e"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/firewall/source_nat/searchRule \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "cd8bb727-a6ca-420a-9106-0723bdb67d7e",
  "sequence": "100",
  "interface": "wan",
  "%interface": "WAN",
  "ipprotocol": "inet",
  "%ipprotocol": "IPv4",
  "protocol": "any",
  "source_net": "10.11.3.0/24",
  "destination_net": "any",
  "target": "wanip",
  "%target": "WAN address",
  "description": "inttest-apiref-snat"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/firewall/source_nat/getRule/cd8bb727-a6ca-420a-9106-0723bdb67d7e \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "enabled": "0",
  "nonat": "0",
  "sequence": "100",
  "interface": {
    "lan": {
      "value": "LAN",
      "selected": 0
    },
    "wan": {
      "value": "WAN",
      "selected": 1
    }
  },
  "ipprotocol": {
    "inet": {
      "value": "IPv4",
      "selected": 1
    },
    "inet6": {
      "value": "IPv6",
      "selected": 0
    }
  },
  "protocol": {
    "any": {
      "value": "any",
      "selected": 1
    },
    "TCP": {
      "value": "TCP",
      "selected": 0
    },
    "UDP": {
      "value": "UDP",
      "selected": 0
    },
    "...": "(133 options total)"
  },
  "source_net": "10.11.3.0/24",
  "source_not": "0",
  "source_port": "",
  "destination_net": "any",
  "destination_not": "0",
  "destination_port": "",
  "target": "wanip",
  "target_port": "",
  "staticnatport": "0"
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/firewall/source_nat/delRule/cd8bb727-a6ca-420a-9106-0723bdb67d7e \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M11 — FwOneToOneManager

**Current match key:** `description`
**Proposed match keys:** `description` + `interface` + `source_net`
**Problem:** **DUPLICATE ALLOWED.** Same as filter rules.

### Create

```bash
curl -X POST https://10.6.239.114/api/firewall/one_to_one/addRule \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"rule": {"description": "inttest-apiref-1to1", "interface": "wan", "external": "10.11.1.200", "source_net": "10.11.2.10/32", "disabled": "1"}}'
```

**Response:** `{"uuid": "16c01ebc-26e6-49b5-82f9-fdc2de3671ad"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/firewall/one_to_one/searchRule \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "16c01ebc-26e6-49b5-82f9-fdc2de3671ad",
  "enabled": "1",
  "sequence": "100",
  "interface": "wan",
  "%interface": "WAN",
  "type": "binat",
  "%type": "BINAT",
  "source_net": "10.11.2.10/32",
  "destination_net": "any",
  "external": "10.11.1.200",
  "description": "inttest-apiref-1to1"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/firewall/one_to_one/getRule/16c01ebc-26e6-49b5-82f9-fdc2de3671ad \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "enabled": "1",
  "log": "0",
  "sequence": "100",
  "interface": {
    "lan": {
      "value": "LAN",
      "selected": 0
    },
    "wan": {
      "value": "WAN",
      "selected": 1
    }
  },
  "type": {
    "binat": {
      "value": "BINAT",
      "selected": 1
    },
    "nat": {
      "value": "NAT",
      "selected": 0
    }
  },
  "source_net": "10.11.2.10/32",
  "source_not": "0",
  "destination_net": "any",
  "destination_not": "0",
  "external": "10.11.1.200",
  "natreflection": {
    "": {
      "value": "Default",
      "selected": 1
    },
    "enable": {
      "value": "Enable",
      "selected": 0
    },
    "disable": {
      "value": "Disable",
      "selected": 0
    }
  },
  "categories": [],
  "description": "inttest-apiref-1to1"
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/firewall/one_to_one/delRule/16c01ebc-26e6-49b5-82f9-fdc2de3671ad \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M09 — FwCategoryManager

**Current match key:** `name`
**Proposed match keys:** `name` (unique, enforced by API)
**Problem:** None — category `name` is enforced unique.

### Create

```bash
curl -X POST https://10.6.239.114/api/firewall/category/addItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"category": {"name": "inttest-apiref-cat", "color": "ff0000"}}'
```

**Response:** `{"uuid": "b59af2f9-7ab1-4ab7-8eee-fad9a74753d6"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/firewall/category/searchItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "b59af2f9-7ab1-4ab7-8eee-fad9a74753d6",
  "name": "inttest-apiref-cat",
  "color": "ff0000"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/firewall/category/getItem/b59af2f9-7ab1-4ab7-8eee-fad9a74753d6 \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "name": "inttest-apiref-cat",
  "auto": "0",
  "color": "ff0000"
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/firewall/category/delItem/b59af2f9-7ab1-4ab7-8eee-fad9a74753d6 \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M10 — FwGroupManager

**Current match key:** `ifname`
**Proposed match keys:** `ifname` (unique, enforced by API)
**Problem:** None — `ifname` is enforced unique.

### Create

```bash
curl -X POST https://10.6.239.114/api/firewall/group/addItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"group": {"ifname": "inttest_apiref", "members": "lan", "descr": "API ref"}}'
```

**Response:** `{"uuid": "29a9a4e1-e066-48d2-8085-2b70bab68db4"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/firewall/group/searchItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "29a9a4e1-e066-48d2-8085-2b70bab68db4",
  "ifname": "inttest_apiref",
  "members": "lan",
  "%members": "LAN",
  "descr": "API ref"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/firewall/group/getItem/29a9a4e1-e066-48d2-8085-2b70bab68db4 \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "ifname": "inttest_apiref",
  "members": {
    "wan": {
      "value": "WAN",
      "selected": 0
    },
    "lan": {
      "value": "LAN",
      "selected": 1
    },
    "lo0": {
      "value": "Loopback",
      "selected": 0
    }
  },
  "nogroup": "0",
  "sequence": "0",
  "descr": "API ref"
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/firewall/group/delItem/29a9a4e1-e066-48d2-8085-2b70bab68db4 \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M12 — TsPipeManager

**Current match key:** `description`
**Proposed match keys:** `description` (practically unique)
**Problem:** Not enforced by API, but pipes are typically named uniquely.

### Create

```bash
curl -X POST https://10.6.239.114/api/trafficshaper/settings/addPipe \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"pipe": {"description": "inttest-apiref-pipe", "bandwidth": "10", "bandwidthMetric": "Mbit"}}'
```

**Response:** `{"uuid": "63c3cfb7-0cda-4832-ac42-b05ea8b6ef68"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/trafficshaper/settings/searchPipes \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "63c3cfb7-0cda-4832-ac42-b05ea8b6ef68",
  "number": "10000",
  "enabled": "1",
  "bandwidth": "10",
  "bandwidthMetric": "Mbit",
  "%bandwidthMetric": "Mbit/s",
  "mask": "none",
  "%mask": "(none)",
  "origin": "TrafficShaper",
  "description": "inttest-apiref-pipe"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/trafficshaper/settings/getPipe/63c3cfb7-0cda-4832-ac42-b05ea8b6ef68 \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "number": "10000",
  "enabled": "1",
  "bandwidth": "10",
  "bandwidthMetric": {
    "bit": {
      "value": "bit/s",
      "selected": 0
    },
    "Kbit": {
      "value": "kbit/s",
      "selected": 0
    },
    "Mbit": {
      "value": "Mbit/s",
      "selected": 1
    },
    "Gbit": {
      "value": "Gbit/s",
      "selected": 0
    }
  },
  "queue": "",
  "mask": {
    "none": {
      "value": "(none)",
      "selected": 1
    },
    "src-ip": {
      "value": "source",
      "selected": 0
    },
    "dst-ip": {
      "value": "destination",
      "selected": 0
    },
    "src-ip6": {
      "value": "source (ip6)",
      "selected": 0
    },
    "dst-ip6": {
      "value": "destination (ip6)",
      "selected": 0
    }
  },
  "buckets": "",
  "scheduler": {
    "": {
      "value": "Weighted Fair Queueing",
      "selected": 1
    },
    "fifo": {
      "value": "FIFO",
      "selected": 0
    },
    "rr": {
      "value": "Deficit Round Robin",
      "selected": 0
    },
    "...": "(6 options total)"
  },
  "codel_enable": "0",
  "codel_target": "",
  "codel_interval": "",
  "codel_ecn_enable": "0",
  "pie_enable": "0",
  "fqcodel_quantum": "",
  "fqcodel_limit": ""
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/trafficshaper/settings/delPipe/63c3cfb7-0cda-4832-ac42-b05ea8b6ef68 \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M13 — IfVlanManager

**Current match key:** `descr`
**Proposed match keys:** `tag` + `if` (enforced unique by API)
**Problem:** **WRONG MATCH KEY.** `descr` is a label, not the identity. `tag` + `if` is the real unique combo (API rejects duplicate tag on same parent). Current key prevents updating description and misidentifies VLANs.

### Create

```bash
curl -X POST https://10.6.239.114/api/interfaces/vlan_settings/addItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"vlan": {"if": "vtnet0", "tag": "1398", "descr": "inttest-apiref-vlan"}}'
```

**Response:** `{"uuid": "f94fce1a-fe31-4881-b501-245dac33e8f4"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/interfaces/vlan_settings/searchItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "f94fce1a-fe31-4881-b501-245dac33e8f4",
  "if": "vtnet0",
  "%if": "vtnet0 (bc:24:11:1d:b7:f4) [LAN]",
  "tag": "1398",
  "%pcp": "Best Effort (0, default)",
  "descr": "inttest-apiref-vlan",
  "vlanif": "vlan01"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/interfaces/vlan_settings/getItem/f94fce1a-fe31-4881-b501-245dac33e8f4 \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "if": {
    "vtnet0": {
      "value": "vtnet0 (bc:24:11:1d:b7:f4) [LAN]",
      "selected": 1
    },
    "vtnet1": {
      "value": "vtnet1 (bc:24:11:fa:2e:d1) [WAN]",
      "selected": 0
    },
    "vlan01": {
      "value": "vlan01 (Tag: 1398, Parent: vtnet0)",
      "selected": 0
    }
  },
  "tag": "1398",
  "pcp": {
    "1": {
      "value": "Background (1, lowest)",
      "selected": 0
    },
    "0": {
      "value": "Best Effort (0, default)",
      "selected": 1
    },
    "2": {
      "value": "Excellent Effort (2)",
      "selected": 0
    },
    "...": "(8 options total)"
  },
  "proto": {
    "": {
      "value": "Auto",
      "selected": 1
    },
    "802.1q": {
      "value": "802.1Q",
      "selected": 0
    },
    "802.1ad": {
      "value": "802.1ad",
      "selected": 0
    }
  },
  "descr": "inttest-apiref-vlan",
  "vlanif": "vlan01"
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/interfaces/vlan_settings/delItem/f94fce1a-fe31-4881-b501-245dac33e8f4 \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## M14 — IfVipManager

**Current match key:** `descr`
**Proposed match keys:** `address` + `interface` + `mode`
**Problem:** **WRONG MATCH KEY.** `descr` is a label. The real identity is the address+interface+mode combo. Current key prevents updating description.

### Create

```bash
curl -X POST https://10.6.239.114/api/interfaces/vip_settings/addItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"vip": {"interface": "lan", "mode": "ipalias", "address": "10.11.1.199/32", "network": "10.11.1.199/32", "descr": "inttest-apiref-vip"}}'
```

**Response:** `{"uuid": "c84d9470-e9fb-47f8-b3f2-3147989f8396"}`

### Search

```bash
curl -X POST https://10.6.239.114/api/interfaces/vip_settings/searchItem \
  -u '<API_KEY>:<API_SECRET>' -k \
  -H 'Content-Type: application/json' \
  -d '{"current": 1, "rowCount": 50, "searchPhrase": "inttest"}'
```

**Response row (flat strings — used by `_find_existing`):**

```json
{
  "uuid": "c84d9470-e9fb-47f8-b3f2-3147989f8396",
  "interface": "lan",
  "%interface": "LAN",
  "mode": "ipalias",
  "%mode": "IP Alias",
  "subnet": "10.11.1.199",
  "subnet_bits": "32",
  "advbase": "1",
  "address": "10.11.1.199/32",
  "descr": "inttest-apiref-vip"
}
```

### Get by UUID

```bash
curl -X GET https://10.6.239.114/api/interfaces/vip_settings/getItem/c84d9470-e9fb-47f8-b3f2-3147989f8396 \
  -u '<API_KEY>:<API_SECRET>' -k
```

**Response (enum dicts — used by `_compute_diff`):**

```json
{
  "interface": {
    "wan": {
      "value": "WAN",
      "selected": 0
    },
    "lan": {
      "value": "LAN",
      "selected": 1
    },
    "lo0": {
      "value": "Loopback",
      "selected": 0
    }
  },
  "mode": {
    "ipalias": {
      "value": "IP Alias",
      "selected": 1
    },
    "carp": {
      "value": "CARP",
      "selected": 0
    },
    "proxyarp": {
      "value": "Proxy ARP",
      "selected": 0
    }
  },
  "gateway": "",
  "noexpand": "0",
  "nobind": "0",
  "password": "",
  "vhid": "",
  "advbase": "1",
  "advskew": "0",
  "peer": "",
  "peer6": "",
  "nosync": "0",
  "address": "10.11.1.199/32",
  "vhid_txt": "",
  "descr": "inttest-apiref-vip"
}
```

### Delete

```bash
curl -X POST https://10.6.239.114/api/interfaces/vip_settings/delItem/c84d9470-e9fb-47f8-b3f2-3147989f8396 \
  -u '<API_KEY>:<API_SECRET>' -k
```

---

## Decision needed

### Option A: Composite match keys (`_match_keys: list[str]`)

Change `_match_key: str` to `_match_keys: list[str]` in BaseManager.
`_find_existing` matches ALL fields in the list. If one match = proceed.
If multiple matches = raise error. If zero = create.

**Pro:** Solves the duplicate description problem. VLANs match by tag+if (enforced unique).
**Con:** Breaking change for existing code. More fields to pass in `ensure()` params.

### Option B: Duplicate detection only

Keep `_match_key: str` but raise `ValueError` if `_find_existing` finds >1 match.
Caller must ensure descriptions are unique.

**Pro:** Minimal change. Fails loud instead of silent mismatch.
**Con:** Doesn't solve the VLAN/VIP wrong-key problem.

### Option C: Hybrid

- Managers with enforced unique keys (auth, alias, category, group): keep single `_match_key`
- Managers without (rules, VLAN, VIP): switch to `_match_keys: list[str]`
- BaseManager supports both: if `_match_keys` is set, use composite; else fall back to `_match_key`

**Pro:** Non-breaking for existing managers. Fixes only what's broken.
**Con:** Two patterns in one base class.
