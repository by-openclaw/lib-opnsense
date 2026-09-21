# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME account manager — CRUD + ensure() + register().

API domain: /api/acmeclient/accounts  (os-acme-client plugin)
Payload key: account
Match key:   name
Entity suffix: '' (bare: search, get, add, set, del, toggle)

Endpoints:
    search    GET  acmeclient/accounts/search
    get       GET  acmeclient/accounts/get/{uuid}
    create    POST acmeclient/accounts/add
    update    POST acmeclient/accounts/update/{uuid}
    delete    POST acmeclient/accounts/del/{uuid}
    register  POST acmeclient/accounts/register/{uuid}   (custom — register with CA)
    apply     None — config is stored immediately; use AcmeServiceManager to
              reconfigure and ``register`` to activate the account with the CA.

Redact fields: key (account private key), eab_hmac, eab_kid
Reference: https://docs.opnsense.org/manual/how-tos/self-signed-chain.html
           https://github.com/opnsense/plugins/tree/master/security/acme-client
"""

from __future__ import annotations

import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class AcmeAccountManager(BaseManager):
    """Manage os-acme-client ACME accounts via /api/acmeclient/accounts.

    Inherits the full CRUD + ``ensure()`` lifecycle from :class:`BaseManager`
    and adds :meth:`register` — the custom verb that registers the account with
    the ACME CA (a prerequisite before any certificate referencing it can be
    signed) — plus the idempotent ``ensure("registered")`` state.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = AcmeAccountManager(client)
            r = await mgr.ensure("present", {
                "name": "letsencrypt-prod",
                "email": "admin@example.com",
                "ca": "letsencrypt",
            })
            await mgr.register(r.uuid)   # register with the CA

    Input (ensure present):
        name:        Account name (required, match key).
        email:       Contact email registered with the CA.
        ca:          CA directory — 'letsencrypt', 'letsencrypt_test', 'buypass',
                     'buypass_test', 'google', 'google_test', 'sslcom', 'zerossl',
                     'custom'.
        custom_ca:   Custom ACME directory URL (ca='custom').
        eab_kid:     External Account Binding key id (redacted).
        eab_hmac:    External Account Binding HMAC key (redacted).
        description: Free-text description.
        enabled:     '1' / '0'.

    REDACT_FIELDS: key, eab_hmac, eab_kid.

    Output (EnsureResult): standard created/updated/deleted/noop.
    """

    _endpoint = "acmeclient/accounts"
    _payload_key = "account"
    _entity_suffix = ""  # bare action names: search, get, add, set, del
    _update_action = "update"  # acmeclient: set/{uuid} says "saved" but is the whole-model setter
    _apply_endpoint = None  # stored immediately; activate via register()/service
    _match_key = "name"

    REDACT_FIELDS: set[str] = {"key", "eab_hmac", "eab_kid"}

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "description": {"type": "str", "max_length": 255},
        "email": {"type": "str", "max_length": 255},
        "ca": {
            "type": "enum",
            "values": [
                "buypass",
                "buypass_test",
                "google",
                "google_test",
                "letsencrypt",
                "letsencrypt_test",
                "sslcom",
                "zerossl",
                "custom",
            ],
        },
        "custom_ca": {"type": "str", "max_length": 255},
        "eab_kid": {"type": "str", "max_length": 255},
        "eab_hmac": {"type": "str", "max_length": 1024},
        "enabled": {"type": "bool_str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the ACME account manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def ensure(  # type: ignore[override]
        self,
        state: str,
        params: dict[str, Any],
        check_mode: bool = False,
        uuid: str | None = None,
    ) -> EnsureResult:
        """Ensure the account and, for ``state='registered'``, its CA registration.

        ``present`` / ``absent`` behave exactly like :meth:`BaseManager.ensure`.
        ``registered`` = ``present`` + :meth:`register` when the last registration
        ``statusCode`` is not ``200`` (idempotent: a registered account is a noop).

        Returns:
            ``EnsureResult``; ``action`` adds ``registered`` / ``would_register``.
        """
        if state != "registered":
            return await super().ensure(state, params, check_mode=check_mode, uuid=uuid)
        result = await super().ensure("present", params, check_mode=check_mode, uuid=uuid)
        acct_uuid = result.uuid
        if acct_uuid is None:  # would be created (check mode) — registration follows
            return EnsureResult(
                changed=True, action="would_register", before=result.before, after=result.after
            )
        current = await self.get(acct_uuid)
        status = str(current.get("statusCode", "") or "").strip()
        if status == "200":
            return result
        if check_mode:
            return EnsureResult(
                changed=True, action="would_register", uuid=acct_uuid, before={"statusCode": status}
            )
        reg = await self.register(acct_uuid)
        return EnsureResult(
            changed=True,
            action="registered",
            uuid=acct_uuid,
            before={"statusCode": status},
            after=reg.after,
        )

    async def register(self, uuid: str) -> EnsureResult:
        """Register the account with its ACME CA (custom ``register`` verb).

        POSTs ``acmeclient/accounts/register/{uuid}``. This contacts the CA,
        creates/recovers the ACME account and stores the issued key. Idempotent
        on the CA side (re-registering an existing account is a no-op there), so
        it is always reported as ``changed=True`` (an action was performed).

        Args:
            uuid: Account UUID (from ``ensure``/``create``).

        Returns:
            ``EnsureResult`` with ``action='registered'``.
        """
        try:
            body = await self._client.post(f"{self._endpoint}/register/{uuid}")
        except Exception as exc:
            logger.error(
                "register failed acme account uuid=%s: %s",
                uuid,
                exc,
                extra={
                    "action": "register_failed",
                    "endpoint": self._endpoint,
                    "uuid": uuid,
                    "error": str(exc),
                },
            )
            raise
        status = str(body.get("status", body.get("result", "")))
        logger.info(
            "registered acme account uuid=%s status=%s",
            uuid,
            status,
            extra={
                "action": "registered",
                "endpoint": self._endpoint,
                "uuid": uuid,
                "changed": True,
            },
        )
        return EnsureResult(
            changed=True,
            action="registered",
            uuid=uuid,
            after={"status": status},
        )

    async def status(self, uuid: str) -> dict[str, Any]:
        """Return the account's registration status fields.

        Convenience reader — fetches the account and returns its
        ``statusCode`` / ``statusLastUpdate``.

        Args:
            uuid: Account UUID.

        Returns:
            Dict with ``statusCode`` and ``statusLastUpdate``.
        """
        acct = await self.get(uuid)
        return {
            "statusCode": acct.get("statusCode", ""),
            "statusLastUpdate": acct.get("statusLastUpdate", ""),
        }
