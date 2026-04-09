# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense auth user model — typed frozen dataclass.

Maps to OPNsense API: ``/api/auth/user``
Payload key: ``user``
Match key: ``name``

Field types derived from OPNsense MVC model:
    https://docs.opnsense.org/development/frontend/models_fieldtypes.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthUser:
    """Local user entity from OPNsense auth/user API.

    Attributes:
        name:        Username (unique, alphanumeric + hyphens/underscores, max 32).
        email:       Email address (optional).
        password:    Password (write-only, redacted in results).
        disabled:    Whether the user is disabled ('0' or '1').
        shell:       Login shell ('' | '/bin/csh' | '/bin/sh' | '/bin/tcsh').
        expires:     Expiration date string (max 10 chars, e.g. '2026-12-31').
        otp_seed:    OTP seed (write-only, redacted in results).
        scrambled_password: Hashed password (redacted in results).
        authorizedkeys:    SSH authorized keys (redacted in results).
        uuid:        Resource UUID assigned by OPNsense.
    """

    name: str
    email: str = ""
    password: str = ""
    disabled: str = "0"
    shell: str = ""
    expires: str = ""
    otp_seed: str = ""
    scrambled_password: str = ""
    authorizedkeys: str = ""
    uuid: str = ""
