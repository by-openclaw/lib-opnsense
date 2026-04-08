# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense auth user manager — CRUD + ensure() for local users.

API domain: /api/auth/user
Payload key: user
Match key:   name (unique username)
Entity suffix: '' (bare: search, get, add, set, del)

Endpoints:
    search  GET  auth/user/search
    get     GET  auth/user/get/{uuid}
    create  POST auth/user/add
    update  POST auth/user/set/{uuid}
    delete  POST auth/user/del/{uuid}
    apply   None — auth changes apply immediately

Redact fields: password, otp_seed, scrambled_password, authorizedkeys
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M01
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

    Input (ensure present):
        name:      Username, alphanumeric/underscore/hyphen, max 32 (required)
        email:     Email address (optional)
        password:  User password (optional)
        disabled:  Disable user account (optional, default='0')
        shell:     Login shell — '', '/bin/csh', '/bin/sh', '/bin/tcsh' (optional)
        expires:   Expiration date string, max 10 chars (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "auth/user"
    _payload_key = "user"
    _entity_suffix = ""  # auth/user uses bare names: search, get, add, set, del
    _apply_endpoint = None  # Auth changes apply immediately
    _match_key = "name"

    REDACT_FIELDS = {"password", "otp_seed", "scrambled_password", "authorizedkeys"}

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 32, "regex": r"^[a-zA-Z0-9_\-]+$"},
        "email": {"type": "email"},
        "password": {"type": "str", "max_length": 255},
        "disabled": {"type": "bool_str"},
        "shell": {"type": "enum", "values": ["", "/bin/csh", "/bin/sh", "/bin/tcsh"]},
        "expires": {"type": "str", "max_length": 10},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the auth user manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
