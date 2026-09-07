# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""dnscrypt-proxy general settings manager (os-dnscrypt-proxy) — singleton get/set.

API domain: /api/dnscryptproxy/general
Payload key: general
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get   GET  dnscryptproxy/general/get
    set   POST dnscryptproxy/general/set  ({"general": {...}})
    apply POST dnscryptproxy/service/reconfigure

The encrypted upstream of the AdGuard -> Unbound -> dnscrypt-proxy chain: Unbound forwards
plaintext to ``listen_addresses`` (loopback :53531), dnscrypt-proxy does DoH/DNSCrypt upstream.
``serverlist``/``disabled_serverlist``/``relaylist`` are free-form ``CSVListField``s on the
API (server NAMES from the public-resolvers list the daemon downloads): the API does NOT
validate the names against that list — a ``GET`` echoes the current values as its only
"options" — so the whole config converges in one ``ensure``. Unknown names are ignored by
the daemon at runtime.

Schema discovered from ``GET /api/dnscryptproxy/general/get`` on OPNsense 26.7.3
(os-dnscrypt-proxy).
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select
from opnsense.models.base import EnsureResult

_MULTI_SELECT_FIELDS: tuple[str, ...] = (
    "listen_addresses",
    "serverlist",
    "disabled_serverlist",
    "relaylist",
)


class DnscryptProxyGeneralManager(BaseSingletonManager):
    """Manage the dnscrypt-proxy general settings via /api/dnscryptproxy/general.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager`; only the keys you pass are diffed.
    Requires the os-dnscrypt-proxy plugin.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = DnscryptProxyGeneralManager(client)
            await mgr.ensure("present", {"enabled": "1",
                "listen_addresses": ["127.0.0.1:53531", "[::1]:53531"],
                "require_dnssec": "1", "serverlist": ["cloudflare",
                "quad9-dnscrypt-ip4-filter-pri"]})

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
        before:   Current settings.
        after:    Settings after the set (or projected in ``check_mode``).
    """

    _endpoint = "dnscryptproxy/general"
    _payload_key = "general"
    _apply_endpoint = "dnscryptproxy/service/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = set()

    _validators = {
        # Boolean toggles
        "enabled": {"type": "bool_str"},
        "allowprivileged": {"type": "bool_str"},
        "block_ipv6": {"type": "bool_str"},
        "cache": {"type": "bool_str"},
        "dnscrypt_ephemeral_keys": {"type": "bool_str"},
        "dnscrypt_servers": {"type": "bool_str"},
        "doh_servers": {"type": "bool_str"},
        "force_tcp": {"type": "bool_str"},
        "ipv4_servers": {"type": "bool_str"},
        "ipv6_servers": {"type": "bool_str"},
        "odoh_servers": {"type": "bool_str"},
        "query_logs": {"type": "bool_str"},
        "require_dnssec": {"type": "bool_str"},
        "require_nofilter": {"type": "bool_str"},
        "require_nolog": {"type": "bool_str"},
        "tls_disable_session_tickets": {"type": "bool_str"},
        # String / numeric-as-string fields
        "cache_max_ttl": {"type": "str", "max_length": 10},
        "cache_min_ttl": {"type": "str", "max_length": 10},
        "cache_neg_max_ttl": {"type": "str", "max_length": 10},
        "cache_neg_min_ttl": {"type": "str", "max_length": 10},
        "cache_size": {"type": "str", "max_length": 10},
        "cert_refresh_delay": {"type": "str", "max_length": 10},
        "keepalive": {"type": "str", "max_length": 10},
        "max_clients": {"type": "str", "max_length": 10},
        "timeout": {"type": "str", "max_length": 10},
        "fallback_resolver": {"type": "str", "max_length": 255},
        "proxy": {"type": "str", "max_length": 255},
        # Multi-select (CSV after normalisation)
        "listen_addresses": {"type": "str", "max_length": 1024},
        "serverlist": {"type": "str", "max_length": 1024},
        "disabled_serverlist": {"type": "str", "max_length": 1024},
        "relaylist": {"type": "str", "max_length": 1024},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def ensure(
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Ensure the settings match ``params`` (multi-select lists normalised to CSV).

        Args:
            state:      Must be ``'present'``.
            params:     Desired settings; multi-select fields may be lists.
            check_mode: If True, report without changing anything.

        Returns:
            ``EnsureResult`` describing what was (or would be) done.
        """
        normalised = dict(params)
        for field in _MULTI_SELECT_FIELDS:
            if field in normalised:
                normalised[field] = normalize_multi_select(normalised[field])
        return await super().ensure(state, normalised, check_mode=check_mode)
