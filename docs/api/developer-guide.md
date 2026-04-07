<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->
# OPNsense API Developer Guide

> **Purpose:** The single source of truth for building automation against
> OPNsense **26.1+** (minimum supported version). This doc teaches any agent
> or developer how to CRUD any OPNsense resource via REST API.
>
> **Read this before writing any Ansible module, script, or integration.**

---

## 1. API fundamentals

### Base URL and auth

```
https://<host>/api/<module>/<controller>/<command>/[<param1>/...]
```

Auth: HTTP Basic with API key (username) + API secret (password).

```bash
curl -sk -u "$KEY:$SECRET" https://opnsense.example.com/api/core/system/status
```

### Request/response

- `GET` = read-only (schema, search, status)
- `POST` = mutate (create, update, delete, apply)
- Body: JSON for POST
- Response: always JSON

---

## 2. The universal CRUD pattern

**Every MVC controller follows the same 7-step lifecycle.**
Only the module/controller/entity names and the payload key change.

| Step | Method | Pattern | Purpose |
|------|--------|---------|---------|
| **Schema** | GET | `/api/{mod}/{ctrl}/get_{entity}` | Empty schema: all fields, enums, defaults |
| **Search** | POST | `/api/{mod}/{ctrl}/search_{entity}` | List existing items (paginated) |
| **Read** | GET | `/api/{mod}/{ctrl}/get_{entity}/{uuid}` | Get one item by UUID |
| **Create** | POST | `/api/{mod}/{ctrl}/add_{entity}` | Create new item, returns UUID |
| **Update** | POST | `/api/{mod}/{ctrl}/set_{entity}/{uuid}` | Update existing item |
| **Delete** | POST | `/api/{mod}/{ctrl}/del_{entity}/{uuid}` | Delete item |
| **Apply** | POST | `/api/{mod}/{ctrl}/reconfigure` | Commit staged changes to running config |

Some controllers also have:

| Step | Method | Pattern | Purpose |
|------|--------|---------|---------|
| **Toggle** | POST | `/api/{mod}/{ctrl}/toggle_{entity}/{uuid}` | Enable/disable |
| **Reorder** | POST | `/api/{mod}/{ctrl}/move_rule_before/{sel}/{tgt}` | Change rule order |

### The apply rule

**Changes are staged until `reconfigure` / `apply` is called.**
Creating, updating, or deleting does NOT affect the running firewall
until you POST to `reconfigure` (or `apply` for filter rules).

---

## 3. Type conventions

The API uses these types. An Ansible module MUST handle the read/write asymmetry.

| Type | Read shape (GET) | Write shape (POST) | Example fields |
|------|-----------------|-------------------|----------------|
| `string-bool` | `"1"` / `"0"` | `"1"` / `"0"` | `enabled`, `log`, `quick` |
| `int-like string` | `"443"` | `"443"` | `port`, `sequence`, `mtu` |
| `enum dict` | `{"wan":{"value":"WAN","selected":1},...}` | `"wan"` (key only) | `interface`, `action`, `protocol` |
| `string` | `"text"` | `"text"` | `description`, `name` |
| `list` | `["uuid1","uuid2"]` | `"uuid1,uuid2"` | `categories`, `peers` |
| `csv content` | `"10.0.0.0/8\n172.16.0.0/12"` | newline-separated | `content` (aliases) |

### Enum dict read vs write

When you **read** an interface field:
```json
{
  "wan": {"value": "WAN", "selected": 1},
  "lan": {"value": "LAN", "selected": 0}
}
```

When you **write** it:
```json
{"interface": "wan"}
```

### Payload top-level key

The POST body wraps fields in a top-level key that **varies per controller**:

| Controller | Payload key |
|-----------|-------------|
| firewall/alias | `alias` |
| firewall/filter | `rule` |
| firewall/source_nat | `rule` |
| wireguard/server | `server` |
| wireguard/client | `client` |
| kea/dhcpv4 subnet | `subnet4` |
| unbound forwarder | `dot` |
| unbound host override | `host` |
| routes | `route` |
| routing gateway | `gateway` |
| auth/user | `user` |
| auth/group | `group` |
| syslog destination | `destination` |
| cron job | `job` |
| monit alert | `alert` |
| trust/ca | `ca` |
| trust/cert | `cert` |

**To discover the key:** GET the empty schema endpoint and look at the top-level key in the response.

---

## 4. Worked example: full CRUD lifecycle

This is exactly how I fixed DNS on this box. Same pattern works for every entity.

### 4.1 Discover the schema

```bash
curl -sk -u "$KEY:$SECRET" \
  https://opn/api/unbound/settings/get_forward | jq '.'
```

Response reveals:
- Payload key: `dot`
- Fields: `enabled`, `type`, `domain`, `server`, `port`, `verify`, `forward_tcp_upstream`, `description`
- `type` is an enum: `dot` (DNS-over-TLS), `forward` (plain)

### 4.2 Search existing items

```bash
curl -sk -X POST -u "$KEY:$SECRET" \
  -H 'Content-Type: application/json' \
  -d '{"current":1,"rowCount":50,"searchPhrase":""}' \
  https://opn/api/unbound/settings/search_forward | jq '.rows'
```

Response: `[]` (no forwarders exist)

### 4.3 Create

```bash
curl -sk -X POST -u "$KEY:$SECRET" \
  -H 'Content-Type: application/json' \
  -d '{
    "dot": {
      "enabled": "1",
      "type": "forward",
      "domain": "",
      "server": "198.51.100.1",
      "port": "",
      "verify": "",
      "forward_tcp_upstream": "0",
      "description": "pfSense upstream DNS"
    }
  }' \
  https://opn/api/unbound/settings/add_forward
```

Response: `{"uuid": "913998c4-...", "result": "saved"}`

### 4.4 Apply

```bash
curl -sk -X POST -u "$KEY:$SECRET" \
  https://opn/api/unbound/service/reconfigure
```

Response: `{"status": "ok"}`

### 4.5 Verify

```bash
curl -sk -X POST -u "$KEY:$SECRET" \
  -d '{"current":1,"rowCount":50,"searchPhrase":""}' \
  -H 'Content-Type: application/json' \
  https://opn/api/unbound/settings/search_forward | jq '.rows'
```

### 4.6 Update (change server)

```bash
curl -sk -X POST -u "$KEY:$SECRET" \
  -H 'Content-Type: application/json' \
  -d '{
    "dot": {
      "enabled": "1",
      "type": "forward",
      "server": "1.1.1.1",
      "description": "Cloudflare"
    }
  }' \
  https://opn/api/unbound/settings/set_forward/913998c4-...
```

### 4.7 Delete

```bash
curl -sk -X POST -u "$KEY:$SECRET" \
  https://opn/api/unbound/settings/del_forward/913998c4-...
```

### 4.8 Apply again

```bash
curl -sk -X POST -u "$KEY:$SECRET" \
  https://opn/api/unbound/service/reconfigure
```

---

## 5. Controller reference table

Every confirmed controller with its entity name, payload key, and apply endpoint.

### Firewall

| Controller | Entity | Payload key | Apply endpoint |
|-----------|--------|-------------|----------------|
| `firewall/alias` | `item` | `alias` | `firewall/alias/reconfigure` |
| `firewall/filter` | `rule` | `rule` | `firewall/filter/apply` |
| `firewall/source_nat` | `rule` | `rule` | `firewall/source_nat/apply` |
| `firewall/one_to_one` | `rule` | `rule` | `firewall/one_to_one/apply` |
| `firewall/npt` | `rule` | `rule` | `firewall/npt/apply` |
| `firewall/category` | `item` | `category` | `firewall/category/reconfigure` |
| `firewall/group` | `item` | `group` | `firewall/group/reconfigure` |

### Interfaces

| Controller | Entity | Payload key | Apply endpoint |
|-----------|--------|-------------|----------------|
| `interfaces/vlan_settings` | `item` | `vlan` | `interfaces/vlan_settings/reconfigure` |
| `interfaces/bridge_settings` | `item` | `bridge` | `interfaces/bridge_settings/reconfigure` |
| `interfaces/vip_settings` | `item` | `vip` | `interfaces/vip_settings/reconfigure` |
| `interfaces/loopback_settings` | `item` | `loopback` | `interfaces/loopback_settings/reconfigure` |
| `interfaces/lagg_settings` | `item` | `lagg` | `interfaces/lagg_settings/reconfigure` |
| `interfaces/gre_settings` | `item` | `gre` | `interfaces/gre_settings/reconfigure` |
| `interfaces/gif_settings` | `item` | `gif` | `interfaces/gif_settings/reconfigure` |
| `interfaces/vxlan_settings` | `item` | `vxlan` | `interfaces/vxlan_settings/reconfigure` |
| `interfaces/neighbor_settings` | `item` | `neighbor` | `interfaces/neighbor_settings/reconfigure` |

### Network services

| Controller | Entity | Payload key | Apply endpoint |
|-----------|--------|-------------|----------------|
| `routes/routes` | `route` | `route` | `routes/routes/reconfigure` |
| `routing/settings` | `gateway` | `gateway` | `routing/settings/reconfigure` |
| `unbound/settings` | `forward` | `dot` | `unbound/service/reconfigure` |
| `unbound/settings` | `host_override` | `host` | `unbound/service/reconfigure` |
| `unbound/settings` | `host_alias` | `host_alias` | `unbound/service/reconfigure` |
| `unbound/settings` | `acl` | `acl` | `unbound/service/reconfigure` |
| `unbound/settings` | `dnsbl` | `dnsbl` | `unbound/service/reconfigure` |
| `kea/dhcpv4` | `subnet` | `subnet4` | `kea/service/reconfigure` |
| `kea/dhcpv4` | `reservation` | `reservation` | `kea/service/reconfigure` |
| `kea/dhcpv4` | `peer` | `peer` | `kea/service/reconfigure` |
| `dhcrelay/settings` | `dest` | `destination` | `dhcrelay/service/reconfigure` |
| `dhcrelay/settings` | `relay` | `relay` | `dhcrelay/service/reconfigure` |
| `dnsmasq/settings` | `host` | `host` | `dnsmasq/service/reconfigure` |
| `dnsmasq/settings` | `domain` | `domain` | `dnsmasq/service/reconfigure` |
| `dnsmasq/settings` | `range` | `range` | `dnsmasq/service/reconfigure` |

### VPN

| Controller | Entity | Payload key | Apply endpoint |
|-----------|--------|-------------|----------------|
| `wireguard/server` | `server` | `server` | `wireguard/service/reconfigure` |
| `wireguard/client` | `client` | `client` | `wireguard/service/reconfigure` |
| `openvpn/instances` | (instance) | `instance` | `openvpn/service/reconfigure` |
| `openvpn/client_overwrites` | (cso) | `cso` | `openvpn/service/reconfigure` |
| `ipsec/connections` | `connection` | `connection` | `ipsec/service/reconfigure` |
| `ipsec/connections` | `child` | `child` | `ipsec/service/reconfigure` |
| `ipsec/connections` | `local` | `local` | `ipsec/service/reconfigure` |
| `ipsec/connections` | `remote` | `remote` | `ipsec/service/reconfigure` |
| `ipsec/key_pairs` | `item` | `key_pair` | `ipsec/service/reconfigure` |
| `ipsec/pre_shared_keys` | `item` | `pre_shared_key` | `ipsec/service/reconfigure` |
| `ipsec/pools` | (pool) | `pool` | `ipsec/service/reconfigure` |
| `ipsec/vti` | (vti) | `vti` | `ipsec/service/reconfigure` |

### Security / Monitoring

| Controller | Entity | Payload key | Apply endpoint |
|-----------|--------|-------------|----------------|
| `ids/settings` | `policy` | `policy` | `ids/service/reconfigure` |
| `ids/settings` | `user_rule` | `rule` | `ids/service/reconfigure` |
| `trafficshaper/settings` | `pipe` | `pipe` | `trafficshaper/service/reconfigure` |
| `trafficshaper/settings` | `queue` | `queue` | `trafficshaper/service/reconfigure` |
| `trafficshaper/settings` | `rule` | `rule` | `trafficshaper/service/reconfigure` |
| `monit/settings` | `alert` | `alert` | `monit/service/reconfigure` |
| `monit/settings` | `service` | `service` | `monit/service/reconfigure` |
| `monit/settings` | `test` | `test` | `monit/service/reconfigure` |

### System

| Controller | Entity | Payload key | Apply endpoint |
|-----------|--------|-------------|----------------|
| `auth/user` | (user) | `user` | N/A (immediate) |
| `auth/group` | (group) | `group` | N/A (immediate) |
| `syslog/settings` | `destination` | `destination` | `syslog/service/reconfigure` |
| `cron/settings` | `job` | `job` | `cron/service/reconfigure` |
| `core/tunables` | `item` | `tunable` | `core/tunables/reconfigure` |
| `trust/ca` | (ca) | `ca` | `trust/settings/reconfigure` |
| `trust/cert` | (cert) | `cert` | `trust/settings/reconfigure` |
| `captiveportal/settings` | `zone` | `zone` | `captiveportal/service/reconfigure` |

---

## 6. ensure() contract (ADR-0029)

Every manager MUST implement this contract. Uses `async/await` (ADR-0029).

```python
@dataclass(frozen=True)
class EnsureResult:
    changed: bool
    action: str          # 'created' | 'updated' | 'deleted' | 'noop'
    uuid: str | None
    before: dict | None
    after: dict | None

async def ensure(self, state: str, params: dict, check_mode: bool = False) -> EnsureResult:
    """
    state: 'present' | 'absent'
    params: dict of desired field values
    check_mode: True = dry-run, no mutation
    """
    
    # 1. SEARCH — find existing item by match key
    existing = await self._client.search(self._endpoint, match_key=params.get('name'))
    
    # 2. STATE = ABSENT
    if state == 'absent':
        if not existing:
            return EnsureResult(changed=False, action='noop', uuid=None, before=None, after=None)
        if check_mode:
            return EnsureResult(changed=True, action='deleted', uuid=existing['uuid'],
                                before=existing, after=None)
        await self._client.delete(self._endpoint, existing['uuid'])
        await self._client.reconfigure(self._apply_endpoint)
        return EnsureResult(changed=True, action='deleted', uuid=existing['uuid'],
                            before=existing, after=None)
    
    # 3. STATE = PRESENT, item missing -> CREATE
    if not existing:
        if check_mode:
            return EnsureResult(changed=True, action='created', uuid=None,
                                before=None, after=params)
        uuid = await self._client.create(self._endpoint, self._payload_key, params)
        await self._client.reconfigure(self._apply_endpoint)
        return EnsureResult(changed=True, action='created', uuid=uuid,
                            before=None, after=params)
    
    # 4. STATE = PRESENT, item exists -> COMPARE + UPDATE if different
    current = await self._client.get(self._endpoint, existing['uuid'])
    diff = self._compute_diff(current, params)
    
    if not diff:
        return EnsureResult(changed=False, action='noop', uuid=existing['uuid'],
                            before=current, after=current)
    
    if check_mode:
        return EnsureResult(changed=True, action='updated', uuid=existing['uuid'],
                            before=current, after=params)
    
    await self._client.update(self._endpoint, existing['uuid'], self._payload_key, params)
    await self._client.reconfigure(self._apply_endpoint)
    return EnsureResult(changed=True, action='updated', uuid=existing['uuid'],
                        before=current, after=params)
```

### Match keys per entity type

| Entity | Match key | Notes |
|--------|-----------|-------|
| Alias | `name` | Alias names are unique |
| Filter rule | `description` | Weak — OPNsense allows duplicates |
| NAT rule | `description` | Same weakness |
| VLAN | `tag` + `if` | VLAN ID + parent interface |
| Route | `network` + `gateway` | Destination + next-hop |
| Gateway | `name` | Gateway names are unique |
| DNS forwarder | `server` + `domain` | Server IP + scope |
| Host override | `hostname` + `domain` | FQDN |
| DHCP subnet | `subnet` | CIDR |
| DHCP reservation | `ip_address` | Reserved IP |
| WireGuard server | `name` | Instance name |
| WireGuard peer | `name` | Peer name |
| User | `name` | Username |
| Group | `name` | Group name |
| Syslog destination | `description` | Or transport + hostname |
| Cron job | `description` | Or command + schedule |
| Certificate | `descr` | Or CN |

---

## 7. Known gaps on OPNsense 26.1+

Features that gained MVC API in 26.1 (no longer gaps):

| Feature | 25.1 status | 26.1+ status |
|---------|-------------|--------------|
| DNAT / Port Forward | Legacy PHP, no API | **API OK** — `fw-dnat-rule` |
| Source NAT | Legacy PHP, no API | **API OK** — `fw-snat-rule` |
| 1:1 NAT | Legacy PHP, no API | **API OK** — `fw-1to1-rule` |
| NPT (IPv6) | Legacy PHP, no API | **API OK** — `fw-npt-rule` |
| Filter rules | Legacy PHP, no API | **API OK** — `fw-filter-rule` |
| DHCP (ISC) | Legacy ISC, XML-only | **Replaced by Kea** — `kea4-*`, `kea6-*` |
| NTP | XML-only | **Replaced by Chrony** — plugin API available |

These features still have **no REST API** on 26.1 (XML-only):

| Feature | Why | Workaround |
|---------|-----|------------|
| Interface assignment | Legacy PHP, not migrated | conf.iso seed or SSH + config.xml |
| Interface IP config | Legacy PHP | conf.iso seed or SSH + config.xml |
| PPPoE / PPTP | Legacy PHP | conf.iso seed or SSH + config.xml |
| System general (hostname, domain, DNS, timezone) | Legacy PHP | conf.iso seed or SSH + config.xml |
| System administration (SSH, WebGUI port/cert) | Legacy PHP | conf.iso seed or SSH + config.xml |

See [gaps.md](gaps.md) for the full gap registry with priorities.

---

## 8. Service lifecycle

Every service follows this pattern:

```bash
GET  /api/{mod}/service/status       # Check running state
POST /api/{mod}/service/start        # Start
POST /api/{mod}/service/stop         # Stop
POST /api/{mod}/service/restart      # Restart
POST /api/{mod}/service/reconfigure  # Apply config changes
```

Available services: unbound, kea, wireguard, openvpn, ipsec, ids, syslog,
cron, monit, trafficshaper, dhcrelay, dnsmasq, captiveportal.

---

## 9. Diagnostics (read-only)

| Endpoint | What it returns |
|----------|----------------|
| `/api/diagnostics/system/system_information` | Hostname, version, platform |
| `/api/diagnostics/system/system_resources` | Memory, CPU |
| `/api/diagnostics/system/system_time` | Uptime, load, time |
| `/api/diagnostics/system/system_temperature` | Thermal sensors |
| `/api/diagnostics/system/system_disk` | Disk usage |
| `/api/diagnostics/interface/get_arp` | ARP table |
| `/api/diagnostics/interface/get_routes` | Routing table |
| `/api/diagnostics/interface/get_interface_config` | Interface state |
| `/api/diagnostics/interface/get_interface_names` | Interface assignments |
| `/api/diagnostics/firewall/stats` | Firewall counters |
| `/api/diagnostics/firewall/list_rule_ids` | Active rule IDs |
| `/api/core/firmware/info` | Version, packages, plugins |
| `/api/core/service/search` | All running services |

---

## 10. Async operations (ADR-0029)

Some operations take time (firmware update, plugin install, IDS rule download).
OPNsense returns a job UUID; the lib uses `async/await` to wait without blocking.

**No polling loops. No threading. No infinite loops.**

### Long-running endpoints

| Endpoint | What it does | Check via |
|----------|-------------|-----------|
| `core/firmware/install/{pkg}` | Install plugin | `core/firmware/running` |
| `core/firmware/update` | Update firmware | `core/firmware/running` |
| `core/firmware/check` | Check for updates | `core/firmware/running` |
| `core/firmware/connection` | Test repo connectivity | `core/firmware/upgradestatus` |
| `ids/service/update_rules` | Download IDS rulesets | `ids/service/status` |

### Python implementation (async/await)

```python
async def wait_for_ready(self, check_endpoint: str, timeout: float | None = None,
                         interval: float = 3.0) -> dict:
    """Wait for a long-running operation to complete.
    
    Uses asyncio.wait_for() — hard deadline, raises TimeoutError.
    Uses asyncio.sleep() — non-blocking, frees event loop.
    No infinite loop possible.
    """
    timeout = timeout or self._async_timeout  # injected via constructor

    async def _wait():
        while True:
            status = await self.get(check_endpoint)
            if status.get('status') in ('ready', 'done'):
                return status
            await asyncio.sleep(interval)  # non-blocking

    return await asyncio.wait_for(_wait(), timeout=timeout)
```

### Parallel operations (like Promise.all)

```python
async def provision_full(client: OpnsenseClient):
    fw_mgr = FwAliasManager(client)
    user_mgr = AuthUserManager(client)
    dns_mgr = UbForwardManager(client)

    # All three run concurrently — single thread, event loop
    alias_result, user_result, dns_result = await asyncio.gather(
        fw_mgr.ensure("alias_net_mgmt", state="present", type="network", content="10.0.1.0/24"),
        user_mgr.ensure("svc-monitoring", state="present", email="mon@example.com"),
        dns_mgr.ensure(server="198.51.100.1", state="present", description="pfSense upstream"),
    )
    # Total time = max(individual times), not sum
```

### Timeout and cleanup guarantees

| Concern | Mechanism |
|---------|-----------|
| Hard deadline | `asyncio.wait_for(coro, timeout=N)` — raises `asyncio.TimeoutError` |
| No infinite loop | `timeout` parameter enforces deadline on every wait |
| No memory leak | `async with httpx.AsyncClient()` — context manager closes connections |
| No blocking sleep | `await asyncio.sleep()` — yields to event loop |
| Configurable | `timeout`, `async_timeout`, `max_retries`, `retry_backoff` — all via constructor (DI) |

---

## 11. Error handling

### HTTP status codes

| Code | Meaning | Action |
|------|---------|--------|
| `200` | Success | Parse JSON response |
| `400` | Validation error | Check `validations` dict in response |
| `401` | Auth failed | Check API key/secret |
| `403` | Forbidden | API user lacks privilege for this endpoint |
| `404` | Endpoint not found | Controller not available (plugin missing or legacy PHP) |
| `500` | Server error | OPNsense internal bug — check PHP error log |

### Validation errors

On `400` or `result: "failed"`, the response contains field-level errors:

```json
{
  "result": "failed",
  "validations": {
    "rule.source_net": "A valid address or alias is required.",
    "rule.destination_port": "Port must be between 1 and 65535."
  }
}
```

### Ansible error contract

```python
def api_call(method, endpoint, data=None):
    """Wrapper with structured error handling."""
    resp = httpx.request(method, url, json=data, auth=(key, secret), verify=False)

    if resp.status_code == 401:
        raise AuthError("API key/secret invalid or expired")

    if resp.status_code == 403:
        raise PrivilegeError(f"API user lacks access to {endpoint}")

    if resp.status_code == 404:
        raise EndpointMissing(f"{endpoint} not available — plugin not installed or legacy PHP")

    body = resp.json()

    if body.get('result') == 'failed':
        raise ValidationError(body.get('validations', {}))

    if resp.status_code >= 500:
        raise ServerError(f"OPNsense internal error on {endpoint}")

    return body
```

### Retry policy (configurable via constructor — ADR-0029)

All retry values are **injected via `OpnsenseClient` constructor**, never hardcoded:

```python
client = OpnsenseClient(
    host="opnsense.example.com", key=KEY, secret=SECRET,
    timeout=30,           # per-request HTTP timeout
    async_timeout=300,    # max wait for long-running ops
    max_retries=3,        # retry count for transient errors
    retry_backoff=2.0,    # exponential backoff base (seconds)
)
```

| Scenario | Retry? | Default | Backoff |
|----------|--------|---------|---------|
| `401` / `403` | No | 0 | Fail immediately |
| `404` | No | 0 | Fail immediately |
| `500` | Yes | `max_retries` (3) | `retry_backoff` exponential (2s, 4s, 8s) |
| Network timeout | Yes | `max_retries` (3) | `retry_backoff` exponential |
| `reconfigure` busy | Yes | `max_retries` (3) | `retry_backoff` exponential |
| `asyncio.TimeoutError` | No | 0 | Hard deadline exceeded — fail |

---

## 12. Logging, observability, and secret redaction

### Log format for automation runs

```
[{timestamp}] [{level}] [{module}] {action} {entity} {uuid} — {result}
```

Example:
```
[2026-04-04T22:38:44Z] [INFO] [unbound_forward] CREATE dot 913998c4-... — changed
[2026-04-04T22:38:45Z] [INFO] [unbound_forward] APPLY reconfigure — ok
[2026-04-04T22:38:45Z] [WARN] [fw_dnat] SKIP — endpoint 404, legacy PHP
```

### Secret redaction rules

These fields MUST be redacted in any log, diff, or output:

| Field pattern | What it contains |
|--------------|-----------------|
| `privkey` | WireGuard private key |
| `psk` | WireGuard pre-shared key |
| `password` | Alias URL auth, user passwords |
| `secret` | API secret, IPsec PSK |
| `key` | API key, IPsec key material |
| `otp_seed` | OTP seed for 2FA |

Redaction format: `<REDACTED:{type}>` (see redaction standard).

```python
REDACT_FIELDS = {'privkey', 'psk', 'password', 'secret', 'key', 'otp_seed'}

def redact(data: dict) -> dict:
    """Deep-redact sensitive fields before logging."""
    result = {}
    for k, v in data.items():
        if k in REDACT_FIELDS:
            result[k] = f"<REDACTED:{k}>"
        elif isinstance(v, dict):
            result[k] = redact(v)
        else:
            result[k] = v
    return result
```

### Loki / Promtail integration

OPNsense syslog can forward to Loki via the syslog API:

```bash
# Check current syslog destinations
curl -sk -u "$KEY:$SECRET" \
  https://opn/api/syslog/settings/get | jq '.syslog'

# Add Loki/Promtail as syslog destination
curl -sk -X POST -u "$KEY:$SECRET" \
  -H 'Content-Type: application/json' \
  -d '{
    "destination": {
      "enabled": "1",
      "transport": "udp4",
      "hostname": "10.6.240.x",
      "port": "1514",
      "level": ["notice","warn","err","crit","alert","emerg"],
      "facility": [],
      "program": "",
      "description": "Loki via Promtail"
    }
  }' \
  https://opn/api/syslog/settings/add_destination

# Apply
curl -sk -X POST -u "$KEY:$SECRET" \
  https://opn/api/syslog/service/reconfigure
```

Syslog destination fields (from schema audit):

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | string-bool | `"1"` / `"0"` |
| `transport` | enum | `udp4`, `tcp4`, `udp6`, `tcp6`, `tls4`, `tls6` |
| `hostname` | string | Loki/Promtail host |
| `port` | int-like string | e.g. `"1514"` |
| `level` | list | severity filter |
| `facility` | list | facility filter (empty = all) |
| `program` | string | program filter |
| `certificate` | enum | TLS cert (for tls transport) |
| `rfc5424` | string-bool | RFC 5424 format |
| `description` | string | free text |

---

## 13. Prometheus and Grafana

### OPNsense does NOT provide a native Prometheus exporter

There is no `/metrics` endpoint. Two approaches:

### Approach A: Prometheus exporter (recommended)

Install the `os-node_exporter` plugin on OPNsense:

```bash
curl -sk -X POST -u "$KEY:$SECRET" \
  https://opn/api/core/firmware/install/os-node_exporter
# Wait for completion, then configure via:
# Services > Node Exporter > General
```

This exposes system metrics (CPU, memory, disk, network) at
`http://opnsense:9100/metrics` in standard Prometheus format.

For **firewall-specific metrics**, build a custom exporter that polls:

| Metric | API source | Prometheus metric name |
|--------|-----------|----------------------|
| Interface bytes in/out | `/api/diagnostics/interface/get_interface_statistics` | `opnsense_interface_bytes_total{direction,iface}` |
| Firewall states | `/api/diagnostics/firewall/stats` | `opnsense_pf_states_total` |
| Gateway RTT | `/api/routes/gateway/status` | `opnsense_gateway_rtt_ms{name}` |
| Gateway loss | `/api/routes/gateway/status` | `opnsense_gateway_loss_pct{name}` |
| CPU/Memory | `/api/diagnostics/system/system_resources` | `opnsense_memory_used_bytes` |
| Temperature | `/api/diagnostics/system/system_temperature` | `opnsense_temperature_celsius{sensor}` |
| Disk usage | `/api/diagnostics/system/system_disk` | `opnsense_disk_used_pct{mount}` |
| Service state | `/api/core/service/search` | `opnsense_service_running{name}` |
| Unbound queries | `/api/unbound/diagnostics/stats` | `opnsense_dns_queries_total` |
| ARP table size | `/api/diagnostics/interface/get_arp` | `opnsense_arp_entries` |

### Approach B: Syslog to Loki (see section 12)

Forward syslog to Promtail/Loki, query from Grafana.
Good for firewall logs, auth events, IDS alerts.

### Grafana dashboard strategy

| Dashboard | Data source | Content |
|-----------|-------------|---------|
| OPNsense System | Prometheus (node_exporter) | CPU, RAM, disk, NIC bandwidth |
| OPNsense Firewall | Prometheus (custom exporter) | States, gateway health, rule hits |
| OPNsense DNS | Prometheus (custom exporter) | Unbound query rate, cache hit ratio |
| OPNsense Logs | Loki (syslog) | Firewall block/pass logs, auth events |
| OPNsense IDS | Loki (syslog) + Prometheus | Alert rate, top signatures, blocked IPs |

---

## 14. Companion docs

| Doc | Purpose | Size |
|-----|---------|------|
| `api-route-catalog.md` | All 600+ routes with doc links | 88K |
| `api-schema-audit.md` | Live-probed field schemas: 192/205 endpoints, every enum, every default | 164K |
| `rest-api-reference.md` | Deep field notes for 9 core topics (manually verified) | 32K |

These three + this guide = complete specification for any Ansible module.

---

## 15. How this guide was built

### Why probing was the key

The official OPNsense docs list routes but do NOT document:
- field names
- field types (string-bool vs enum vs list)
- enum values
- default values
- read vs write shape differences
- payload top-level keys
- which controllers are actually present on a given version

**No Swagger/OpenAPI spec exists.** The upstream docs at
[docs.opnsense.org/development/api.html](https://docs.opnsense.org/development/api.html)
list endpoints per module, but each page only shows the route + method.
The actual data model is hidden inside the MVC XML model files in the
[OPNsense source](https://github.com/opnsense/core/tree/master/src/opnsense/mvc/app/models/OPNsense).

### What made this work

| Ingredient | What it provided |
|-----------|-----------------|
| **Upstream route docs** | The endpoint list (which controllers exist) |
| **Live API probing** | The actual data model (fields, enums, defaults, types) |
| **A test device** | The ability to verify every call, discover 404s, test CRUD |
| **Schema trick** | `GET /api/.../get_{entity}` without UUID = empty schema with all fields |
| **Search trick** | `POST /api/.../search_{entity}` = actual row shape + live data |

### Upstream references

| Resource | URL | What it provides |
|----------|-----|-----------------|
| Core API index | [docs.opnsense.org/development/api.html](https://docs.opnsense.org/development/api.html) | List of modules |
| Per-module routes | `docs.opnsense.org/development/api/core/{module}.html` | Endpoint + method per controller |
| MVC source models | [github.com/opnsense/core/.../models/OPNsense](https://github.com/opnsense/core/tree/master/src/opnsense/mvc/app/models/OPNsense) | XML model definitions (authoritative field source) |
| API usage guide | [docs.opnsense.org/development/api.html](https://docs.opnsense.org/development/api.html#introduction) | Auth method, URL pattern, conventions |
| Changelog | [docs.opnsense.org/releases.html](https://docs.opnsense.org/releases.html) | Which version added which MVC controller |
| Plugin list | [docs.opnsense.org/manual/how-tos/installplugin.html](https://docs.opnsense.org/manual/how-tos/installplugin.html) | Available plugin packages |

### Test device requirement

**You cannot build reliable OPNsense automation without a live test device.**

Reasons:
- No OpenAPI/Swagger spec exists
- Docs may list controllers that don't exist on your version (DNAT on 25.1)
- Payload keys are not documented (must GET empty schema to discover)
- Enum values vary per installation (interface names, gateway names, alias names)
- Some 200 responses have `"result": "failed"` with validation errors
- Version-specific behavior (see version-compatibility.md for cross-version matrix)

Minimum test setup:

| Component | Spec |
|-----------|------|
| VM | 2 vCPU, 2GB RAM, 20GB disk |
| OS | OPNsense 25.1.x (latest) |
| Interfaces | 2 NICs (WAN + LAN) |
| Network | WAN with internet access + DNS |
| API key | `System > Access > Users > [user] > API keys` |
| Access | HTTPS to WebGUI/API from automation host |

---

## 16. Probing scripts

To re-probe schemas after OPNsense upgrades:

```bash
cd tools/opnsense/scripts
./probe-api-schemas.sh            # hits 205 endpoints, writes JSON
# build-api-schema-audit.sh runs automatically
# git diff docs/api-schema-audit.md  # see what changed
```

Credentials: [config/api-env.sh](../../config/api-env.sh) (gitignored).

---

> **Version:** OPNsense 26.1+ (minimum supported)
> **Probed:** 2026-04-04 | 192/205 endpoints OK
> **Author:** Opus agent
