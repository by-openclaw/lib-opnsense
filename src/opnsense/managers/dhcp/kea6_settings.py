# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCP6 general settings manager — singleton config (get/set).

API domain: /api/kea/dhcpv6
Payload key: dhcpv6 / section: general
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get   GET  kea/dhcpv6/get
    set   POST kea/dhcpv6/set  ({"dhcpv6": {"general": {...}}})
    apply POST kea/service/reconfigure

``mac_sources`` is a multi-select (default ``ipv6-link-local``). Kea v6 does NOT emit router
advertisements — pair it with radvd.
Subnets / reservations are managed by the ``Kea6*Manager`` classes.
A freshly seeded FW ships ``enabled='0'`` — this block turns the daemon on and binds it to
``interfaces`` (slot ids, list or CSV).

Schema discovered from ``GET /api/kea/dhcpv6/get`` on OPNsense 26.7.3.
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select
from opnsense.models.base import EnsureResult

_MULTI_SELECT_FIELDS: tuple[str, ...] = (
    "interfaces",
    "mac_sources",
)


class Kea6SettingsManager(BaseSingletonManager):
    """Manage the Kea DHCPv6 ``general`` block via /api/kea/dhcpv6.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = Kea6SettingsManager(client)
            await mgr.ensure("present", {"enabled": "1", "interfaces": ["opt2", "opt3"],
                                         "valid_lifetime": "4000", "fwrules": "0"})

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
    """

    _endpoint = "kea/dhcpv6"
    _payload_key = "dhcpv6"
    _section = "general"
    _apply_endpoint = "kea/service/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = set()

    _validators = {
        # Boolean toggles
        "enabled": {"type": "bool_str"},
        "fwrules": {"type": "bool_str"},
        "manual_config": {"type": "bool_str"},
        # Numeric-as-string fields
        "valid_lifetime": {"type": "str", "max_length": 10},
        "decline_probation_period": {"type": "str", "max_length": 10},
        "service_sockets_max_retries": {"type": "str", "max_length": 10},
        "service_sockets_retry_wait_time": {"type": "str", "max_length": 10},
        # Multi-select (CSV after normalisation)
        "interfaces": {"type": "str", "max_length": 1024},
        "mac_sources": {"type": "str", "max_length": 1024},
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
        """Ensure the ``general`` block matches ``params`` (multi-select lists normalised)."""
        normalised = dict(params)
        for field in _MULTI_SELECT_FIELDS:
            if field in normalised:
                normalised[field] = normalize_multi_select(normalised[field])
        return await super().ensure(state, normalised, check_mode=check_mode)
