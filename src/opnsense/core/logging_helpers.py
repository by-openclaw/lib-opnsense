# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Structured log dict construction for manager operations.

Encapsulates the logging contract table from BaseManager — builds
structured extra dicts with timing, severity mapping, and all required
fields for Ansible -vvvvvv compatibility.

Zero imports from managers/ or client.py — independently reusable.

Logging contract:
    +-----------+-------+------+--------+-------+---------+-------------+
    | Action    | match | uuid | before | after | changed | duration_ms |
    +-----------+-------+------+--------+-------+---------+-------------+
    | created   |  yes  | yes  |   --   |  yes  |   yes   |     yes     |
    | updated   |  yes  | yes  |  yes   |  yes  |   yes   |     yes     |
    | deleted   |  yes  | yes  |  yes   |  --   |   yes   |     yes     |
    | noop      |  yes  | yes  |   --   |  --   |   yes   |     yes     |
    | error     |  yes  | yes* |  yes*  |  --   |   --    |     yes     |
    +-----------+-------+------+--------+-------+---------+-------------+

Severity: DEBUG=noop, INFO=create/update, WARNING=delete, ERROR=failure.

Usage::

    from opnsense.core.logging_helpers import ManagerLogBuilder

    builder = ManagerLogBuilder()
    extra = builder.created(match_fields, uuid="abc", after=redacted)
"""

from __future__ import annotations

import time
from typing import Any

# Severity mapping per action
ACTION_SEVERITY: dict[str, str] = {
    "created": "info",
    "updated": "info",
    "deleted": "warning",
    "noop": "debug",
    "create_failed": "error",
    "update_failed": "error",
    "delete_failed": "error",
    "list_failed": "error",
    "get_failed": "error",
    "get_schema_failed": "error",
    "apply_failed": "error",
    "ambiguous_match": "error",
    "validation_failed": "error",
}


class ManagerLogBuilder:
    """Build structured log extra dicts for manager operations.

    Tracks timing via ``time.monotonic()`` from construction.
    """

    def __init__(self) -> None:
        """Initialise with a monotonic start timestamp."""
        self._t0 = time.monotonic()

    @property
    def t0(self) -> float:
        """Return the start timestamp."""
        return self._t0

    def duration_ms(self) -> float:
        """Calculate elapsed time in milliseconds since construction."""
        return round((time.monotonic() - self._t0) * 1000, 1)

    @staticmethod
    def severity(action: str) -> str:
        """Map action name to log severity level.

        Args:
            action: Action name (e.g. 'created', 'noop', 'create_failed').

        Returns:
            Log level string: 'debug', 'info', 'warning', or 'error'.
        """
        return ACTION_SEVERITY.get(action, "info")

    def build_extra(
        self,
        action: str,
        match_fields: dict[str, Any] | None = None,
        *,
        uuid: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        changed: bool | None = None,
        check_mode: bool | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Build a structured log extra dict per the logging contract.

        Only includes fields that have values — no None padding.

        Args:
            action:       Action name (e.g. 'created', 'noop', 'update_failed').
            match_fields: Match key log fields from IdentityResolver.
            uuid:         Resource UUID (when known).
            before:       Redacted state before operation.
            after:        Redacted state after operation.
            changed:      Whether the operation changed state.
            check_mode:   Whether this was a dry-run.
            error:        Error message string (for failures).

        Returns:
            Dict suitable for passing as ``extra=`` to stdlib logger.
        """
        extra: dict[str, Any] = {"action": action}

        if check_mode is not None:
            extra["check_mode"] = check_mode
        if changed is not None:
            extra["changed"] = changed
        if uuid is not None:
            extra["uuid"] = uuid
        if match_fields is not None:
            extra.update(match_fields)
        if before is not None:
            extra["before"] = before
        if after is not None:
            extra["after"] = after
        if error is not None:
            extra["error"] = error

        extra["duration_ms"] = self.duration_ms()
        return extra
