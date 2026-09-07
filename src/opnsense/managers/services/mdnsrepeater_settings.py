# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense mDNS repeater (os-mdns-repeater) settings manager — singleton config (get/set).

API domain: /api/mdnsrepeater/settings
Payload key: mdnsrepeater
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get   GET  mdnsrepeater/settings/get
    set   POST mdnsrepeater/settings/set
    apply POST mdnsrepeater/service/reconfigure

Repeats mDNS (Bonjour/Avahi) between the selected ``interfaces`` (slot ids, at least two);
``blocklist`` holds networks whose announcements are dropped. Requires the os-mdns-repeater plugin.

Schema discovered from ``GET /api/mdnsrepeater/settings/get`` on OPNsense 26.7.3.
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select
from opnsense.models.base import EnsureResult

_MULTI_SELECT_FIELDS: tuple[str, ...] = (
    "interfaces",
    "blocklist",
)


class MdnsRepeaterSettingsManager(BaseSingletonManager):
    """OPNsense mDNS repeater (os-mdns-repeater) settings manager.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = MdnsRepeaterSettingsManager(client)
            await mgr.ensure("present", {"enabled": "1", "interfaces": ["opt2", "opt8", "opt10"]})

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
    """

    _endpoint = "mdnsrepeater/settings"
    _payload_key = "mdnsrepeater"
    _apply_endpoint = "mdnsrepeater/service/reconfigure"
    _apply_timeout = 120

    REDACT_FIELDS: set[str] = set()

    _validators = {
        # Boolean toggles
        "enabled": {"type": "bool_str"},
        "enablecarp": {"type": "bool_str"},
        # Multi-select (CSV after normalisation)
        "interfaces": {"type": "str", "max_length": 4096},
        "blocklist": {"type": "str", "max_length": 4096},
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
        """Ensure the settings match ``params`` (multi-select lists normalised to CSV)."""
        normalised = dict(params)
        for field in _MULTI_SELECT_FIELDS:
            if field in normalised:
                normalised[field] = normalize_multi_select(normalised[field])
        return await super().ensure(state, normalised, check_mode=check_mode)
