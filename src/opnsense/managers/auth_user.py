"""OPNsense auth user manager — CRUD + ensure() for local users.

API domain: /api/auth/user
Payload key: user
Match key:   name (unique username)

Auth changes apply immediately — no reconfigure endpoint needed.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class AuthUserManager(BaseManager):
    """Manage OPNsense local users via /api/auth/user.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Redacts password, OTP seed, scrambled password, and SSH keys in results.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = AuthUserManager(client)
            result = await mgr.ensure("present", {"name": "rune", "email": "..."})
    """

    _endpoint = "auth/user"
    _payload_key = "user"
    _apply_endpoint = None  # Auth changes apply immediately
    _match_key = "name"

    REDACT_FIELDS = {"password", "otp_seed", "scrambled_password", "authorizedkeys"}

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the auth user manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
