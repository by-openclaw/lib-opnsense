# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense LLDP daemon general settings manager (os-lldpd) — singleton config (get/set).

API domain: /api/lldpd/general
Payload key: general
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get   GET  lldpd/general/get
    set   POST lldpd/general/set  ({"general": {...}})
    apply POST lldpd/service/reconfigure

``interface`` is a CSV of interface slot ids (TextField on the API, not an option list) —
announce LLDP on internal ports only, never the WAN uplinks. cdp/fdp/edp/sonmp enable
vendor discovery protocols; agentx exposes an SNMP AgentX sub-agent.

Schema discovered from ``GET /api/lldpd/general/get`` on OPNsense 26.7.3 (os-lldpd).
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select
from opnsense.models.base import EnsureResult

_MULTI_SELECT_FIELDS: tuple[str, ...] = ("interface",)


class LldpdGeneralManager(BaseSingletonManager):
    """Manage the LLDP daemon general settings via /api/lldpd/general.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager`; only the keys you pass are diffed.
    Requires the os-lldpd plugin.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = LldpdGeneralManager(client)
            await mgr.ensure("present", {"enabled": "1", "interface": ["lan", "opt1", "opt2"],
            "cdp": "0"})

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
        before:   Current settings.
        after:    Settings after the set (or projected in ``check_mode``).
    """

    _endpoint = "lldpd/general"
    _payload_key = "general"
    _apply_endpoint = "lldpd/service/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = set()

    _validators = {
        # Boolean toggles
        "enabled": {"type": "bool_str"},
        "cdp": {"type": "bool_str"},
        "fdp": {"type": "bool_str"},
        "edp": {"type": "bool_str"},
        "sonmp": {"type": "bool_str"},
        "agentx": {"type": "bool_str"},
        # String / numeric-as-string fields
        "interface": {"type": "str", "max_length": 255},
        # Multi-select (CSV after normalisation)
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
