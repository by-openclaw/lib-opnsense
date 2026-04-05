# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense auth privilege manager — privilege assignment operations.

Privileges are NOT CRUD entities — they are assignment relationships
between users/groups and privilege IDs. This manager does NOT extend
BaseManager.

API domain: /api/auth/priv
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.models.base import EnsureResult


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
        assigned_targets = self._extract_targets(assignment, target_type)
        is_assigned = target_name in assigned_targets

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

        # Apply the change
        if state == "present":
            assigned_targets.add(target_name)
        else:
            assigned_targets.discard(target_name)

        # POST the updated assignment
        payload = {
            "priv": priv_id,
            f"{target_type}s": ",".join(sorted(assigned_targets)),
        }
        await self._client.post(f"auth/priv/set_item/{priv_id}", data=payload)

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

    def _extract_targets(
        self,
        assignment: dict[str, Any],
        target_type: str,
    ) -> set[str]:
        """Extract currently assigned user or group names from a privilege.

        Args:
            assignment:  Privilege assignment dict from the API.
            target_type: 'user' or 'group'.

        Returns:
            Set of target names currently assigned to this privilege.
        """
        key = f"{target_type}s"
        raw = assignment.get(key, "")

        if isinstance(raw, list):
            return set(raw)
        if isinstance(raw, dict):
            # OPNsense sometimes returns {uuid: {selected: "1", value: "name"}}
            return {
                str(v.get("value", v.get("name", k)))
                for k, v in raw.items()
                if isinstance(v, dict) and v.get("selected") in ("1", 1, True)
            }
        if isinstance(raw, str) and raw:
            return set(raw.split(","))
        return set()
