# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Base manager — thin orchestrator composing core/ components.

Provides the full CRUD + ensure() lifecycle by delegating to:
    - core/identity.py    — IdentityResolver (match keys + find_existing)
    - core/diff.py        — DiffEngine (state comparison)
    - core/redaction.py   — Redactor (field redaction)
    - core/validation.py  — ValidatorRegistry (field validation)
    - core/endpoint.py    — EndpointResolver (URL construction)
    - core/logging_helpers.py — ManagerLogBuilder (structured log dicts)

Logging contract — every ensure() outcome logs these fields
(designed for Ansible -vvvvvv compatibility):

+-----------------+-------+------+--------+-------+---------+-------------+
| Log site        | match | uuid | before | after | changed | duration_ms |
+-----------------+-------+------+--------+-------+---------+-------------+
| create chk_mode |  yes  |  --  |   --   |  yes  |   yes   |     yes     |
| created         |  yes  | yes  |   --   |  yes  |   yes   |     yes     |
| update chk_mode |  yes  | yes  |  yes   |  yes  |   yes   |     yes     |
| updated         |  yes  | yes  |  yes   |  yes  |   yes   |     yes     |
| delete chk_mode |  yes  | yes  |  yes   |  --   |   yes   |     yes     |
| deleted         |  yes  | yes  |  yes   |  --   |   yes   |     yes     |
| noop            |  yes  | yes  |   --   |  --   |   yes   |     yes     |
| error (all)     |  yes  | yes* |  yes*  |  --   |   --    |     yes     |
+-----------------+-------+------+--------+-------+---------+-------------+
* = when available

Severity: DEBUG=noop, INFO=create/update, WARNING=delete, ERROR=failure.
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.core.diff import DiffEngine
from opnsense.core.endpoint import EndpointConfig, EndpointResolver
from opnsense.core.identity import IdentityResolver
from opnsense.core.logging_helpers import ManagerLogBuilder
from opnsense.core.redaction import Redactor
from opnsense.core.validation import ValidatorRegistry
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)

# Shared instances — stateless, safe to reuse across managers
_diff_engine = DiffEngine()
_redactor = Redactor()
_validator_registry = ValidatorRegistry()


class BaseManager(ABC):
    """Abstract base for all OPNsense API managers.

    Subclasses must set:
        _endpoint:       API domain path (e.g. 'auth/user')
        _payload_key:    Top-level JSON key for payloads (e.g. 'user')
        _apply_endpoint: Reconfigure endpoint, or None if changes are immediate

    Identity — set ONE of:
        _match_key:      Single field name (e.g. 'name'). Legacy, for API-enforced unique fields.
        _match_keys:     List of fields forming composite identity (e.g. ['tag', 'if']).
                         Preferred for all new managers. Raises AmbiguousMatchError on >1 match.

    Subclasses may override:
        REDACT_FIELDS:   Set of field names to redact in results/logs (Loki)
        _entity_suffix:  Suffix appended to CRUD action names in endpoint URLs.
                         Default: capitalized _payload_key (e.g. 'Item', 'Rule').
                         Set to '' for controllers that use bare names
                         (e.g. auth/user uses 'search' not 'searchUser').
    """

    _endpoint: str
    _payload_key: str
    _apply_endpoint: str | None
    _match_key: str | None = None  # Legacy single key
    _match_keys: list[str] | None = None  # Composite identity (preferred)
    _entity_suffix: str | None = None  # None = auto from _payload_key
    _validators: dict[str, dict[str, Any]] = {}  # Field validators per manager
    _apply_timeout: int | None = None  # Per-manager apply timeout override (seconds)

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager with an OpnsenseClient.

        Args:
            client: An :class:`OpnsenseClient` instance (may be used as context manager).
        """
        self._client = client

        # Resolve composite match keys
        match_keys = self._match_keys or ([self._match_key] if self._match_key else None)
        if not match_keys:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define _match_key or _match_keys"
            )

        # Build core components
        self._identity = IdentityResolver(
            match_keys=match_keys,
            endpoint=self._endpoint,
            manager_name=self.__class__.__name__,
        )
        self._endpoints = EndpointResolver(
            EndpointConfig(
                base=self._endpoint,
                payload_key=self._payload_key,
                entity_suffix=self._entity_suffix,
                apply_endpoint=self._apply_endpoint,
            )
        )

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
        try:
            return await self._client.search(self._endpoints.search(), search_phrase=search_phrase)
        except Exception as exc:
            logger.error(
                "list failed %s: %s",
                self._endpoint,
                exc,
                extra={"action": "list_failed", "endpoint": self._endpoint, "error": str(exc)},
            )
            raise

    async def get(self, uuid: str) -> dict[str, Any]:
        """Get a single resource by UUID.

        Args:
            uuid: Resource UUID.

        Returns:
            Resource dict (the inner payload, unwrapped from payload_key).
        """
        try:
            body = await self._client.get(self._endpoints.get(uuid))
        except Exception as exc:
            logger.error(
                "get failed %s uuid=%s: %s",
                self._endpoint,
                uuid,
                exc,
                extra={
                    "action": "get_failed",
                    "endpoint": self._endpoint,
                    "uuid": uuid,
                    "error": str(exc),
                },
            )
            raise
        return body.get(self._payload_key, body)

    async def get_schema(self) -> dict[str, Any]:
        """Get the empty schema for this resource type.

        Returns:
            Schema dict showing available fields and defaults.
        """
        try:
            body = await self._client.get(self._endpoints.get())
        except Exception as exc:
            logger.error(
                "get_schema failed %s: %s",
                self._endpoint,
                exc,
                extra={
                    "action": "get_schema_failed",
                    "endpoint": self._endpoint,
                    "error": str(exc),
                },
            )
            raise
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
        log = ManagerLogBuilder()
        label = self._identity.match_label(params)
        match_fields = self._identity.match_log_fields(params)
        redacted_after = _redactor.redact_dict(params, redact_fields=self.REDACT_FIELDS)

        if check_mode:
            logger.info(
                "create check_mode=True %s",
                label,
                extra=log.build_extra(
                    "created",
                    match_fields,
                    after=redacted_after,
                    changed=True,
                    check_mode=True,
                ),
            )
            return EnsureResult(changed=True, action="created", after=redacted_after)

        try:
            uuid = await self._client.create(self._endpoints.add(), self._payload_key, params)
            await self._apply()
        except Exception as exc:
            logger.error(
                "create failed %s: %s",
                label,
                exc,
                extra=log.build_extra(
                    "create_failed",
                    match_fields,
                    error=str(exc),
                ),
            )
            raise

        logger.info(
            "created %s uuid=%s",
            label,
            uuid,
            extra=log.build_extra(
                "created",
                match_fields,
                uuid=uuid,
                after=redacted_after,
                changed=True,
            ),
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
        log = ManagerLogBuilder()
        label = self._identity.match_label(params)
        match_fields = self._identity.match_log_fields(params)
        before = await self.get(uuid)
        redacted_before = _redactor.redact_dict(before, redact_fields=self.REDACT_FIELDS)
        redacted_after = _redactor.redact_dict(params, redact_fields=self.REDACT_FIELDS)

        if check_mode:
            logger.info(
                "update check_mode=True %s uuid=%s",
                label,
                uuid,
                extra=log.build_extra(
                    "updated",
                    match_fields,
                    uuid=uuid,
                    before=redacted_before,
                    after=redacted_after,
                    changed=True,
                    check_mode=True,
                ),
            )
            return EnsureResult(
                changed=True,
                action="updated",
                uuid=uuid,
                before=redacted_before,
                after=redacted_after,
            )

        try:
            await self._client.update(self._endpoints.set(), uuid, self._payload_key, params)
            await self._apply()
        except Exception as exc:
            logger.error(
                "update failed %s uuid=%s: %s",
                label,
                uuid,
                exc,
                extra=log.build_extra(
                    "update_failed",
                    match_fields,
                    uuid=uuid,
                    before=redacted_before,
                    error=str(exc),
                ),
            )
            raise

        logger.info(
            "updated %s uuid=%s",
            label,
            uuid,
            extra=log.build_extra(
                "updated",
                match_fields,
                uuid=uuid,
                before=redacted_before,
                after=redacted_after,
                changed=True,
            ),
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
        log = ManagerLogBuilder()
        before = await self.get(uuid)
        label = self._identity.match_label(before)
        match_fields = self._identity.match_log_fields(before)
        redacted_before = _redactor.redact_dict(before, redact_fields=self.REDACT_FIELDS)

        if check_mode:
            logger.warning(
                "delete check_mode=True %s uuid=%s",
                label,
                uuid,
                extra=log.build_extra(
                    "deleted",
                    match_fields,
                    uuid=uuid,
                    before=redacted_before,
                    changed=True,
                    check_mode=True,
                ),
            )
            return EnsureResult(
                changed=True,
                action="deleted",
                uuid=uuid,
                before=redacted_before,
            )

        try:
            await self._client.delete(self._endpoints.delete(), uuid)
            await self._apply()
        except Exception as exc:
            logger.error(
                "delete failed %s uuid=%s: %s",
                label,
                uuid,
                exc,
                extra=log.build_extra(
                    "delete_failed",
                    match_fields,
                    uuid=uuid,
                    before=redacted_before,
                    error=str(exc),
                ),
            )
            raise

        logger.warning(
            "deleted %s uuid=%s",
            label,
            uuid,
            extra=log.build_extra(
                "deleted",
                match_fields,
                uuid=uuid,
                before=redacted_before,
                changed=True,
            ),
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
        uuid: str | None = None,
    ) -> EnsureResult:
        """Ensure a resource matches desired state — full idempotent lifecycle.

        Mirrors Ansible state semantics:
            state="present" -> create if missing, update if drifted, noop if matching
            state="absent"  -> delete if exists, noop if already gone

        Args:
            state:      Desired state: 'present' or 'absent'.
            params:     Resource parameters (must include all _match_keys fields).
            check_mode: If True, return what would happen without making changes.
            uuid:       Optional UUID — bypasses _find_existing. Use when UUID is
                        known (e.g. after AmbiguousMatchError, or out-of-band creation).

        Returns:
            EnsureResult describing what was (or would be) done.

        Raises:
            ValueError: If state is not 'present' or 'absent'.
            FieldValidationError: If any field fails client-side validation.
            AmbiguousMatchError: If multiple resources match the composite keys.
        """
        if state not in ("present", "absent"):
            raise ValueError(f"Invalid state '{state}'. Use 'present' or 'absent'.")

        # Client-side validation — reject bad params before any API call
        if self._validators and state == "present":
            try:
                _validator_registry.validate_params(params, self._validators)
            except Exception as exc:
                logger.error(
                    "validation failed %s: %s",
                    self.__class__.__name__,
                    exc,
                    extra={
                        "action": "validation_failed",
                        "endpoint": self._endpoint,
                        "error": str(exc),
                    },
                )
                raise

        log = ManagerLogBuilder()
        label = self._identity.match_label(params)
        match_fields = self._identity.match_log_fields(params)

        # Resolve existing resource — by UUID or by composite match keys
        existing: dict[str, Any] | None
        if uuid is not None:
            existing = await self.get(uuid)
            existing["uuid"] = uuid
        else:
            existing = await self._identity.find_existing(params, self.list)

        if state == "present":
            if existing is None:
                return await self.create(params, check_mode=check_mode)

            # Resource exists — check for drift
            existing_uuid = existing.get("uuid", "")
            diff = _diff_engine.compute_diff(existing, params)

            if diff is None:
                logger.debug(
                    "noop %s uuid=%s — state matches",
                    label,
                    existing_uuid,
                    extra=log.build_extra(
                        "noop",
                        match_fields,
                        uuid=existing_uuid,
                        changed=False,
                    ),
                )
                return EnsureResult(changed=False, action="noop", uuid=existing_uuid)

            return await self.update(existing_uuid, params, check_mode=check_mode)

        # state == "absent"
        if existing is None:
            logger.debug(
                "noop %s — already absent",
                label,
                extra=log.build_extra("noop", match_fields, changed=False),
            )
            return EnsureResult(changed=False, action="noop")

        existing_uuid = existing.get("uuid", "")
        return await self.delete(existing_uuid, check_mode=check_mode)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _apply(self) -> None:
        """Trigger reconfigure if _apply_endpoint is set.

        Some OPNsense modules require an explicit reconfigure call to
        apply CRUD changes to the running configuration. Auth endpoints
        apply immediately and set _apply_endpoint = None.

        Uses ``_apply_timeout`` if set on the concrete manager — slow endpoints
        like ``firewall/filter/apply`` or ``unbound/service/reconfigure`` may
        need 60-120s instead of the global default.
        """
        apply_ep = self._endpoints.apply()
        if apply_ep is not None:
            try:
                await self._client.reconfigure(apply_ep, timeout=self._apply_timeout)
            except Exception as exc:
                logger.error(
                    "apply failed %s: %s",
                    apply_ep,
                    exc,
                    extra={
                        "action": "apply_failed",
                        "endpoint": apply_ep,
                        "error": str(exc),
                    },
                )
                raise
