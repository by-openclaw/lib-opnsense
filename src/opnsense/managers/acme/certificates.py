# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME certificate manager — CRUD + ensure() + issue/lifecycle verbs.

API domain: /api/acmeclient/certificates  (os-acme-client plugin)
Payload key: certificate
Match key:   name
Entity suffix: '' (bare: search, get, add, set, del, toggle)

A certificate references an ``account`` (CA), a ``validationMethod`` (challenge)
and optional ``restartActions``. Once defined it must be **signed** (issued) via
the custom ``sign`` verb; the resulting leaf lands in the OPNsense trust store
under ``certRefId`` for other subsystems (WebGUI, HAProxy, …) to reference.

Endpoints:
    search     GET  acmeclient/certificates/search
    get        GET  acmeclient/certificates/get/{uuid}
    create     POST acmeclient/certificates/add
    update     POST acmeclient/certificates/update/{uuid}
    delete     POST acmeclient/certificates/del/{uuid}
    sign       POST acmeclient/certificates/sign/{uuid}        (issue/renew)
    revoke     POST acmeclient/certificates/revoke/{uuid}      (revoke at CA)
    removekey  POST acmeclient/certificates/removekey/{uuid}   (strip private key)
    automation POST acmeclient/certificates/automation/{uuid}  (run restartActions)
    import     POST acmeclient/certificates/import/{uuid}      (re-import leaf)
    apply      None — CRUD stored immediately; issuance is the ``sign`` verb.

Reference: https://github.com/opnsense/plugins/tree/master/security/acme-client
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseServerError
from opnsense.managers.base import BaseManager
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class AcmeCertificateManager(BaseManager):
    """Manage os-acme-client certificates via /api/acmeclient/certificates.

    Inherits the full CRUD + ``ensure()`` lifecycle from :class:`BaseManager`
    and adds the certificate lifecycle verbs: :meth:`sign`, :meth:`revoke`,
    :meth:`remove_key`, :meth:`automation`, :meth:`import_` — plus the idempotent
    ``ensure("issued")`` state (present + sign once; ``renew=True`` to renew).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = AcmeCertificateManager(client)
            r = await mgr.ensure("present", {
                "name": "fw.example.com",
                "account": account_uuid,
                "validationMethod": validation_uuid,
                "keyLength": "key_4096",
                "restartActions": gui_action_uuid,
            })
            await mgr.sign(r.uuid)   # issue the certificate

    Input (ensure present):
        name:             Primary domain / certificate name (required, match key).
        altNames:         Additional SANs.
        account:          UUID of the AcmeAccount (CA).
        validationMethod: UUID of the AcmeValidation (challenge).
        keyLength:        'key_2048' / 'key_3072' / 'key_4096' / 'key_ec256' /
                          'key_ec384'.
        ocsp:             OCSP Must-Staple ('1'/'0').
        restartActions:   UUID(s) of AcmeAction to run post-issue (comma-separated).
        autoRenewal:      '1'/'0'.
        renewInterval:    Renew when this many days remain.
        aliasmode:        'none' / 'automatic' / 'domain' / 'challenge'.
        enabled:          '1' / '0'.

    Output (EnsureResult): standard created/updated/deleted/noop; verbs return
    action='signed'/'revoked'/'key_removed'/'automation_run'/'imported'.
    """

    _endpoint = "acmeclient/certificates"
    _payload_key = "certificate"
    _entity_suffix = ""
    _update_action = "update"  # acmeclient: set/{uuid} says "saved" but is the whole-model setter
    _apply_endpoint = None  # issuance is explicit via sign()
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "description": {"type": "str", "max_length": 255},
        "altNames": {"type": "str"},
        "account": {"type": "str"},
        "validationMethod": {"type": "str"},
        "keyLength": {
            "type": "enum",
            "values": ["key_2048", "key_3072", "key_4096", "key_ec256", "key_ec384"],
        },
        "ocsp": {"type": "bool_str"},
        "restartActions": {"type": "str"},
        "autoRenewal": {"type": "bool_str"},
        "renewInterval": {"type": "str", "max_length": 5},
        "aliasmode": {
            "type": "enum",
            "values": ["none", "automatic", "domain", "challenge"],
        },
        "enabled": {"type": "bool_str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the ACME certificate manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    # acme.sh DNS-01 round trips (dns_sleep + CA) take minutes — never the default timeout.
    _sign_timeout = 300
    # `sign` is ASYNCHRONOUS on the plugin side (configd runs lecert.php under daemon -f and
    # answers at once): the object stays statusCode 100 ("in progress") until acme.sh finishes.
    # ensure("issued") therefore polls the object until a terminal status; a second sign while
    # the first is still running makes the CA answer "order status valid" → 400 (seen 2026-09-09).
    _issue_poll_interval = 10.0
    _issue_wait_timeout = 600.0
    _STATUS_RUNNING = ("100",)  # lecert.php sets 100 while it works
    _STATUS_PENDING = ("", "100")  # right after our sign: not yet 100, or 100
    _STATUS_OK = ("200", "250")

    async def ensure(  # type: ignore[override]
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
        uuid: str | None = None,
        renew: bool = False,
    ) -> EnsureResult:
        """Ensure the certificate object and, for ``state='issued'``, an issued leaf.

        ``present`` / ``absent`` behave exactly like :meth:`BaseManager.ensure`.
        ``issued`` = ``present`` + :meth:`sign` when the object has no issued leaf yet
        (``certRefId`` empty or last ``statusCode`` not OK). An issued, unchanged
        certificate is a noop; ``renew=True`` signs again (explicit renewal, never
        idempotent by design). ``certRefId`` is read-only on the API (setBase drops it, verified
        on 26.7): the trust-store refid the leaf lands under is the plugin's choice, so binding
        the WebGUI to it is a seed concern (pre-set refid in config.xml), not this manager's.

        ``sign`` is asynchronous on the plugin: this method polls the object until a
        terminal ``statusCode`` and raises :class:`OpnsenseServerError` on 300/400.
        """
        if state != "issued":
            return await super().ensure(state, params, check_mode=check_mode, uuid=uuid)
        result = await super().ensure("present", params, check_mode=check_mode, uuid=uuid)
        cert_uuid = result.uuid
        if cert_uuid is None:  # object would be created (check mode) — nothing to sign yet
            return EnsureResult(
                changed=True, action="would_issued", before=result.before, after=result.after
            )
        current = await self.get(cert_uuid)
        ref, status, stamp = self._issue_state(current)
        if status in self._STATUS_RUNNING and not check_mode:
            # An issue/renew may still be running (cron, GUI, previous run): never race it.
            current = await self._wait_for_issue(cert_uuid, stale_stamp=None)
            ref, status, stamp = self._issue_state(current)
        issued = bool(ref) and status in self._STATUS_OK
        if issued and not renew:
            return result
        action = "renewed" if issued else "issued"
        before = {"certRefId": ref, "statusCode": status}
        if check_mode:
            logger.info(
                "%s check_mode=True acme cert uuid=%s",
                action,
                cert_uuid,
                extra={"action": f"would_{action}", "endpoint": self._endpoint, "uuid": cert_uuid},
            )
            return EnsureResult(
                changed=True, action=f"would_{action}", uuid=cert_uuid, before=before
            )
        await self._invoke("sign", cert_uuid, action)
        final = await self._wait_for_issue(cert_uuid, stale_stamp=stamp)
        ref_after, status_after, _ = self._issue_state(final)
        after = {"certRefId": ref_after, "statusCode": status_after}
        if status_after not in self._STATUS_OK or not ref_after:
            logger.error(
                "%s failed acme cert uuid=%s statusCode=%s",
                action,
                cert_uuid,
                status_after,
                extra={"action": f"{action}_failed", "endpoint": self._endpoint, "uuid": cert_uuid},
            )
            raise OpnsenseServerError(
                f"acme {action} of {cert_uuid} ended with statusCode={status_after or 'none'} "
                "(400 = validation/CA failure, 300 = config error, 100 = still running after "
                f"{int(self._issue_wait_timeout)} s) — read the acmeclient log on the firewall",
                endpoint=f"{self._endpoint}/sign/{cert_uuid}",
            )
        return EnsureResult(changed=True, action=action, uuid=cert_uuid, before=before, after=after)

    @staticmethod
    def _issue_state(obj: dict[str, Any]) -> tuple[str, str, str]:
        """``(certRefId, statusCode, statusLastUpdate)`` of a full certificate object."""
        return (
            str(obj.get("certRefId", "") or "").strip(),
            str(obj.get("statusCode", "") or "").strip(),
            str(obj.get("statusLastUpdate", "") or "").strip(),
        )

    async def _wait_for_issue(self, uuid: str, stale_stamp: str | None) -> dict[str, Any]:
        """Poll the certificate until a terminal statusCode that is NEWER than ``stale_stamp``.

        Right after our ``sign`` the object still carries the previous (terminal) status for a
        moment — lecert.php starts under ``daemon -f``; the old status must not be mistaken for
        the outcome. ``stale_stamp=None`` = just wait for the current run to end. Returns the
        last object read; the caller decides what the status means.
        """
        deadline = asyncio.get_running_loop().time() + self._issue_wait_timeout
        current = await self.get(uuid)
        while True:
            _, status, stamp = self._issue_state(current)
            pending = status in self._STATUS_PENDING or (
                stale_stamp is not None and stamp == stale_stamp
            )
            if not pending or asyncio.get_running_loop().time() >= deadline:
                return current
            await asyncio.sleep(self._issue_poll_interval)
            current = await self.get(uuid)

    async def _invoke(self, verb: str, uuid: str, action_name: str) -> EnsureResult:
        """POST a custom certificate verb (``{endpoint}/{verb}/{uuid}``).

        Args:
            verb:        API verb (e.g. 'sign', 'revoke', 'removekey').
            uuid:        Certificate UUID.
            action_name: EnsureResult action label.

        Returns:
            ``EnsureResult`` with ``changed=True`` and the API status.
        """
        try:
            body = await self._client.post(
                f"{self._endpoint}/{verb}/{uuid}",
                timeout=self._sign_timeout if verb == "sign" else None,
            )
        except Exception as exc:
            logger.error(
                "%s failed acme cert uuid=%s: %s",
                verb,
                uuid,
                exc,
                extra={
                    "action": f"{verb}_failed",
                    "endpoint": self._endpoint,
                    "uuid": uuid,
                    "error": str(exc),
                },
            )
            raise
        status = str(body.get("status", body.get("result", "")))
        logger.info(
            "%s acme cert uuid=%s status=%s",
            action_name,
            uuid,
            status,
            extra={
                "action": action_name,
                "endpoint": self._endpoint,
                "uuid": uuid,
                "changed": True,
            },
        )
        return EnsureResult(changed=True, action=action_name, uuid=uuid, after={"status": status})

    async def sign(self, uuid: str) -> EnsureResult:
        """Issue (or renew) the certificate via the CA (``sign`` verb)."""
        return await self._invoke("sign", uuid, "signed")

    async def revoke(self, uuid: str) -> EnsureResult:
        """Revoke the certificate at the CA (``revoke`` verb)."""
        return await self._invoke("revoke", uuid, "revoked")

    async def remove_key(self, uuid: str) -> EnsureResult:
        """Strip the stored private key (``removekey`` verb)."""
        return await self._invoke("removekey", uuid, "key_removed")

    async def automation(self, uuid: str) -> EnsureResult:
        """Run the certificate's restart/automation actions (``automation`` verb)."""
        return await self._invoke("automation", uuid, "automation_run")

    async def import_(self, uuid: str) -> EnsureResult:
        """Re-import the issued leaf into the trust store (``import`` verb)."""
        return await self._invoke("import", uuid, "imported")
