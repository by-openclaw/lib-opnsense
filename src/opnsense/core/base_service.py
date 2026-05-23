# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Service controller base — idempotent service control for OPNsense daemons.

Many OPNsense modules expose a service controller at ``{module}/service/*``
with ``status``, ``start``, ``stop``, ``restart``, ``reconfigure`` endpoints.
There is no CRUD, no UUID — it controls a daemon's lifecycle. Examples:
``dnsmasq/service``, ``radvd/service``, ``unbound/service``, ``kea/service``,
``ids/service``, ``wireguard/service``, ``ipsec/service``, ``syslog/service``.

This module supplies the missing pattern: read status, decide whether action
is required to reach the target state, perform the action only if needed —
true idempotency on a binary state machine.

Target states for ``ensure(state=...)``:

- ``'running'``      — start if not running, noop otherwise
- ``'stopped'``      — stop if running, noop otherwise
- ``'reconfigured'`` — always reconfigure (no noop semantics — caller explicitly
                       wants the daemon to re-read its config)

Logging contract — every ``ensure()`` outcome logs ``before`` / ``after`` /
``changed`` / ``duration_ms`` per ADR ``lib/python/0001 §8``.

Severity: DEBUG=noop, INFO=start/reconfigure, WARNING=stop, ERROR=failure.

See: ADR ``lib/python/0001-design-standard.md``, epic
``https://github.com/by-openclaw/lib-opnsense/issues/65``.
"""

from __future__ import annotations

import logging
from abc import ABC

from opnsense.client import OpnsenseClient
from opnsense.core.logging_helpers import ManagerLogBuilder
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)

# Status values that mean "the daemon is up and serving".
# OPNsense returns 'running' on actively-serving services. Other values
# observed in the wild: 'stopped', 'disabled', 'unknown'.
_RUNNING_STATES: frozenset[str] = frozenset({"running"})
_STOPPED_STATES: frozenset[str] = frozenset({"stopped", "disabled", "unknown"})


class BaseServiceManager(ABC):
    """Abstract base for OPNsense service controllers.

    INPUT (subclass declarations):
        _endpoint:      Service controller path (e.g. ``'dnsmasq/service'``).
        _apply_timeout: Optional per-call timeout for slow reconfigures (seconds).

    OUTPUT (``EnsureResult``):
        changed:  True if the service state was modified.
        action:   ``'started'`` | ``'stopped'`` | ``'restarted'`` |
                  ``'reconfigured'`` | ``'noop'``.
        uuid:     Always ``None`` (services have no UUID).
        before:   ``{'status': '<previous>'}`` dict (one-key for log symmetry).
        after:    ``{'status': '<current>'}`` dict.

    Valid ``ensure()`` states:
        ``'running'``      — start if not running
        ``'stopped'``      — stop if running
        ``'reconfigured'`` — always reconfigure (no idempotency on this action)
    """

    _endpoint: str
    _apply_timeout: int | None = None

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the service manager with an OpnsenseClient.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        self._client = client

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def status(self) -> str:
        """Fetch the current service status string.

        Returns:
            The ``'status'`` field from the API response. Common values:
            ``'running'``, ``'stopped'``, ``'disabled'``, ``'unknown'``.
        """
        try:
            body = await self._client.get(f"{self._endpoint}/status")
        except Exception as exc:
            logger.error(
                "status failed %s: %s",
                self._endpoint,
                exc,
                extra={
                    "action": "status_failed",
                    "endpoint": self._endpoint,
                    "error": str(exc),
                },
            )
            raise
        return str(body.get("status", "unknown"))

    async def start(self, check_mode: bool = False) -> EnsureResult:
        """Start the service unconditionally (not idempotent — use ``ensure``)."""
        return await self._action("start", "started", check_mode)

    async def stop(self, check_mode: bool = False) -> EnsureResult:
        """Stop the service unconditionally (not idempotent — use ``ensure``)."""
        return await self._action("stop", "stopped", check_mode)

    async def restart(self, check_mode: bool = False) -> EnsureResult:
        """Restart the service unconditionally."""
        return await self._action("restart", "restarted", check_mode)

    async def reconfigure(self, check_mode: bool = False) -> EnsureResult:
        """Tell the service to re-read its config without a full restart."""
        return await self._action("reconfigure", "reconfigured", check_mode)

    async def ensure(
        self,
        state: str,
        check_mode: bool = False,
    ) -> EnsureResult:
        """Ensure the service is in the target state.

        Args:
            state:      ``'running'`` | ``'stopped'`` | ``'reconfigured'``.
            check_mode: If True, return what would happen without making changes.

        Returns:
            ``EnsureResult`` describing what was (or would be) done.

        Raises:
            ValueError: If ``state`` is not a valid target.
        """
        if state not in ("running", "stopped", "reconfigured"):
            raise ValueError(
                f"Invalid state {state!r}. Use 'running', 'stopped', or 'reconfigured'."
            )

        # 'reconfigured' has no idempotency — skip the pre-status read.
        if state == "reconfigured":
            return await self.reconfigure(check_mode=check_mode)

        log = ManagerLogBuilder()
        before = await self.status()
        before_dict = {"status": before}

        if state == "running":
            if before in _RUNNING_STATES:
                logger.debug(
                    "noop %s — already running",
                    self._endpoint,
                    extra=log.build_extra(
                        "noop",
                        {},
                        before=before_dict,
                        changed=False,
                    ),
                )
                return EnsureResult(
                    changed=False,
                    action="noop",
                    before=before_dict,
                    after=before_dict,
                )
            return await self.start(check_mode=check_mode)

        if state == "stopped":
            if before in _STOPPED_STATES:
                logger.debug(
                    "noop %s — already stopped (status=%s)",
                    self._endpoint,
                    before,
                    extra=log.build_extra(
                        "noop",
                        {},
                        before=before_dict,
                        changed=False,
                    ),
                )
                return EnsureResult(
                    changed=False,
                    action="noop",
                    before=before_dict,
                    after=before_dict,
                )
            return await self.stop(check_mode=check_mode)

        # Unreachable — state validation at the top of the method gates this branch.
        raise AssertionError(f"unreachable state {state!r}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _action(
        self,
        verb: str,
        action_name: str,
        check_mode: bool,
    ) -> EnsureResult:
        """Perform a service action (``start``/``stop``/``restart``/``reconfigure``).

        Reads status both before and after so callers see the real transition.
        """
        log = ManagerLogBuilder()
        before = await self.status()
        before_dict = {"status": before}

        if check_mode:
            severity = logger.warning if action_name == "stopped" else logger.info
            severity(
                "%s check_mode=True %s",
                action_name,
                self._endpoint,
                extra=log.build_extra(
                    action_name,
                    {},
                    before=before_dict,
                    changed=True,
                    check_mode=True,
                ),
            )
            return EnsureResult(
                changed=True,
                action=action_name,
                before=before_dict,
            )

        try:
            await self._client.post(
                f"{self._endpoint}/{verb}",
                {},
                timeout=self._apply_timeout,
            )
        except Exception as exc:
            logger.error(
                "%s failed %s: %s",
                verb,
                self._endpoint,
                exc,
                extra=log.build_extra(
                    f"{verb}_failed",
                    {},
                    before=before_dict,
                    error=str(exc),
                ),
            )
            raise

        after = await self.status()
        after_dict = {"status": after}
        severity = logger.warning if action_name == "stopped" else logger.info
        severity(
            "%s %s",
            action_name,
            self._endpoint,
            extra=log.build_extra(
                action_name,
                {},
                before=before_dict,
                after=after_dict,
                changed=True,
            ),
        )
        return EnsureResult(
            changed=True,
            action=action_name,
            before=before_dict,
            after=after_dict,
        )
