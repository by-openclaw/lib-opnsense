# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense routing route manager -- CRUD + ensure().

API domain: /api/routes/routes
Payload key: route
Match keys:  ['network', 'gateway'] (composite)
Entity suffix: Route (searchRoute, getRoute, addRoute, setRoute, delRoute)

Supported endpoints:
    POST /api/routes/routes/searchRoute        -- list routes
    GET  /api/routes/routes/getRoute            -- schema / get by UUID
    POST /api/routes/routes/addRoute            -- create route
    POST /api/routes/routes/setRoute/{uuid}     -- update route
    POST /api/routes/routes/delRoute/{uuid}     -- delete route
    POST /api/routes/routes/reconfigure         -- apply changes

Route fields:
    network   -- destination network (e.g. '10.99.0.0/24')
    gateway   -- gateway UUID or name
    descr     -- description (max 255)
    disabled  -- disabled flag ('0' or '1')  -- firmware up to 26.1
    enabled   -- enabled flag ('0' or '1')   -- firmware 26.7 and later (renamed, inverted)

The manager accepts either flag and sends the one the firmware has (read from the schema), so
a caller written against one firmware keeps working on the other. Before this translation a
route declared ``disabled: '1'`` was created ENABLED on 26.7: the API ignores a field it does
not know, and the diff skips a field the row does not carry.

Route changes require reconfigure to take effect.
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager
from opnsense.models.base import EnsureResult

_TRUE = {"1", "true", "yes", "on"}


class RtRouteManager(BaseManager):
    """Manage OPNsense static routes via /api/routes/routes.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Routes define static routing table entries.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = RtRouteManager(client)
            result = await mgr.ensure("present", {
                "network": "10.99.0.0/24",
                "gateway": "WAN_DHCP",
                "descr": "Test route",
                "disabled": "1",
            })

    Input (ensure present):
        network:   Destination network CIDR, e.g. '10.99.0.0/24' (required)
        gateway:   Gateway UUID or name (required)
        descr:     Description, max 255 (optional)
        disabled:  Disable route (optional, default='0')

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "routes/routes"
    _payload_key = "route"
    _entity_suffix = "Route"
    _apply_endpoint = "routes/routes/reconfigure"
    _match_keys = ["network", "gateway"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "network": {"type": "str", "required": True},
        "gateway": {"type": "str", "required": True},
        "descr": {"type": "str", "max_length": 255},
        "disabled": {"type": "bool_str"},
        "enabled": {"type": "bool_str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the routing route manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
        self._enable_field: str | None = None  # the flag this firmware has, read once

    async def ensure(
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
        uuid: str | None = None,
        dedupe: bool = False,
        force_update: bool = False,
    ) -> EnsureResult:
        """Ensure the route, with the enable flag translated to this firmware's field.

        Args:
            state:        ``'present'`` or ``'absent'``.
            params:       Route parameters; ``disabled`` or ``enabled`` (not both, unless
                          they agree).
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
            await self._device_enable_flag(params),
            check_mode=check_mode,
            uuid=uuid,
            dedupe=dedupe,
            force_update=force_update,
        )

    async def create(self, params: dict[str, Any], check_mode: bool = False) -> EnsureResult:
        """Create a route, with the enable flag under this firmware's field.

        Args:
            params:     Route field values.
            check_mode: If True, report without changing anything.

        Returns:
            ``EnsureResult`` with ``action='created'``.
        """
        return await super().create(await self._device_enable_flag(params), check_mode=check_mode)

    async def update(
        self,
        uuid: str,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Update a route, with the enable flag under this firmware's field.

        Args:
            uuid:       Route UUID.
            params:     Route field values.
            check_mode: If True, report without changing anything.

        Returns:
            ``EnsureResult`` with ``action='updated'``.
        """
        return await super().update(
            uuid, await self._device_enable_flag(params), check_mode=check_mode
        )

    async def _device_enable_flag(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return ``params`` with the enable flag under the field this firmware has."""
        has_disabled, has_enabled = "disabled" in params, "enabled" in params
        if not has_disabled and not has_enabled:
            return params
        disabled = str(params["disabled"]).lower() in _TRUE if has_disabled else None
        enabled = str(params["enabled"]).lower() in _TRUE if has_enabled else None
        if disabled is not None and enabled is not None and disabled == enabled:
            raise ValueError("route: 'disabled' and 'enabled' contradict each other")
        if self._enable_field is None:
            schema = await self.get_schema()
            # Positive detection only: anything that is not a schema with `enabled`
            # keeps the historical field.
            self._enable_field = (
                "enabled" if isinstance(schema, dict) and "enabled" in schema else "disabled"
            )
        is_enabled = enabled if enabled is not None else not disabled
        out = {k: v for k, v in params.items() if k not in ("disabled", "enabled")}
        if self._enable_field == "enabled":
            out["enabled"] = "1" if is_enabled else "0"
        else:
            out["disabled"] = "0" if is_enabled else "1"
        return out
