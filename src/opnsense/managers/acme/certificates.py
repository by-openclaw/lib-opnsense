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
    update     POST acmeclient/certificates/set/{uuid}
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

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class AcmeCertificateManager(BaseManager):
    """Manage os-acme-client certificates via /api/acmeclient/certificates.

    Inherits the full CRUD + ``ensure()`` lifecycle from :class:`BaseManager`
    and adds the certificate lifecycle verbs: :meth:`sign`, :meth:`revoke`,
    :meth:`remove_key`, :meth:`automation`, :meth:`import_`.

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
            body = await self._client.post(f"{self._endpoint}/{verb}/{uuid}")
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
