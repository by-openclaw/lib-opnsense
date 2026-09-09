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
        try:
            return " ".join(f"{k}={params.get(k, '')}" for k in self._match_keys)
        except Exception as exc:
            logger.error(
                "match_label failed: %s",
                exc,
                extra={"action": "match_label_failed", "error": str(exc)},
            )
            raise

    def match_log_fields(self, params: dict[str, Any]) -> dict[str, Any]:
        """Build log extra fields for match keys.

        Args:
            params: Parameters containing match key fields.

        Returns:
            Dict with 'match_keys' and 'endpoint' for structured logging.
        """
        try:
            return {
                "match_keys": {k: str(params.get(k, "")) for k in self._match_keys},
                "endpoint": self._endpoint,
            }
        except Exception as exc:
            logger.error(
                "match_log_fields failed: %s",
                exc,
                extra={"action": "match_log_fields_failed", "error": str(exc)},
            )
            raise

    async def find_matching(
        self,
        params: dict[str, Any],
        list_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
        _search_phrase: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return EVERY resource matching the composite match keys.

        Same lookup as :meth:`find_existing`, but duplicates are returned instead of
        raising — the caller decides what to do with them. Ordered by UUID so a
        de-duplicating caller keeps the same survivor on every run.

        Args:
            params:  Parameters containing all match key fields.
            list_fn: Async callable that accepts a search phrase and returns resource dicts.

        Returns:
            Matching resource dicts, possibly empty, ordered by UUID.
        """
        if _search_phrase is None:
            _search_phrase = next(
                (str(params.get(k, "")) for k in self._match_keys if str(params.get(k, ""))),
                "",
            )
        rows = await list_fn(_search_phrase)
        matches = [
            row
            for row in rows
            if all(str(row.get(k, "")) == str(params.get(k, "")) for k in self._match_keys)
        ]
        return sorted(matches, key=lambda row: str(row.get("uuid", "")))

    async def find_existing(
        self,
        params: dict[str, Any],
        list_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ) -> dict[str, Any] | None:
        """Search for an existing resource by composite match keys.

        Uses the first NON-empty match key as the search phrase (server-side
        substring filter; ``''`` = list all when every key is empty), then
        exact-matches ALL keys in Python — an empty key value is a valid
        identity (catch-all Unbound forward ``domain=''``).

        Args:
            params:  Parameters containing all match key fields.
            list_fn: Async callable that accepts a search phrase and returns
                     a list of resource dicts (e.g. ``manager.list``).

        Returns:
            The single matching resource dict (with 'uuid' key), or None.

        Raises:
            AmbiguousMatchError: If more than one resource matches all keys.
        """
        try:
            # The server-side search phrase is the first NON-empty match key.
            # An empty primary is a legitimate identity (e.g. the catch-all
            # Unbound forward has domain=''): bailing out here made ensure()
            # create a duplicate on every run. With every key empty the phrase
            # is '' (list all) and the Python exact-match below decides.
            search_phrase = next(
                (str(params.get(k, "")) for k in self._match_keys if str(params.get(k, ""))),
                "",
            )

            matches = await self.find_matching(params, list_fn, _search_phrase=search_phrase)

            if len(matches) == 0:
                return None
            if len(matches) == 1:
                return matches[0]

            match_vals = {k: str(params.get(k, "")) for k in self._match_keys}
            uuids = [m["uuid"] for m in matches]
        except AmbiguousMatchError:
            raise
        except Exception as exc:
            logger.error(
                "find_existing failed %s: %s",
                self._manager_name,
                exc,
                extra={
                    "action": "find_existing_failed",
                    "endpoint": self._endpoint,
                    "error": str(exc),
                },
            )
            raise

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
