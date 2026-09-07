# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense QEMU guest agent settings manager (os-qemu-guest-agent) — singleton config (get/set).

API domain: /api/qemuguestagent/settings
Payload key: qemuguestagent / section: general
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get   GET  qemuguestagent/settings/get
    set   POST qemuguestagent/settings/set  ({"qemuguestagent": {"general": {...}}})
    apply POST qemuguestagent/service/reconfigure

Field names are CamelCase on this plugin (``Enabled``, ``LogDebug``, ``DisabledRPCs``). The
document nests them under ``general`` (``_section``). ``DisabledRPCs`` is a multi-select of
guest-* RPC names to block (e.g. ``guest-exec``) — pass a list or CSV.

Schema discovered from ``GET /api/qemuguestagent/settings/get`` on OPNsense 26.7.3
(os-qemu-guest-agent).
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager
from opnsense.core.validation import normalize_multi_select
from opnsense.models.base import EnsureResult

_MULTI_SELECT_FIELDS: tuple[str, ...] = ("DisabledRPCs",)


class QemuGuestAgentSettingsManager(BaseSingletonManager):
    """Manage the QEMU guest agent settings via /api/qemuguestagent/settings.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager`; only the keys you pass are diffed.
    Requires the os-qemu-guest-agent plugin.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = QemuGuestAgentSettingsManager(client)
            await mgr.ensure("present", {"Enabled": "1", "DisabledRPCs": ["guest-exec",
            "guest-exec-status"]})

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
        before:   Current settings.
        after:    Settings after the set (or projected in ``check_mode``).
    """

    _endpoint = "qemuguestagent/settings"
    _payload_key = "qemuguestagent"
    _section = "general"
    _apply_endpoint = "qemuguestagent/service/reconfigure"
    _apply_timeout = 60

    REDACT_FIELDS: set[str] = set()

    _validators = {
        # Boolean toggles
        "Enabled": {"type": "bool_str"},
        "LogDebug": {"type": "bool_str"},
        # Multi-select (CSV after normalisation)
        "DisabledRPCs": {"type": "str", "max_length": 1024},
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
