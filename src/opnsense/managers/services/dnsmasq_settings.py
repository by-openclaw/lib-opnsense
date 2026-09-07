# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq global settings manager — singleton config (get/set).

API domain: /api/dnsmasq/settings
Payload key: dnsmasq
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get  GET  dnsmasq/settings/get
    set  POST dnsmasq/settings/set
    apply POST dnsmasq/service/reconfigure

Sub-resources (hosts, ranges, domains, options, boot, tags) are managed by
their own ``Dnsmasq*Manager`` classes — not by this one.

Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select

# Kept as a module alias: the helper moved to ``opnsense.core.validation`` so
# every multi-select manager (dnsmasq, unbound, …) shares one implementation.
_normalize_multi_select = normalize_multi_select


class DnsmasqSettingsManager(BaseSingletonManager):
    """Manage the OPNsense Dnsmasq global config via /api/dnsmasq/settings.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager`. Sub-resources (host overrides, DHCP ranges,
    domain forwarders, options, boot, tags) belong to their dedicated managers.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = DnsmasqSettingsManager(client)
            # Disable Dnsmasq DHCP/RA so Kea can bind 67/547
            await mgr.ensure("present", {"enable": "0"})
            # Or: bind only to listed interfaces, leaving others alone
            await mgr.ensure("present", {
                "enable": "1",
                "strictbind": "1",
                "interface": ["lan"],            # list ok — normalised to "lan"
                "port": "53053",                 # leave 53 to Unbound
            })

    Input (ensure present): see :class:`opnsense.models.services.dnsmasq.DnsmasqSettings`
    for the full attribute list — every field is optional; only the keys you
    pass are diffed.

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
        before:   Current settings (redacted).
        after:    Settings after the set (redacted).
    """

    _endpoint = "dnsmasq/settings"
    _payload_key = "dnsmasq"
    _apply_endpoint = "dnsmasq/service/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = set()

    _validators = {
        # Boolean toggles
        "enable": {"type": "bool_str"},
        "regdhcp": {"type": "bool_str"},
        "regdhcpstatic": {"type": "bool_str"},
        "dhcpfirst": {"type": "bool_str"},
        "strict_order": {"type": "bool_str"},
        "domain_needed": {"type": "bool_str"},
        "no_private_reverse": {"type": "bool_str"},
        "no_resolv": {"type": "bool_str"},
        "log_queries": {"type": "bool_str"},
        "no_hosts": {"type": "bool_str"},
        "strictbind": {"type": "bool_str"},
        "dnssec": {"type": "bool_str"},
        "add_subnet": {"type": "bool_str"},
        "strip_subnet": {"type": "bool_str"},
        "no_ident": {"type": "bool_str"},
        # String fields
        "regdhcpdomain": {"type": "str", "max_length": 255},
        "interface": {"type": "str", "max_length": 255},
        "port": {"type": "str", "max_length": 5},
        "dns_port": {"type": "str", "max_length": 5},
        "dns_forward_max": {"type": "str", "max_length": 10},
        "cache_size": {"type": "str", "max_length": 10},
        "local_ttl": {"type": "str", "max_length": 10},
        # Single-select enum
        "add_mac": {
            "type": "enum",
            "values": ["", "standard", "base64", "text"],
        },
        # Multi-select enum (validator only checks it's a string after normalize)
        "dhcp": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Dnsmasq settings manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def ensure(
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> Any:
        """Normalise multi-select fields then delegate to the base ``ensure``.

        Multi-select fields (``interface``, ``dhcp``) accept either a string
        or a list/tuple/set on input; the API requires a comma-separated
        string on ``set``. We coerce here so callers don't have to remember.
        """
        if state == "present":
            normalized = dict(params)
            for k in ("interface", "dhcp"):
                if k in normalized:
                    normalized[k] = _normalize_multi_select(normalized[k])
            params = normalized
        return await super().ensure(state, params, check_mode=check_mode)
