# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense auth privilege manager — privilege assignment operations.

Privileges are NOT CRUD entities — they are assignment relationships
between users/groups and privilege IDs. This manager does NOT extend
BaseManager.

Endpoints:
    list    GET  auth/priv/get
    get     GET  auth/priv/get_item/{priv_id}
    assign  POST auth/priv/set_item/{priv_id}
    apply   None — auth changes apply immediately

Redact fields: none
Logging: custom (INFO=assign, WARNING=unassign, ERROR=failure)
Safety:  see docs/test-zone-plan.md §M03
"""

from __future__ import annotations

import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class AuthPrivManager:
    """Manage OPNsense privilege assignments for users and groups.

    Unlike AuthUserManager and AuthGroupManager, privileges are not
    standard CRUD resources. They represent assignments (user/group ->
    privilege) and use a different API pattern.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = AuthPrivManager(client)
            result = await mgr.ensure(
                priv_id="page-all",
                target_type="group",
                target_name="admins",
                state="present",
            )

    Input (ensure):
        priv_id:      Privilege identifier, e.g. 'page-all' (required)
        target_type:  Target type — 'user' or 'group' (required)
        target_name:  Name of the user or group (required)
        state:        Desired state — 'present' or 'absent' (optional, default='present')
        check_mode:   Dry-run flag (optional, default=False)

    Output (EnsureResult):
        changed:  bool — True if assignment was modified
        action:   'created' | 'deleted' | 'noop'
        after:    Dict with priv_id, target_type, target_name, state (on change)
    """

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the privilege manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        self._client = client

    async def list_privileges(self) -> list[dict[str, Any]]:
        """List all available privileges.

        Returns:
            List of privilege dicts with id, name, and description fields.
        """
        body = await self._client.get("auth/priv/get")
        # OPNsense returns privileges in various nested structures;
        # normalize to a flat list
        if isinstance(body, dict):
            privs = body.get("rows", body.get("privileges", []))
            if isinstance(privs, list):
                return privs
            # Handle dict-of-dicts format
            if isinstance(privs, dict):
                return [
                    {"id": k, **v} if isinstance(v, dict) else {"id": k, "name": v}
                    for k, v in privs.items()
                ]
        return []

    async def get_assignment(self, priv_id: str) -> dict[str, Any]:
        """Get a specific privilege assignment's details.

        Args:
            priv_id: Privilege identifier (e.g. 'page-all', 'user-shell-access').

        Returns:
            Dict with privilege details including assigned users/groups.
        """
        return await self._client.get(f"auth/priv/get_item/{priv_id}")

    async def ensure(
        self,
        priv_id: str,
        target_type: str,
        target_name: str,
        state: str = "present",
        check_mode: bool = False,
    ) -> EnsureResult:
        """Ensure a privilege is assigned to or unassigned from a target.

        Args:
            priv_id:     Privilege identifier (e.g. 'page-all').
            target_type: Type of target: 'user' or 'group'.
            target_name: Name of the user or group.
            state:       'present' to assign, 'absent' to unassign.
            check_mode:  If True, return what would happen without changes.

        Returns:
            EnsureResult describing what was (or would be) done.

        Raises:
            ValueError: If target_type is not 'user' or 'group'.
            ValueError: If state is not 'present' or 'absent'.
        """
        if target_type not in ("user", "group"):
            raise ValueError(f"Invalid target_type '{target_type}'. Use 'user' or 'group'.")
        if state not in ("present", "absent"):
            raise ValueError(f"Invalid state '{state}'. Use 'present' or 'absent'.")

        # Fetch current assignment to check idempotency
        assignment = await self.get_assignment(priv_id)
        name_to_uuid, assigned_names = self._extract_targets(assignment, target_type)
        is_assigned = target_name in assigned_names

        if state == "present" and is_assigned:
            return EnsureResult(changed=False, action="noop")

        if state == "absent" and not is_assigned:
            return EnsureResult(changed=False, action="noop")

        if check_mode:
            action = "created" if state == "present" else "deleted"
            return EnsureResult(
                changed=True,
                action=action,
                after={
                    "priv_id": priv_id,
                    "target_type": target_type,
                    "target_name": target_name,
                    "state": state,
                },
            )

        # Build the selected UUID set from currently assigned targets
        selected_uuids: set[str] = set()
        for name in assigned_names:
            uuid = name_to_uuid.get(name)
            if uuid:
                selected_uuids.add(uuid)

        # Apply the change — resolve target_name to UUID
        target_uuid = name_to_uuid.get(target_name, target_name)
        if state == "present":
            selected_uuids.add(target_uuid)
        else:
            selected_uuids.discard(target_uuid)

        # POST the updated assignment — OPNsense expects UUIDs
        payload = {
            "priv": {
                f"{target_type}s": ",".join(sorted(selected_uuids)),
            },
        }
        try:
            await self._client.post(f"auth/priv/set_item/{priv_id}", data=payload)
        except Exception as exc:
            logger.error(
                "privilege %s failed: %s %s=%s: %s",
                "assign" if state == "present" else "unassign",
                priv_id,
                target_type,
                target_name,
                exc,
                extra={
                    "action": "priv_failed",
                    "priv_id": priv_id,
                    "target_type": target_type,
                    "target_name": target_name,
                    "error": str(exc),
                },
            )
            raise

        action = "created" if state == "present" else "deleted"
        log_level = logging.INFO if state == "present" else logging.WARNING
        logger.log(
            log_level,
            "privilege %s: %s %s=%s",
            action,
            priv_id,
            target_type,
            target_name,
            extra={
                "action": action,
                "changed": True,
                "priv_id": priv_id,
                "target_type": target_type,
                "target_name": target_name,
                "state": state,
            },
        )
        return EnsureResult(
            changed=True,
            action=action,
            after={
                "priv_id": priv_id,
                "target_type": target_type,
                "target_name": target_name,
                "state": state,
            },
        )

    def _extract_targets(
        self,
        assignment: dict[str, Any],
        target_type: str,
    ) -> tuple[dict[str, str], set[str]]:
        """Extract currently assigned user or group names from a privilege.

        OPNsense 26.1 returns ``{uuid: {selected: "1", value: "name"}}`` for
        both users and groups. The set_item endpoint expects UUIDs, so we
        return both a name→uuid mapping and the set of assigned names.

        Args:
            assignment:  Privilege assignment dict from the API.
            target_type: 'user' or 'group'.

        Returns:
            Tuple of (name_to_uuid mapping, set of assigned names).
        """
        # Navigate into the 'priv' wrapper if present (26.1 format)
        data = assignment.get("priv", assignment)
        key = f"{target_type}s"
        raw = data.get(key, "")

        name_to_uuid: dict[str, str] = {}
        assigned: set[str] = set()

        if isinstance(raw, dict):
            # OPNsense 26.1: {uuid: {selected: 0/1, value: "name"}}
            for uuid_key, v in raw.items():
                if isinstance(v, dict):
                    name = str(v.get("value", v.get("name", uuid_key)))
                    name_to_uuid[name] = uuid_key
                    if v.get("selected") in ("1", 1, True):
                        assigned.add(name)
        elif isinstance(raw, list):
            assigned = set(raw)
        elif isinstance(raw, str) and raw:
            assigned = set(raw.split(","))

        return name_to_uuid, assigned
