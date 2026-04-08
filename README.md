# lib-opnsense

Async Python library for [OPNsense](https://opnsense.org/) REST API — CRUD + idempotent ensure() for auth, firewall, DNS, interfaces, and traffic shaping.

[![Version](https://img.shields.io/badge/version-0.2.0-blue)](https://github.com/by-openclaw/lib-opnsense/releases)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/by-openclaw/lib-opnsense/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Internal use — BY-SYSTEMS DevOps platform.**
> See [LICENSE](LICENSE) for terms and disclaimer of liability.

---

## Install

```bash
pip install git+https://github.com/by-openclaw/lib-opnsense.git@v0.2.0
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
from opnsense.managers.fw_filter import FwFilterManager
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
│   └── 20 concrete managers       # Config only (~30 lines each)
│
├── models/                        # Frozen dataclasses — one per entity
│   ├── base.py                    # EnsureResult
│   └── 16 entity models           # AuthUser, FwFilterRule, UbHostOverride, ...
│
├── client.py                      # httpx async transport (retry, exception mapping)
├── exceptions.py                  # Typed exception hierarchy (8 types)
├── credentials.py                 # EnvCredentialProvider + VaultCredentialProvider
└── logging.py                     # Structlog config (delegates to core/redaction)
```

---

## Managers (20 total)

### Auth (4 managers — changes apply immediately)

| Manager | Match keys | Notes |
|---------|------------|-------|
| AuthUserManager | `name` | CRUD + ensure, redacts password/otp |
| AuthGroupManager | `name` | CRUD + ensure |
| AuthPrivManager | — | Standalone, privilege assignment |
| AuthApiKeyManager | — | Standalone, API key lifecycle |

### Firewall (7 managers — requires apply/reconfigure)

| Manager | Match keys | Notes |
|---------|------------|-------|
| FwAliasManager | `name` | Host, network, port, URL aliases |
| FwFilterManager | `description, interface, direction, protocol` | Pass/block/reject rules |
| FwDnatManager | `descr, interface, target` | Port forwarding (D-NAT) |
| FwSourceNatManager | `description, interface, source_net` | Outbound NAT / masquerade |
| FwOneToOneManager | `description, interface, source_net` | Bidirectional 1:1 NAT |
| FwCategoryManager | `name` | Rule categories (immediate) |
| FwGroupManager | `ifname` | Interface groups (immediate) |

### Interfaces (2 managers — requires reconfigure)

| Manager | Match keys | Notes |
|---------|------------|-------|
| IfVlanManager | `tag, if` | 802.1Q VLAN sub-interfaces |
| IfVipManager | `address, interface, mode` | Virtual IPs (alias, CARP, proxy ARP) |

### Traffic Shaper (1 manager — requires reconfigure)

| Manager | Match keys | Notes |
|---------|------------|-------|
| TsPipeManager | `description, bandwidth, bandwidthMetric` | Bandwidth pipes |

### Unbound DNS (6 managers — requires reconfigure)

| Manager | Match keys | Notes |
|---------|------------|-------|
| UbHostOverrideManager | `hostname, domain, server` | Local A/AAAA/MX records |
| UbHostAliasManager | `hostname, domain` | CNAME-like aliases (create+read only on 26.1.5) |
| UbForwardManager | `domain, server` | Domain-specific DNS forwarding |
| UbAclManager | `name` | Resolver access control lists |
| UbDotManager | `server, port` | DNS-over-TLS upstream servers |
| UbDiagnosticsManager | — | Read-only: stats + DNSBL config |

### API coverage

See [docs/api-coverage.md](docs/api-coverage.md) for the full per-endpoint status table (134 domains probed, 18 integration tested).

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

---

## Testing

### Unit tests (558 tests, offline)

```bash
pytest tests/unit/ -q
```

### Integration tests (173 tests, live OPNsense device)

```bash
# Set credentials in .env or environment
pytest tests/integration/ -q
```

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
