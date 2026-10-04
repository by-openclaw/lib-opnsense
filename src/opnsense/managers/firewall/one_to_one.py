# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall 1:1 NAT (BINAT) manager — CRUD + ensure().

API domain: /api/firewall/one_to_one
Payload key: rule
Match key:   description (unique rule description)
Entity suffix: Rule (searchRule, getRule, addRule, setRule, delRule)

Endpoints:
    search  GET  firewall/one_to_one/searchRule
    get     GET  firewall/one_to_one/getRule/{uuid}
    create  POST firewall/one_to_one/addRule
    update  POST firewall/one_to_one/setRule/{uuid}
    delete  POST firewall/one_to_one/delRule/{uuid}
    apply   POST firewall/one_to_one/apply

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M11
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager
from opnsense.models.base import EnsureResult

_TRUE = {"1", "true", "yes", "on"}


class FwOneToOneManager(BaseManager):
    """Manage OPNsense 1:1 NAT (BINAT) rules via /api/firewall/one_to_one.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    1:1 NAT maps an external IP bidirectionally to an internal IP.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwOneToOneManager(client)
            result = await mgr.ensure("present", {
                "description": "1:1 NAT WAN ↔ DMZ Traefik",
                "interface": "wan",
                "type": "binat",
                "external": "10.6.224.106",
                "source_net": "10.1.2.10/32",
            })

    Input (ensure present):
        description:  Rule description, max 255 (required)
        interface:    Interface name (required)
        source_net:   Source network (required)
        external:     External IP address (optional)
        disabled:     Disable rule (optional, default='0')
        sequence:     Rule order priority, min 1 (optional)
        source_not:   Invert source match (optional, default='0')
        destination_not: Invert destination match (optional, default='0')
        destination_net: Destination network (optional)
        log:          Log matching packets (optional, default='0')
        type:         NAT type — binat, nat (optional)
        natreflection: NAT reflection — '', enable, disable (optional)
        categories:   Comma-separated category UUIDs (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "firewall/one_to_one"
    _payload_key = "rule"
    _entity_suffix = "Rule"  # search_rule, get_rule, add_rule, set_rule, del_rule
    _apply_endpoint = "firewall/one_to_one/apply"
    _match_keys = ["description", "interface", "source_net"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "interface": {"type": "str", "required": True},
        "source_net": {"type": "str", "required": True},
        "external": {"type": "str"},
        # The API field is `enabled` (every probed firmware, 25.1 → 26.7.5). `disabled` is
        # the historical input of this manager: accepted, translated in ensure(), never sent
        # — the API ignored it, so a rule declared disabled was created enabled.
        "enabled": {"type": "bool_str"},
        "disabled": {"type": "bool_str"},
        "sequence": {"type": "int", "min": 1},
        "source_not": {"type": "bool_str"},
        "destination_not": {"type": "bool_str"},
        "destination_net": {"type": "str"},
        "log": {"type": "bool_str"},
        "type": {"type": "enum", "values": ["binat", "nat"]},
        "natreflection": {"type": "enum", "values": ["", "enable", "disable"]},
        "categories": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall 1:1 NAT manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def ensure(
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
        uuid: str | None = None,
        dedupe: bool = False,
        force_update: bool = False,
    ) -> EnsureResult:
        """Ensure the rule; a legacy ``disabled`` input becomes the API's ``enabled``.

        Args:
            state:        ``'present'`` or ``'absent'``.
            params:       Rule parameters; ``enabled``, or the legacy ``disabled``.
            check_mode:   If True, report without changing anything.
            uuid:         Optional UUID, bypasses the identity lookup.
            dedupe:       Collapse duplicates of the same identity.
            force_update: Send the update even without a visible difference.

        Returns:
            ``EnsureResult`` describing what was (or would be) done.

        Raises:
            ValueError: If ``disabled`` and ``enabled`` are both given and contradict.
        """
        return await super().ensure(
            state,
            self._api_enable_flag(params),
            check_mode=check_mode,
            uuid=uuid,
            dedupe=dedupe,
            force_update=force_update,
        )

    async def create(self, params: dict[str, Any], check_mode: bool = False) -> EnsureResult:
        """Create a rule; a legacy ``disabled`` input becomes the API's ``enabled``.

        Args:
            params:     Rule field values.
            check_mode: If True, report without changing anything.

        Returns:
            ``EnsureResult`` with ``action='created'``.
        """
        return await super().create(self._api_enable_flag(params), check_mode=check_mode)

    async def update(
        self,
        uuid: str,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Update a rule; a legacy ``disabled`` input becomes the API's ``enabled``.

        Args:
            uuid:       Rule UUID.
            params:     Rule field values.
            check_mode: If True, report without changing anything.

        Returns:
            ``EnsureResult`` with ``action='updated'``.
        """
        return await super().update(uuid, self._api_enable_flag(params), check_mode=check_mode)

    @staticmethod
    def _api_enable_flag(params: dict[str, Any]) -> dict[str, Any]:
        """Return ``params`` with a legacy ``disabled`` translated to ``enabled``."""
        if "disabled" not in params:
            return params
        disabled = str(params["disabled"]).lower() in _TRUE
        if "enabled" in params and (str(params["enabled"]).lower() in _TRUE) == disabled:
            raise ValueError("one_to_one: 'disabled' and 'enabled' contradict each other")
        out = {k: v for k, v in params.items() if k != "disabled"}
        out["enabled"] = "0" if disabled else "1"
        return out
