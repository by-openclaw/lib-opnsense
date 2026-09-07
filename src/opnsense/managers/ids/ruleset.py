# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IDS ruleset toggles — enable/disable downloadable rule sets by filename.

API domain: /api/ids/settings
Pattern:    custom (rulesets are a fixed catalogue: no add/del, only toggle + properties).

Endpoints:
    list    GET  ids/settings/listRulesets   ({rows: [{filename, description, enabled}]})
    toggle  POST ids/settings/toggleRuleset/<filename>/<0|1>
    apply   POST ids/service/reconfigure  (+ ids/service/updateRules to actually fetch the rules)

Toggling only flags a set; the rules are fetched by ``updateRules`` (see
:class:`~opnsense.managers.ids.service.IdsServiceManager`) and activated by ``reconfigure``.
"""

from __future__ import annotations

import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseServerError
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class IdsRulesetManager:
    """Ensure IDS rule sets are enabled or disabled.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IdsRulesetManager(client)
            rows = await mgr.list()
            names = [r["filename"] for r in rows if r["filename"].startswith("emerging-")]
            await mgr.ensure_many({n: True for n in names} | {"abuse.ch.sslblacklist.rules": True})

    Output (EnsureResult):
        changed: True if any toggle was fired.
        action:  ``'updated'`` | ``'noop'``.
        before/after: ``{filename: '0'|'1'}`` for the filenames asked about.
    """

    _endpoint = "ids/settings"
    _apply_endpoint = "ids/service/reconfigure"

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the ruleset manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        self._client = client

    async def list(self) -> list[dict[str, Any]]:
        """Return the ruleset catalogue rows (``filename``, ``description``, ``enabled``)."""
        body = await self._client.get(f"{self._endpoint}/listRulesets")
        rows = body.get("rows", []) if isinstance(body, dict) else []
        return [r for r in rows if isinstance(r, dict)]

    async def ensure(
        self, filename: str, enabled: bool = True, check_mode: bool = False, apply: bool = True
    ) -> EnsureResult:
        """Ensure one ruleset is enabled/disabled (idempotent)."""
        return await self.ensure_many({filename: enabled}, check_mode=check_mode, apply=apply)

    async def ensure_many(
        self, desired: dict[str, bool], check_mode: bool = False, apply: bool = True
    ) -> EnsureResult:
        """Ensure a set of rulesets match ``desired`` (filename → enabled) with minimal toggles.

        Args:
            desired:    ``{filename: True|False}``.
            check_mode: Report without toggling.
            apply:      Reconfigure the IDS after toggling (``False`` to batch with other changes).

        Raises:
            ValueError: A filename is not in the device's catalogue.
        """
        rows = {r.get("filename"): str(r.get("enabled", "0")) for r in await self.list()}
        unknown = [f for f in desired if f not in rows]
        if unknown:
            raise ValueError(f"IdsRulesetManager: unknown ruleset(s) {unknown} — see list()")
        before = {f: rows[f] for f in desired}
        todo = {
            f: ("1" if want else "0")
            for f, want in desired.items()
            if rows[f] != ("1" if want else "0")
        }
        if not todo:
            logger.debug(
                "noop ids rulesets — %d already match",
                len(desired),
                extra={"action": "noop", "count": len(desired)},
            )
            return EnsureResult(changed=False, action="noop", before=before, after=before)
        after = {**before, **todo}
        if check_mode:
            logger.info(
                "ids rulesets check_mode=True: %d toggle(s)",
                len(todo),
                extra={"action": "updated", "check_mode": True, "toggles": list(todo)},
            )
            return EnsureResult(changed=True, action="updated", before=before, after=after)
        try:
            for filename, flag in todo.items():
                await self._client.post(
                    f"{self._endpoint}/toggleRuleset/{filename}/{flag}", data={}
                )
            if apply:
                await self._client.reconfigure(self._apply_endpoint, timeout=120)
        except OpnsenseServerError as exc:
            # toggleRuleset saves the WHOLE IDS model; a seeded device still carries the
            # OPNsense default general.interfaces="wan" (not a slot on our seeds), so the save
            # fails validation and surfaces as an opaque 500. Point at the real fix.
            logger.error(
                "ids ruleset toggle failed: %s",
                exc,
                extra={"action": "update_failed", "error": str(exc)},
            )
            raise OpnsenseServerError(
                f"{exc} — the IDS model may be invalid as stored (e.g. general.interfaces='wan' "
                "on a fresh device): apply IdsSettingsManager (interfaces/homenet) BEFORE "
                "toggling rulesets"
            ) from exc
        except Exception as exc:
            logger.error(
                "ids ruleset toggle failed: %s",
                exc,
                extra={"action": "update_failed", "error": str(exc)},
            )
            raise
        logger.info("ids rulesets updated: %s", todo, extra={"action": "updated", "toggles": todo})
        return EnsureResult(changed=True, action="updated", before=before, after=after)
