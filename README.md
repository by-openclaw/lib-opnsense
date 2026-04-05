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
            params={"name": "svc-deploy", "email": "deploy@by-systems.be"},
        )
        print(result)  # EnsureResult(changed=True, action='created', uuid='...')

asyncio.run(main())
```

---

## Architecture

```
OpnsenseClient (httpx async, retry, exception mapping)
    |
    +-- BaseManager (abstract CRUD + ensure lifecycle)
    |       |
    |       +-- AuthUserManager    /api/auth/user
    |       +-- AuthGroupManager   /api/auth/group
    |
    +-- AuthPrivManager (privilege assignment, non-CRUD)
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

## Available managers

| Manager | API domain | Payload key | Match key | Reconfigure |
|---|---|---|---|---|
| `AuthUserManager` | `/api/auth/user` | `user` | `name` | No (immediate) |
| `AuthGroupManager` | `/api/auth/group` | `group` | `name` | No (immediate) |
| `AuthPrivManager` | `/api/auth/priv` | n/a | n/a | No (immediate) |

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
OPN_HOST=10.6.224.106 OPN_KEY=your-key OPN_SECRET=your-secret \
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
