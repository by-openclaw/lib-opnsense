# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Manager protocol — typing.Protocol for dependency injection.

Consumers depend on this protocol, not on the concrete BaseManager class.
Enables testing with stubs and future alternative implementations.

Usage::

    from opnsense.managers.protocols import ManagerProtocol

    async def provision(mgr: ManagerProtocol, params: dict) -> EnsureResult:
        return await mgr.ensure("present", params)
"""

from __future__ import annotations

from typing import Any, Protocol

from opnsense.models.base import EnsureResult


class ManagerProtocol(Protocol):
    """Protocol defining what a manager looks like to consumers.

    All managers (BaseManager subclasses and standalone managers)
    should satisfy this protocol.
    """

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List resources matching an optional search phrase."""
        ...

    async def get(self, uuid: str) -> dict[str, Any]:
        """Get a single resource by UUID."""
        ...

    async def create(self, params: dict[str, Any], check_mode: bool = False) -> EnsureResult:
        """Create a new resource."""
        ...

    async def update(
        self, uuid: str, params: dict[str, Any], check_mode: bool = False
    ) -> EnsureResult:
        """Update an existing resource."""
        ...

    async def delete(self, uuid: str, check_mode: bool = False) -> EnsureResult:
        """Delete a resource by UUID."""
        ...

    async def ensure(
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
        uuid: str | None = None,
    ) -> EnsureResult:
        """Ensure a resource matches desired state."""
        ...
