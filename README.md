# lib-opnsense

Async Python library for [OPNsense](https://opnsense.org/) REST API -- user, group, privilege, and firewall management.

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/by-openclaw/lib-opnsense/releases)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/by-openclaw/lib-opnsense/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-pending-lightgrey)](https://github.com/by-openclaw/lib-opnsense/actions/workflows/ci.yml)

> **Internal use -- BY-SYSTEMS DevOps platform.**
> See [LICENSE](LICENSE) for terms and disclaimer of liability.

---

## Install

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
from opnsense.managers.auth_user import AuthUserManager
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
        users = AuthUserManager(client)
        result = await users.ensure(
            state="present",
            params={"name": "svc-deploy", "email": "deploy@example.com"},
        )
        print(result)  # EnsureResult(changed=True, action='created', uuid='...')

asyncio.run(main())
```

---

## Architecture

> PlantUML source: `assets/diagrams/lib-architecture.puml`
> Flow diagram: `assets/diagrams/ensure-flow.puml`
> Render: open in VS Code with PlantUML extension, or `java -jar plantuml.jar assets/diagrams/*.puml`

```
OpnsenseClient (httpx async, retry, exception mapping)
    |
    +-- BaseManager (abstract CRUD + ensure lifecycle)
    |       |
    |       +-- AuthUserManager    /api/auth/user
    |       +-- AuthGroupManager   /api/auth/group
    |       +-- (future managers follow same pattern)
    |
    +-- AuthPrivManager (privilege assignment, non-CRUD)
    |
    +-- Credentials
    |       +-- EnvCredentialProvider   (env vars / .env)
    |       +-- VaultCredentialProvider (HashiCorp Vault KV v2)
    |
    +-- Models
    |       +-- EnsureResult (frozen dataclass)
    |
    +-- Exceptions
            +-- OpnsenseError (base)
            +-- OpnsenseAuthError (401)
            +-- OpnsensePermissionError (403)
            +-- OpnsenseEndpointMissingError (404)
            +-- OpnsenseValidationError (400 / result=failed)
            +-- OpnsenseServerError (500)
            +-- OpnsenseTimeoutError
            +-- OpnsenseConnectionError
```

---

## API coverage

Coverage by domain. Checked = implemented + tested. Unchecked = planned.
Verified against OPNsense **25.1.12**.

### Auth (immediate, no reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list users | `AuthUserManager` | `POST /api/auth/user/search` | [x] |
| get user | `AuthUserManager` | `GET /api/auth/user/get/{uuid}` | [x] |
| create user | `AuthUserManager` | `POST /api/auth/user/add` | [x] |
| update user | `AuthUserManager` | `POST /api/auth/user/set/{uuid}` | [x] |
| delete user | `AuthUserManager` | `POST /api/auth/user/del/{uuid}` | [x] |
| ensure user | `AuthUserManager` | (composite) | [x] |
| list groups | `AuthGroupManager` | `POST /api/auth/group/search` | [x] |
| get group | `AuthGroupManager` | `GET /api/auth/group/get/{uuid}` | [x] |
| create group | `AuthGroupManager` | `POST /api/auth/group/add` | [x] |
| update group | `AuthGroupManager` | `POST /api/auth/group/set/{uuid}` | [x] |
| delete group | `AuthGroupManager` | `POST /api/auth/group/del/{uuid}` | [x] |
| ensure group | `AuthGroupManager` | (composite) | [x] |
| list privileges | `AuthPrivManager` | `GET /api/auth/priv/get` | [x] |
| assign privilege | `AuthPrivManager` | `POST /api/auth/priv/set_item/{id}` | [x] |
| ensure privilege | `AuthPrivManager` | (composite) | [x] |

### Firewall (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list aliases | `FwAliasManager` | `POST /api/firewall/alias/search_item` | [ ] |
| ensure alias | `FwAliasManager` | (composite) | [ ] |
| list filter rules | `FwRuleManager` | `POST /api/firewall/filter/search_rule` | [ ] |
| ensure filter rule | `FwRuleManager` | (composite) | [ ] |
| list SNAT rules | `FwSnatManager` | `POST /api/firewall/source_nat/search_rule` | [ ] |
| ensure SNAT rule | `FwSnatManager` | (composite) | [ ] |

### Unbound DNS (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list forwarders | `UbForwardManager` | `POST /api/unbound/settings/search_forward` | [ ] |
| ensure forwarder | `UbForwardManager` | (composite) | [ ] |
| list host overrides | `UbHostOverrideManager` | `POST /api/unbound/settings/search_host_override` | [ ] |
| ensure host override | `UbHostOverrideManager` | (composite) | [ ] |

### Kea DHCPv4 (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list subnets | `KeaSubnetManager` | `POST /api/kea/dhcpv4/search_subnet` | [ ] |
| ensure subnet | `KeaSubnetManager` | (composite) | [ ] |
| list reservations | `KeaReservationManager` | `POST /api/kea/dhcpv4/search_reservation` | [ ] |
| ensure reservation | `KeaReservationManager` | (composite) | [ ] |

### WireGuard (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list servers | `WgServerManager` | `POST /api/wireguard/server/search_server` | [ ] |
| ensure server | `WgServerManager` | (composite) | [ ] |
| list clients | `WgClientManager` | `POST /api/wireguard/client/search_client` | [ ] |
| ensure client | `WgClientManager` | (composite) | [ ] |

### Interfaces (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list VLANs | `IfVlanManager` | `POST /api/interfaces/vlan_settings/search_item` | [ ] |
| ensure VLAN | `IfVlanManager` | (composite) | [ ] |

### Routes / Gateways (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list routes | `RtRouteManager` | `POST /api/routes/routes/searchroute` | [ ] |
| ensure route | `RtRouteManager` | (composite) | [ ] |
| list gateways | `RtGatewayManager` | `POST /api/routing/settings/search_gateway` | [ ] |
| ensure gateway | `RtGatewayManager` | (composite) | [ ] |

### System (various)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list syslog destinations | `SyslogDestManager` | `POST /api/syslog/settings/search_destinations` | [ ] |
| ensure syslog destination | `SyslogDestManager` | (composite) | [ ] |
| list cron jobs | `CronJobManager` | `POST /api/cron/settings/search_jobs` | [ ] |
| ensure cron job | `CronJobManager` | (composite) | [ ] |

### Diagnostics (read-only, no manager needed)

| Method | Client direct | Endpoint | Status |
|--------|---------------|----------|:------:|
| system info | `client.get()` | `GET /api/diagnostics/system/system_information` | [x] |
| ARP table | `client.get()` | `GET /api/diagnostics/interface/get_arp` | [x] |
| routing table | `client.get()` | `GET /api/diagnostics/interface/get_routes` | [x] |
| firewall stats | `client.get()` | `GET /api/diagnostics/firewall/stats` | [x] |
| gateway status | `client.get()` | `GET /api/routes/gateway/status` | [x] |

---

## API reference

### OpnsenseClient

```python
class OpnsenseClient:
    def __init__(self, host, key, secret, port=443, verify_ssl=False,
                 timeout=30, async_timeout=300, max_retries=3, retry_backoff=2.0)
    async def get(endpoint: str) -> dict
    async def post(endpoint: str, data: dict | None = None) -> dict
    async def search(endpoint: str, search_phrase: str = "", row_count: int = 50) -> list[dict]
    async def create(endpoint: str, payload_key: str, params: dict) -> str  # returns UUID
    async def update(endpoint: str, uuid: str, payload_key: str, params: dict) -> dict
    async def delete(endpoint: str, uuid: str) -> dict
    async def reconfigure(endpoint: str) -> dict
    async def wait_for_ready(check_endpoint: str, timeout: float | None, interval: float = 3.0) -> dict
```

### BaseManager

```python
class BaseManager(ABC):
    async def list(search_phrase: str = "") -> list[dict]
    async def get(uuid: str) -> dict
    async def get_schema() -> dict
    async def create(params: dict, check_mode: bool = False) -> EnsureResult
    async def update(uuid: str, params: dict, check_mode: bool = False) -> EnsureResult
    async def delete(uuid: str, check_mode: bool = False) -> EnsureResult
    async def ensure(state: str, params: dict, check_mode: bool = False) -> EnsureResult
```

### AuthUserManager

Extends BaseManager. Endpoint: `/api/auth/user`. Redacts: `password`, `otp_seed`, `scrambled_password`, `authorizedkeys`.

### AuthGroupManager

Extends BaseManager. Endpoint: `/api/auth/group`. No redacted fields.

### AuthPrivManager

Standalone manager (not BaseManager). Manages privilege assignments between users/groups and privilege IDs.

```python
class AuthPrivManager:
    async def list_privileges() -> list[dict]
    async def get_assignment(priv_id: str) -> dict
    async def ensure(priv_id: str, target_type: str, target_name: str,
                     state: str = "present", check_mode: bool = False) -> EnsureResult
```

---

## Testing

### Unit tests (offline -- no firewall required)

```bash
pytest tests/unit/ -v
```

### Smoke tests

```bash
pytest tests/smoke/ -v
```

### Integration tests (live OPNsense device)

Requires a reachable OPNsense device and environment variables set:

```bash
OPN_HOST=opnsense.example.com OPN_KEY=your-key OPN_SECRET=your-secret \
pytest tests/integration/ -v
```

### Linting and type checking

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
```

---

## Dev container

A `.devcontainer/` configuration will be provided in a future release. Until then, use the venv setup above.

---

## License

[MIT](LICENSE)
