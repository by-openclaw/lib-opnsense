# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Base models shared across all OPNsense managers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnsureResult:
    """Result of an ensure() operation.

    Frozen dataclass returned by all ensure() methods across every manager.
    Provides a consistent, immutable result type for Ansible-style idempotency.

    Attributes:
        changed: Whether the operation modified state on the firewall.
        action:  One of 'created', 'updated', 'deleted', 'noop'.
        uuid:    UUID of the affected resource, or None for noop/delete.
        before:  Resource state before the operation, or None.
        after:   Resource state after the operation, or None.
    """

    changed: bool
    action: str  # 'created' | 'updated' | 'deleted' | 'noop'
    uuid: str | None = None
    before: dict | None = None
    after: dict | None = None
