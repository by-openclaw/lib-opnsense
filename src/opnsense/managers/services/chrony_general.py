# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Chrony NTP general settings manager (os-chrony) — singleton config (get/set).

API domain: /api/chrony/general
Payload key: general
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get   GET  chrony/general/get
    set   POST chrony/general/set  ({"general": {...}})
    apply POST chrony/service/reconfigure

Client-only NTP unless ``allowednetworks`` is non-empty (then chronyd serves :123 to those
networks). ``peers``/``allowednetworks`` are multi-selects — pass a list or a CSV string.
Replaces the base ntpd (stop it with ``core/service/stop/ntpd``).

Schema discovered from ``GET /api/chrony/general/get`` on OPNsense 26.7.3 (os-chrony).
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select
from opnsense.models.base import EnsureResult

_MULTI_SELECT_FIELDS: tuple[str, ...] = (
    "peers",
    "allowednetworks",
)


class ChronyGeneralManager(BaseSingletonManager):
    """Manage the Chrony NTP general settings via /api/chrony/general.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager`; only the keys you pass are diffed.
    Requires the os-chrony plugin.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = ChronyGeneralManager(client)
            await mgr.ensure("present", {"enabled": "1", "port": "123",
                "peers": ["0.be.pool.ntp.org", "1.be.pool.ntp.org"],
                "allowednetworks": ["10.1.0.0/16", "fd01::/32"]})

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
        before:   Current settings.
        after:    Settings after the set (or projected in ``check_mode``).
    """

    _endpoint = "chrony/general"
    _payload_key = "general"
    _apply_endpoint = "chrony/service/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = set()

    _validators = {
        # Boolean toggles
        "enabled": {"type": "bool_str"},
        "ntsclient": {"type": "bool_str"},
        "ntsnocert": {"type": "bool_str"},
        # String / numeric-as-string fields
        "port": {"type": "str", "max_length": 5},
        "fallbackpeers": {"type": "str", "max_length": 255},
        # Multi-select (CSV after normalisation)
        "peers": {"type": "str", "max_length": 1024},
        "allowednetworks": {"type": "str", "max_length": 1024},
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
