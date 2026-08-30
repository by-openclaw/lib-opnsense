# lib-opnsense

Async Python library for [OPNsense](https://opnsense.org/) REST API — CRUD + idempotent ensure() for auth, firewall, DNS, interfaces, and traffic shaping.

[![Version](https://img.shields.io/badge/version-1.3.0)](https://github.com/by-openclaw/lib-opnsense/releases) <!-- x-release-please-version -->
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/by-openclaw/lib-opnsense/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Internal use — BY-SYSTEMS DevOps platform.**
> See [LICENSE](LICENSE) for terms and disclaimer of liability.

---

## Install

```bash
# Install latest release (see https://github.com/by-openclaw/lib-opnsense/releases)
pip install git+https://github.com/by-openclaw/lib-opnsense.git@main
```

Development:

```bash
git clone https://github.com/by-openclaw/lib-opnsense.git
cd lib-opnsense
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Quick start

```python
import asyncio
from opnsense import OpnsenseClient
from opnsense.managers.firewall.filter import FwFilterManager
from opnsense.credentials import get_credentials

async def main():
    creds = get_credentials()  # reads OPN_HOST, OPN_KEY, OPN_SECRET from env/.env
    async with OpnsenseClient(
        host=creds.host,
        key=creds.key,
        secret=creds.secret,
        port=creds.port,
        verify_ssl=creds.verify_ssl,
    ) as client:
        fw = FwFilterManager(client)
        result = await fw.ensure(
            state="present",
            params={
                "description": "Allow HTTPS from DMZ",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "destination_port": "443",
                "enabled": "0",
            },
        )
        print(result)  # EnsureResult(changed=True, action='created', uuid='...')

asyncio.run(main())
```

---

## Architecture

```
src/opnsense/
├── core/                          # Cross-cutting concerns (zero coupling)
│   ├── identity.py                # IdentityResolver — composite match keys
│   ├── diff.py                    # DiffEngine — state comparison + enum normalization
│   ├── redaction.py               # Redactor — field redaction with partial reveal
│   ├── validation.py              # FieldValidator protocol + ValidatorRegistry
│   ├── endpoint.py                # EndpointConfig + EndpointResolver
│   └── logging_helpers.py         # ManagerLogBuilder — structured log construction
│
├── managers/
│   ├── base.py                    # BaseManager — thin orchestrator (composes core/)
│   ├── protocols.py               # ManagerProtocol (typing.Protocol for DI)
│   ├── auth/                      # user, group, priv, api_key
│   ├── firewall/                  # alias, filter, dnat, source_nat, one_to_one, npt, category, group
│   ├── interfaces/                # vlan, vip, bridge, gif, gre, lagg, loopback, neighbor, vxlan
│   ├── routing/                   # gateway, route
│   ├── dns/                       # ub_host_override, ub_host_alias, ub_forward, ub_acl, ub_dot, ub_diagnostics
│   ├── dhcp/                      # kea4_subnet, kea4_reservation, kea4_peer, kea6_subnet, kea6_reservation
│   ├── vpn/                       # wg_server, wg_client, ovpn_instance, ipsec_conn/child/local/remote/psk/keypair/pool/vti
│   ├── shaper/                    # ts_pipe, ts_queue, ts_rule
│   ├── trust/                     # ca, cert
│   └── services/                  # cron_job, syslog_dest, cp_zone, ddns_account, plugin
│
├── models/                        # Frozen dataclasses — mirrors managers/ structure
│   ├── base.py                    # EnsureResult
│   └── {scope}/                   # One model per entity (50 models)
│
├── client.py                      # httpx async transport (retry, exception mapping)
├── exceptions.py                  # Typed exception hierarchy (8 types)
├── credentials.py                 # EnvCredentialProvider + VaultCredentialProvider
└── logging.py                     # Structlog config (delegates to core/redaction)
```

---

## Managers (54 total)

| Scope | Managers | Status |
|-------|:-------:|--------|
| Auth (users, groups, privileges, API keys) | 4 | all integration tested |
| Firewall (aliases, filter, D-NAT, S-NAT, 1:1, NPTv6, categories, groups) | 8 | all integration tested |
| Interfaces (VLANs, VIPs, bridge, GIF, GRE, LAGG, loopback, neighbor, VXLAN) | 9 | all integration tested |
| Routing (gateways, static routes) | 2 | all integration tested |
| Traffic Shaper (pipes, queues, rules) | 3 | all integration tested |
| Unbound DNS (host overrides, aliases, forwarding, ACLs, DoT, diagnostics) | 6 | all integration tested |
| Kea DHCP (v4 subnets, reservations, peers + v6 subnets, reservations) | 5 | all integration tested |
| WireGuard (server + client/peer + key pair generation) | 2 | all integration tested |
| Trust/PKI (CA + certificates, import or generate) | 2 | all integration tested |
| OpenVPN (server/client instances, needs CA + cert) | 1 | integration tested |
| IPsec (connections, children, local/remote, PSK, keypairs, pools, VTI) | 8 | all integration tested |
| Captive Portal (guest network zones) | 1 | all integration tested |
| Syslog (remote destinations) | 1 | all integration tested |
| Cron (scheduled jobs) | 1 | all integration tested |
| DynDNS (Cloudflare, AWS, custom — A/AAAA updates) | 1 | integration tested |
| Plugin management (list, install, remove) | 1 | integration tested |

Full per-manager table with match keys, endpoints, and test status: [docs/api-coverage.md](docs/api-coverage.md)

### Duplicate detection

OPNsense API does **not** enforce uniqueness on FW rules, NAT rules, interfaces, or traffic shaper pipes. The lib uses composite match keys + `AmbiguousMatchError` to detect and prevent silent duplication. Auth users/groups are server-enforced unique.

---

## API reference

### OpnsenseClient

```python
class OpnsenseClient:
    def __init__(self, host, key, secret, port=443, verify_ssl=False,
                 timeout=30, async_timeout=300, max_retries=3, retry_backoff=2.0)

    # All methods accept optional timeout= and max_retries= per-call overrides
    async def get(endpoint, timeout=None, max_retries=None) -> dict
    async def post(endpoint, data=None, timeout=None, max_retries=None) -> dict
    async def search(endpoint, search_phrase="", timeout=None, max_retries=None) -> list[dict]
    async def create(endpoint, payload_key, params, timeout=None, max_retries=None) -> str
    async def update(endpoint, uuid, payload_key, params, timeout=None, max_retries=None) -> dict
    async def delete(endpoint, uuid, timeout=None, max_retries=None) -> dict
    async def reconfigure(endpoint, timeout=None, max_retries=None) -> dict
```

### BaseManager

```python
class BaseManager(ABC):
    async def list(search_phrase="") -> list[dict]
    async def get(uuid) -> dict
    async def get_schema() -> dict
    async def create(params, check_mode=False) -> EnsureResult
    async def update(uuid, params, check_mode=False) -> EnsureResult
    async def delete(uuid, check_mode=False) -> EnsureResult
    async def ensure(state, params, check_mode=False, uuid=None) -> EnsureResult
```

### Error handling

```python
try:
    result = await mgr.ensure("present", params)
except FieldValidationError as exc:
    print(f"Bad input: {exc.field} — {exc.rule}")
except AmbiguousMatchError as exc:
    print(f"Duplicates: {exc.uuids}")
except OpnsenseValidationError as exc:
    print(f"API validation: {exc.validations}")
except OpnsenseAuthError:
    print("401 — check API key")
except OpnsenseError as exc:
    print(f"API error: {exc}")
```

### WireGuard key pair flow

```python
from opnsense.managers.vpn.wg_server import WgServerManager
from opnsense.managers.vpn.wg_client import WgClientManager

async with OpnsenseClient(...) as client:
    server_mgr = WgServerManager(client)
    client_mgr = WgClientManager(client)

    # 1. Generate server key pair (store privkey in Vault)
    keys = await server_mgr.generate_keypair()
    # keys = {"privkey": "base64...", "pubkey": "base64..."}

    # 2. Create server tunnel
    await server_mgr.ensure("present", {
        "name": "wg0",
        "privkey": keys["privkey"],   # server keeps this
        "port": "51820",
        "tunneladdress": "10.10.0.1/24",
    })
    # Share keys["pubkey"] with all clients

    # 3. Add peer (client provides their pubkey)
    await client_mgr.ensure("present", {
        "name": "win11-rune",
        "pubkey": "<client-public-key>",  # from client device
        "tunneladdress": "10.10.0.2/32",
        "serveraddress": "fw.example.com",
        "serverport": "51820",
    })
```

Key exchange: each side generates its own key pair. Only public keys are shared.
Private keys never leave the device. Store server privkey in Vault KV.

---

## Testing

### Unit tests (1,207 tests, offline)

```bash
pytest tests/unit/ -q
```

### Integration tests (~380 tests, 54 files across 11 scopes, live OPNsense device)

```bash
# Set credentials in .env or environment
pytest tests/integration/ -q
```

### Features

- **bcrypt password verification** -- diff engine uses `bcrypt.checkpw()` for `$2y$` hashed fields (UpdateOnlyTextField), avoiding unnecessary updates on password-type fields
- **Firmware upgrade validation** -- `scripts/firmware-upgrade-check.sh` validates API compatibility before OPNsense upgrades
- **Enum field validation** -- 14 enum fixes verified by `scripts/verify-validators.py` (0 mismatches); per-manager regex-based port and IP validators
- **Per-manager test files** -- each integration test file follows a 10-step standard (setup, create, verify, update, verify, noop, delete, verify, cleanup, summary)

### Quality gates

```bash
ruff check src/ tests/           # lint
ruff format --check src/ tests/  # format
mypy src/ --ignore-missing-imports  # types
bandit -r src/ -q -ll            # security
```

---

## License

[MIT](LICENSE)
