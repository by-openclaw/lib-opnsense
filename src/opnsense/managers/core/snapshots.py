# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense config snapshot (ZFS boot-environment) manager — ensure() + activate.

API domain: /api/core/snapshots  (ZFS-only; requires a ZFS-root install)
Endpoints:
    search    POST core/snapshots/search           — rows: uuid,name,active,size,created
    create    POST core/snapshots/add   {name}     — create a boot env (no payload key, no uuid)
    delete    POST core/snapshots/del/{uuid}          — destroys a boot environment
    activate  POST core/snapshots/activate/{uuid}     — sets it active for next boot
    supported GET  core/snapshots/isSupported          — ZFS check

This is NOT a standard ApiMutableModelController: `add` takes a bare ``{name}`` (no
payload key) and returns ``{"status":"ok","result":"bootenvironment executed create
successfully"}`` without a uuid, so identity is resolved by ``name`` from ``search``.
Hence a standalone manager (like AuthApiKeyManager), not a BaseManager subclass.

Verified against a live OPNsense 26.7 CE ZFS install (vm-opns-lab-01).
Logging/consumer error-handling contract: see managers/base.py + CLAUDE.md.
"""

from __future__ import annotations

import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class CoreSnapshotManager:
    """Manage OPNsense config snapshots (ZFS boot environments) via /api/core/snapshots.

    Snapshots are point-in-time boot environments — take one before a risky change,
    roll back by activating it and rebooting. ZFS-root only.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = CoreSnapshotManager(client)
            await mgr.ensure("present", "pre-upgrade")   # create if absent (idempotent)
            await mgr.activate("pre-upgrade")            # boot into it next reboot
            await mgr.ensure("absent", "pre-upgrade")    # destroy
    """

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise with an OpnsenseClient."""
        self._client = client

    async def is_supported(self) -> bool:
        """Return True if the install supports snapshots (ZFS root)."""
        try:
            body = await self._client.get("core/snapshots/isSupported")
        except Exception:
            # Some builds return 400 to the bare GET; fall back to a successful search.
            try:
                await self._client.search("core/snapshots/search")
                return True
            except Exception:
                return False
        return str(body.get("status", "")).lower() in ("ok", "1", "true") or bool(
            body.get("supported")
        )

    async def list(self) -> list[dict[str, Any]]:
        """Return all snapshots (rows: uuid, name, active, mountpoint, size, created)."""
        return await self._client.search("core/snapshots/search")

    async def _find(self, name: str) -> dict[str, Any] | None:
        """Return the snapshot row matching ``name``, or None."""
        for row in await self.list():
            if row.get("name") == name:
                return row
        return None

    async def ensure(
        self,
        state: str,
        name: str,
        check_mode: bool = False,
    ) -> EnsureResult:
        """Ensure a snapshot named ``name`` is present or absent (idempotent).

        Args:
            state:      'present' or 'absent'.
            name:       Snapshot / boot-environment name.
            check_mode: If True, report the action without changing anything.

        Returns:
            EnsureResult with action 'created' | 'deleted' | 'noop'.

        Raises:
            OpnsenseError: On API failure (logged then re-raised).
            ValueError:    On an unknown ``state``.
        """
        if state not in ("present", "absent"):
            raise ValueError(f"state must be 'present' or 'absent', got {state!r}")

        existing = await self._find(name)

        if state == "present":
            if existing:
                return EnsureResult(changed=False, action="noop", uuid=existing.get("uuid"))
            if check_mode:
                return EnsureResult(changed=True, action="created", after={"name": name})
            try:
                await self._client.post("core/snapshots/add", {"name": name})
            except Exception:
                logger.error(
                    "snapshot create failed name=%s",
                    name,
                    extra={"action": "created", "changed": True, "snapshot": name},
                )
                raise
            row = await self._find(name)
            logger.info(
                "snapshot created name=%s",
                name,
                extra={"action": "created", "changed": True, "snapshot": name},
            )
            return EnsureResult(
                changed=True,
                action="created",
                uuid=(row or {}).get("uuid"),
                after=row or {"name": name},
            )

        # absent
        if not existing:
            return EnsureResult(changed=False, action="noop")
        if check_mode:
            return EnsureResult(
                changed=True, action="deleted", uuid=existing.get("uuid"), before=existing
            )
        try:
            await self._client.post(f"core/snapshots/del/{existing['uuid']}")
        except Exception:
            logger.error(
                "snapshot delete failed name=%s uuid=%s",
                name,
                existing.get("uuid"),
                extra={"action": "deleted", "changed": True, "snapshot": name},
            )
            raise
        logger.warning(
            "snapshot deleted name=%s uuid=%s",
            name,
            existing.get("uuid"),
            extra={"action": "deleted", "changed": True, "snapshot": name},
        )
        return EnsureResult(
            changed=True, action="deleted", uuid=existing.get("uuid"), before=existing
        )

    async def activate(self, name: str, check_mode: bool = False) -> EnsureResult:
        """Activate the snapshot ``name`` for the next boot.

        Args:
            name:       Snapshot name to activate.
            check_mode: If True, report without changing.

        Returns:
            EnsureResult with action 'updated' (activated) or 'noop' (already active).

        Raises:
            OpnsenseError: On API failure.
            KeyError:      If no snapshot named ``name`` exists.
        """
        existing = await self._find(name)
        if not existing:
            raise KeyError(f"no snapshot named {name!r}")
        # 'active' contains 'N' (next-boot) and/or 'R' (running) flags.
        if "N" in str(existing.get("active", "")):
            return EnsureResult(changed=False, action="noop", uuid=existing.get("uuid"))
        if check_mode:
            return EnsureResult(changed=True, action="updated", uuid=existing["uuid"])
        try:
            await self._client.post(f"core/snapshots/activate/{existing['uuid']}")
        except Exception:
            logger.error("snapshot activate failed name=%s", name, extra={"snapshot": name})
            raise
        logger.info(
            "snapshot activated name=%s",
            name,
            extra={"action": "updated", "changed": True, "snapshot": name},
        )
        return EnsureResult(changed=True, action="updated", uuid=existing["uuid"])
