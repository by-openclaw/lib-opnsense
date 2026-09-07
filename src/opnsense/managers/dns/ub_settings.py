# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound general settings manager — singleton config (get/set).

API domain: /api/unbound/settings
Payload key: unbound
Section:     general
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

The Unbound ``settings/get`` document nests the resolver's daemon config under
``general`` (next to ``advanced``, ``acls``, ``dnsbl``, ``forwarding``, ``dots``,
``hosts``, ``aliases``). This manager owns the ``general`` block only; on
``set`` the params are sent as ``{"unbound": {"general": {...}}}``. The
sub-resource collections have their own ``Ub*Manager`` classes.

Endpoints:
    get   GET  unbound/settings/get
    set   POST unbound/settings/set
    apply POST unbound/service/reconfigure

A freshly installed/seeded firewall ships with ``enabled='0'`` — the resolver
does not run until this block enables it. Multi-select fields
(``active_interface``, ``outgoing_interface``) accept a list or a CSV string
of interface slot ids; an empty value means "all interfaces".

Schema discovered from ``GET /api/unbound/settings/get`` on OPNsense 26.7.3.
Reference: https://docs.opnsense.org/manual/unbound.html
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select
from opnsense.models.base import EnsureResult

_MULTI_SELECT_FIELDS: tuple[str, ...] = ("active_interface", "outgoing_interface")


class UbSettingsManager(BaseSingletonManager):
    """Manage the OPNsense Unbound ``general`` config via /api/unbound/settings.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager` (``_section='general'`` unwraps/re-nests the
    block). Forwards, DoT, ACLs, host overrides and aliases belong to their
    dedicated managers.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = UbSettingsManager(client)
            # Enable the resolver on :53 for every interface (fresh FW)
            await mgr.ensure("present", {"enabled": "1", "port": "53"})
            # Listen only on the internal slots, resolve DNSSEC
            await mgr.ensure("present", {
                "enabled": "1",
                "active_interface": ["lan", "opt2"],   # list ok — normalised to CSV
                "dnssec": "1",
            })

    Input (ensure present): see :class:`opnsense.models.dns.ub_settings.UbSettings`
    for the full attribute list — every field is optional; only the keys you
    pass are diffed.

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
        before:   Current ``general`` settings.
        after:    Settings after the set (or projected in ``check_mode``).
    """

    _endpoint = "unbound/settings"
    _payload_key = "unbound"
    _section = "general"
    _apply_endpoint = "unbound/service/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = set()

    _validators = {
        # Boolean toggles
        "enabled": {"type": "bool_str"},
        "stats": {"type": "bool_str"},
        "dnssec": {"type": "bool_str"},
        "dns64": {"type": "bool_str"},
        "noarecords": {"type": "bool_str"},
        "regdhcp": {"type": "bool_str"},
        "regdhcpstatic": {"type": "bool_str"},
        "noreglladdr6": {"type": "bool_str"},
        "noregrecords": {"type": "bool_str"},
        "txtsupport": {"type": "bool_str"},
        "cacheflush": {"type": "bool_str"},
        "safesearch": {"type": "bool_str"},
        "enable_wpad": {"type": "bool_str"},
        # String fields
        "port": {"type": "str", "max_length": 5},
        "dns64prefix": {"type": "str", "max_length": 64},
        "regdhcpdomain": {"type": "str", "max_length": 255},
        # Multi-select (CSV of interface slot ids after normalisation)
        "active_interface": {"type": "str", "max_length": 255},
        "outgoing_interface": {"type": "str", "max_length": 255},
        # Single-select enum
        "local_zone_type": {
            "type": "enum",
            "values": [
                "always_nxdomain",
                "always_refuse",
                "always_transparent",
                "deny",
                "inform",
                "inform_deny",
                "nodefault",
                "refuse",
                "static",
                "transparent",
                "typetransparent",
            ],
        },
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Unbound settings manager.

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
        """Ensure the ``general`` block matches ``params`` (multi-selects normalised).

        Args:
            state:      Must be ``'present'``.
            params:     Desired settings; ``active_interface`` /
                        ``outgoing_interface`` may be a list of slot ids.
            check_mode: If True, report without changing anything.

        Returns:
            ``EnsureResult`` describing what was (or would be) done.
        """
        normalised = dict(params)
        for field in _MULTI_SELECT_FIELDS:
            if field in normalised:
                normalised[field] = normalize_multi_select(normalised[field])
        return await super().ensure(state, normalised, check_mode=check_mode)
