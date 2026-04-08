# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Identity resolution — composite match key lookup.

Finds a resource in a list of dicts by matching one or more key fields.
Decoupled from BaseManager — accepts a ``list_fn`` callable for any data source.

Zero imports from managers/ or client.py — independently reusable.

Usage::

    from opnsense.core.identity import IdentityResolver

    resolver = IdentityResolver(match_keys=["tag", "if"])
    existing = await resolver.find_existing(params, list_fn=mgr.list)
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from opnsense.exceptions import AmbiguousMatchError

logger = logging.getLogger(__name__)


class IdentityResolver:
    """Resolve resource identity via composite match keys.

    Args:
        match_keys: List of field names forming the resource identity.
        endpoint:   API endpoint path (for error context in AmbiguousMatchError).
        manager_name: Manager class name (for error messages).
    """

    def __init__(
        self,
        match_keys: list[str],
        endpoint: str = "",
        manager_name: str = "",
    ) -> None:
        """Initialise with match keys and optional context for error messages."""
        if not match_keys:
            raise ValueError("match_keys must be a non-empty list")
        self._match_keys = list(match_keys)
        self._endpoint = endpoint
        self._manager_name = manager_name

    @property
    def match_keys(self) -> list[str]:
        """Return a copy of the match keys."""
        return list(self._match_keys)

    def match_label(self, params: dict[str, Any]) -> str:
        """Human-readable label: 'key1=val1 key2=val2'.

        Args:
            params: Parameters containing match key fields.

        Returns:
            Space-separated key=value pairs for all match keys.
        """
        return " ".join(f"{k}={params.get(k, '')}" for k in self._match_keys)

    def match_log_fields(self, params: dict[str, Any]) -> dict[str, Any]:
        """Build log extra fields for match keys.

        Args:
            params: Parameters containing match key fields.

        Returns:
            Dict with 'match_keys' and 'endpoint' for structured logging.
        """
        return {
            "match_keys": {k: str(params.get(k, "")) for k in self._match_keys},
            "endpoint": self._endpoint,
        }

    async def find_existing(
        self,
        params: dict[str, Any],
        list_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ) -> dict[str, Any] | None:
        """Search for an existing resource by composite match keys.

        Uses the first match key as the search phrase (server-side substring
        filter), then exact-matches ALL keys in Python.

        Args:
            params:  Parameters containing all match key fields.
            list_fn: Async callable that accepts a search phrase and returns
                     a list of resource dicts (e.g. ``manager.list``).

        Returns:
            The single matching resource dict (with 'uuid' key), or None.

        Raises:
            AmbiguousMatchError: If more than one resource matches all keys.
        """
        primary_value = str(params.get(self._match_keys[0], ""))
        if not primary_value:
            return None

        rows = await list_fn(primary_value)

        matches = [
            row
            for row in rows
            if all(str(row.get(k, "")) == str(params.get(k, "")) for k in self._match_keys)
        ]

        if len(matches) == 0:
            return None
        if len(matches) == 1:
            return matches[0]

        match_vals = {k: str(params.get(k, "")) for k in self._match_keys}
        uuids = [m["uuid"] for m in matches]
        logger.error(
            "ambiguous match %s: %d resources match %s — UUIDs: %s",
            self._manager_name,
            len(matches),
            match_vals,
            uuids,
            extra={
                "action": "ambiguous_match",
                "match_keys": match_vals,
                "uuids": uuids,
                "count": len(matches),
                "endpoint": self._endpoint,
            },
        )
        raise AmbiguousMatchError(
            message=(
                f"{self._manager_name}: {len(matches)} resources match "
                f"{match_vals}. "
                f"UUIDs: {uuids}. "
                f"Deduplicate manually or pass uuid= to ensure()."
            ),
            match_keys=match_vals,
            uuids=uuids,
            endpoint=self._endpoint,
        )
