# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Base manager — abstract class for OPNsense API domain managers.

Provides the full CRUD + ensure() lifecycle with:
- Idempotent ensure() using fetch-diff-noop semantics
- check_mode (dry_run) support on all destructive methods
- Field redaction for sensitive data in logs/results
- Automatic reconfigure after mutations (when _apply_endpoint is set)

Logging contract — every ensure() outcome logs these fields
(designed for Ansible -vvvvvv compatibility):

+-----------------+-------+-------+------+--------+-------+---------+-------------+
| Log site        | match | match | uuid | before | after | changed | duration_ms |
|                 | field | value |      |        |       |         |             |
+-----------------+-------+-------+------+--------+-------+---------+-------------+
| create chk_mode |  yes  |  yes  |  --  |   --   |  yes  |   yes   |     yes     |
| created         |  yes  |  yes  | yes  |   --   |  yes  |   yes   |     yes     |
| update chk_mode |  yes  |  yes  | yes  |  yes   |  yes  |   yes   |     yes     |
| updated         |  yes  |  yes  | yes  |  yes   |  yes  |   yes   |     yes     |
| delete chk_mode |  yes  |  yes  | yes  |  yes   |  --   |   yes   |     yes     |
| deleted         |  yes  |  yes  | yes  |  yes   |  --   |   yes   |     yes     |
| noop            |  yes  |  yes  | yes  |   --   |  --   |   yes   |     yes     |
| error (all)     |  yes  |  yes  | yes* |  yes*  |  --   |   --    |     yes     |
+-----------------+-------+-------+------+--------+-------+---------+-------------+
* = when available

Severity: DEBUG=noop, INFO=create/update, WARNING=delete, ERROR=failure.
"""

from __future__ import annotations

import copy
import logging
import time
from abc import ABC
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class BaseManager(ABC):
    """Abstract base for all OPNsense API managers.

    Subclasses must set:
        _endpoint:       API domain path (e.g. 'auth/user')
        _payload_key:    Top-level JSON key for payloads (e.g. 'user')
        _apply_endpoint: Reconfigure endpoint, or None if changes are immediate
        _match_key:      Field name used to match existing resources (e.g. 'name')

    Subclasses may override:
        REDACT_FIELDS:   Set of field names to redact in results/logs
        _entity_suffix:  Suffix appended to CRUD action names in endpoint URLs.
                         Default: capitalized _payload_key (e.g. 'Item', 'Rule').
                         Set to '' for controllers that use bare names
                         (e.g. auth/user uses 'search' not 'searchUser').
    """

    _endpoint: str
    _payload_key: str
    _apply_endpoint: str | None
    _match_key: str
    _entity_suffix: str | None = None  # None = auto from _payload_key

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager with an OpnsenseClient.

        Args:
            client: An :class:`OpnsenseClient` instance (may be used as context manager).
        """
        self._client = client

    # ------------------------------------------------------------------
    # Endpoint helpers
    # ------------------------------------------------------------------

    @property
    def _suffix(self) -> str:
        """Resolve entity suffix for endpoint URLs.

        Returns the _entity_suffix if explicitly set, otherwise capitalizes
        _payload_key. Set _entity_suffix = '' for controllers using bare
        action names (e.g. auth/user/search instead of auth/user/searchUser).
        """
        if self._entity_suffix is not None:
            return self._entity_suffix
        return self._payload_key.capitalize()

    # ------------------------------------------------------------------
    # Public CRUD methods
    # ------------------------------------------------------------------

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List resources matching an optional search phrase.

        Args:
            search_phrase: Filter string passed to the OPNsense search API.

        Returns:
            List of resource dicts.
        """
        endpoint = f"{self._endpoint}/search{self._suffix}"
        return await self._client.search(endpoint, search_phrase=search_phrase)

    async def get(self, uuid: str) -> dict[str, Any]:
        """Get a single resource by UUID.

        Args:
            uuid: Resource UUID.

        Returns:
            Resource dict (the inner payload, unwrapped from payload_key).
        """
        endpoint = f"{self._endpoint}/get{self._suffix}/{uuid}"
        body = await self._client.get(endpoint)
        return body.get(self._payload_key, body)

    async def get_schema(self) -> dict[str, Any]:
        """Get the empty schema for this resource type.

        Returns:
            Schema dict showing available fields and defaults.
        """
        endpoint = f"{self._endpoint}/get{self._suffix}"
        body = await self._client.get(endpoint)
        return body.get(self._payload_key, body)

    async def create(
        self,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Create a new resource.

        Args:
            params:     Resource field values.
            check_mode: If True, return what would happen without making changes.

        Returns:
            EnsureResult with action='created'.
        """
        t0 = time.monotonic()
        match_val = params.get(self._match_key, "")
        redacted_after = self._redact(params)
        if check_mode:
            logger.info(
                "create check_mode=True %s=%s",
                self._match_key,
                match_val,
                extra={
                    "action": "created",
                    "check_mode": True,
                    "changed": True,
                    "match_field": self._match_key,
                    "match_value": match_val,
                    "endpoint": self._endpoint,
                    "after": redacted_after,
                    "duration_ms": round((time.monotonic() - t0) * 1000, 1),
                },
            )
            return EnsureResult(
                changed=True,
                action="created",
                after=redacted_after,
            )

        endpoint = f"{self._endpoint}/add{self._suffix}"
        try:
            uuid = await self._client.create(endpoint, self._payload_key, params)
            await self._apply()
        except Exception as exc:
            logger.error(
                "create failed %s=%s: %s",
                self._match_key,
                match_val,
                exc,
                extra={
                    "action": "create_failed",
                    "match_field": self._match_key,
                    "match_value": match_val,
                    "endpoint": self._endpoint,
                    "error": str(exc),
                    "duration_ms": round((time.monotonic() - t0) * 1000, 1),
                },
            )
            raise

        logger.info(
            "created %s=%s uuid=%s",
            self._match_key,
            match_val,
            uuid,
            extra={
                "action": "created",
                "changed": True,
                "uuid": uuid,
                "match_field": self._match_key,
                "match_value": match_val,
                "endpoint": self._endpoint,
                "after": redacted_after,
                "duration_ms": round((time.monotonic() - t0) * 1000, 1),
            },
        )
        return EnsureResult(
            changed=True,
            action="created",
            uuid=uuid,
            after=redacted_after,
        )

    async def update(
        self,
        uuid: str,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Update an existing resource.

        Args:
            uuid:       Resource UUID.
            params:     Fields to update.
            check_mode: If True, return what would happen without making changes.

        Returns:
            EnsureResult with action='updated'.
        """
        t0 = time.monotonic()
        before = await self.get(uuid)
        redacted_before = self._redact(before)
        redacted_after = self._redact(params)

        if check_mode:
            logger.info(
                "update check_mode=True %s uuid=%s",
                self._endpoint,
                uuid,
                extra={
                    "action": "updated",
                    "check_mode": True,
                    "changed": True,
                    "uuid": uuid,
                    "match_field": self._match_key,
                    "match_value": params.get(self._match_key, ""),
                    "endpoint": self._endpoint,
                    "before": redacted_before,
                    "after": redacted_after,
                    "duration_ms": round((time.monotonic() - t0) * 1000, 1),
                },
            )
            return EnsureResult(
                changed=True,
                action="updated",
                uuid=uuid,
                before=redacted_before,
                after=redacted_after,
            )

        endpoint = f"{self._endpoint}/set{self._suffix}"
        try:
            await self._client.update(endpoint, uuid, self._payload_key, params)
            await self._apply()
        except Exception as exc:
            logger.error(
                "update failed %s uuid=%s: %s",
                self._endpoint,
                uuid,
                exc,
                extra={
                    "action": "update_failed",
                    "uuid": uuid,
                    "match_field": self._match_key,
                    "match_value": params.get(self._match_key, ""),
                    "endpoint": self._endpoint,
                    "error": str(exc),
                    "before": redacted_before,
                    "duration_ms": round((time.monotonic() - t0) * 1000, 1),
                },
            )
            raise

        logger.info(
            "updated %s uuid=%s",
            self._endpoint,
            uuid,
            extra={
                "action": "updated",
                "changed": True,
                "uuid": uuid,
                "match_field": self._match_key,
                "match_value": params.get(self._match_key, ""),
                "endpoint": self._endpoint,
                "before": redacted_before,
                "after": redacted_after,
                "duration_ms": round((time.monotonic() - t0) * 1000, 1),
            },
        )
        return EnsureResult(
            changed=True,
            action="updated",
            uuid=uuid,
            before=redacted_before,
            after=redacted_after,
        )

    async def delete(
        self,
        uuid: str,
        check_mode: bool = False,
    ) -> EnsureResult:
        """Delete a resource by UUID.

        Args:
            uuid:       Resource UUID.
            check_mode: If True, return what would happen without making changes.

        Returns:
            EnsureResult with action='deleted'.
        """
        t0 = time.monotonic()
        before = await self.get(uuid)
        redacted_before = self._redact(before)

        if check_mode:
            logger.warning(
                "delete check_mode=True %s uuid=%s",
                self._endpoint,
                uuid,
                extra={
                    "action": "deleted",
                    "check_mode": True,
                    "changed": True,
                    "uuid": uuid,
                    "match_field": self._match_key,
                    "match_value": before.get(self._match_key, ""),
                    "endpoint": self._endpoint,
                    "before": redacted_before,
                    "duration_ms": round((time.monotonic() - t0) * 1000, 1),
                },
            )
            return EnsureResult(
                changed=True,
                action="deleted",
                uuid=uuid,
                before=redacted_before,
            )

        endpoint = f"{self._endpoint}/del{self._suffix}"
        try:
            await self._client.delete(endpoint, uuid)
            await self._apply()
        except Exception as exc:
            logger.error(
                "delete failed %s uuid=%s: %s",
                self._endpoint,
                uuid,
                exc,
                extra={
                    "action": "delete_failed",
                    "uuid": uuid,
                    "match_field": self._match_key,
                    "match_value": before.get(self._match_key, ""),
                    "endpoint": self._endpoint,
                    "error": str(exc),
                    "before": redacted_before,
                    "duration_ms": round((time.monotonic() - t0) * 1000, 1),
                },
            )
            raise

        logger.warning(
            "deleted %s uuid=%s",
            self._endpoint,
            uuid,
            extra={
                "action": "deleted",
                "changed": True,
                "uuid": uuid,
                "match_field": self._match_key,
                "match_value": before.get(self._match_key, ""),
                "endpoint": self._endpoint,
                "before": redacted_before,
                "duration_ms": round((time.monotonic() - t0) * 1000, 1),
            },
        )
        return EnsureResult(
            changed=True,
            action="deleted",
            uuid=uuid,
            before=redacted_before,
        )

    async def ensure(
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
    ) -> EnsureResult:
        """Ensure a resource matches desired state — full idempotent lifecycle.

        Mirrors Ansible state semantics:
            state="present" -> create if missing, update if drifted, noop if matching
            state="absent"  -> delete if exists, noop if already gone

        Args:
            state:      Desired state: 'present' or 'absent'.
            params:     Resource parameters (must include _match_key field).
            check_mode: If True, return what would happen without making changes.

        Returns:
            EnsureResult describing what was (or would be) done.

        Raises:
            ValueError: If state is not 'present' or 'absent'.
        """
        if state not in ("present", "absent"):
            raise ValueError(f"Invalid state '{state}'. Use 'present' or 'absent'.")

        t0 = time.monotonic()
        existing = await self._find_existing(params)

        if state == "present":
            if existing is None:
                return await self.create(params, check_mode=check_mode)

            # Resource exists — check for drift
            existing_uuid = existing.get("uuid", "")
            diff = self._compute_diff(existing, params)

            if diff is None:
                logger.debug(
                    "noop %s=%s uuid=%s — state matches",
                    self._match_key,
                    params.get(self._match_key),
                    existing_uuid,
                    extra={
                        "action": "noop",
                        "changed": False,
                        "uuid": existing_uuid,
                        "match_field": self._match_key,
                        "match_value": params.get(self._match_key),
                        "endpoint": self._endpoint,
                        "duration_ms": round((time.monotonic() - t0) * 1000, 1),
                    },
                )
                return EnsureResult(changed=False, action="noop", uuid=existing_uuid)

            return await self.update(existing_uuid, params, check_mode=check_mode)

        # state == "absent"
        if existing is None:
            logger.debug(
                "noop %s=%s — already absent",
                self._match_key,
                params.get(self._match_key),
                extra={
                    "action": "noop",
                    "changed": False,
                    "match_field": self._match_key,
                    "match_value": params.get(self._match_key),
                    "endpoint": self._endpoint,
                    "duration_ms": round((time.monotonic() - t0) * 1000, 1),
                },
            )
            return EnsureResult(changed=False, action="noop")

        existing_uuid = existing.get("uuid", "")
        return await self.delete(existing_uuid, check_mode=check_mode)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _find_existing(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Search for an existing resource by _match_key.

        Args:
            params: Parameters containing the _match_key field to search for.

        Returns:
            The matching resource dict (with 'uuid' key), or None.
        """
        match_value = params.get(self._match_key, "")
        if not match_value:
            return None

        rows = await self.list(search_phrase=str(match_value))
        for row in rows:
            if row.get(self._match_key) == match_value:
                return row
        return None

    def _compute_diff(
        self,
        current: dict[str, Any],
        desired: dict[str, Any],
    ) -> dict[str, str] | None:
        """Compare current state against desired and return changed fields.

        Only compares fields present in ``desired`` — extra fields in
        ``current`` are ignored (OPNsense returns many computed fields).

        Args:
            current: Current resource state from the API.
            desired: Desired resource parameters.

        Returns:
            Dict of field: desired_value for fields that differ, or None
            if no changes are needed.
        """
        diff: dict[str, str] = {}
        for key, desired_value in desired.items():
            current_value = current.get(key)
            # Skip fields not present in the current search row —
            # search results are a subset of fields; missing fields
            # do not indicate drift.
            if current_value is None and key not in current:
                continue
            # Normalize OPNsense enum dicts for comparison.
            # Format 1: {"selected": "1"} — simple selected value
            # Format 2: {"lan": {"value": "LAN", "selected": 1}, ...} — enum dict
            if isinstance(current_value, dict):
                if "selected" in current_value:
                    current_value = current_value.get("selected", "")
                else:
                    # Enum dict: find the key with selected=1
                    for opt_key, opt_val in current_value.items():
                        if isinstance(opt_val, dict) and opt_val.get("selected") in (1, "1", True):
                            current_value = opt_key
                            break
            if str(current_value) != str(desired_value):
                diff[key] = str(desired_value)
        return diff if diff else None

    def _redact(self, data: dict[str, Any]) -> dict[str, Any]:
        """Deep-redact REDACT_FIELDS from a data dict.

        Returns a new dict with sensitive field values replaced by
        ``<REDACTED:{field_name}>``.

        Args:
            data: Resource data dict to redact.

        Returns:
            A copy of the dict with sensitive fields redacted.
        """
        if not self.REDACT_FIELDS:
            return data

        redacted = copy.deepcopy(data)
        for key in self.REDACT_FIELDS:
            if key in redacted:
                redacted[key] = f"<REDACTED:{key}>"
        return redacted

    async def _apply(self) -> None:
        """Trigger reconfigure if _apply_endpoint is set.

        Some OPNsense modules require an explicit reconfigure call to
        apply CRUD changes to the running configuration. Auth endpoints
        apply immediately and set _apply_endpoint = None.
        """
        if self._apply_endpoint is not None:
            await self._client.reconfigure(self._apply_endpoint)
