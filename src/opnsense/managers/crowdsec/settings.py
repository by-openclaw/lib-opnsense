# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense CrowdSec general settings manager — singleton config (get/set).

API domain: /api/crowdsec/general
Payload key: general
Pattern:    BaseSingletonManager — fetch/diff/set with idempotent ensure().

Endpoints:
    get          GET  crowdsec/general/get
    set          POST crowdsec/general/set
    apply        POST crowdsec/service/reconfigure

The plugin's ``GeneralController`` extends ``ApiMutableModelControllerBase``,
so ``get``/``set`` are inherited and every field below is writable.

**Why this matters for a multi-server deployment.** A default install turns on
``lapi_enabled`` and points ``firewall_bouncer_enabled`` at its own LAPI on
127.0.0.1. The firewall then looks perfectly healthy while being completely
isolated from a central LAPI — decisions raised elsewhere are never enforced
here, and nothing in the UI says so. Setting ``lapi_manual_configuration`` is
what lets the bouncer talk to a remote LAPI instead.

Reference: https://docs.crowdsec.net/u/user_guides/multiserver_setup/
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_singleton import BaseSingletonManager


class CrowdSecSettingsManager(BaseSingletonManager):
    """Manage the OPNsense CrowdSec plugin config via /api/crowdsec/general.

    Inherits fetch/diff/set + ``ensure(state='present')`` from
    :class:`BaseSingletonManager`. Bouncers, machines, collections and
    decisions are read-only listings owned by their own managers.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = CrowdSecSettingsManager(client)

            # Firewall as a bouncer only, pulling from a central LAPI:
            await mgr.ensure("present", {
                "agent_enabled": "0",
                "lapi_enabled": "0",
                "firewall_bouncer_enabled": "1",
                "lapi_manual_configuration": "1",
            })

    Input (ensure present): any subset of the fields in ``_validators``; only
    the keys passed are diffed, everything else is left untouched.

    Output (EnsureResult):
        changed:  bool — True if any field drifted.
        action:   ``'updated'`` | ``'noop'``.
        uuid:     Always None (singleton config).
        before:   Current settings, ``enroll_key`` redacted.
        after:    Settings after the set, ``enroll_key`` redacted.
    """

    _endpoint = "crowdsec/general"
    _payload_key = "general"
    _apply_endpoint = "crowdsec/service/reconfigure"
    _apply_timeout = 60

    # enroll_key is a live CrowdSec console enrolment credential. It is returned
    # in plaintext by GET, so it must never reach a log, a diff or a captured
    # schema artefact.
    REDACT_FIELDS: set[str] = {"enroll_key"}

    _validators = {
        # Boolean toggles ("0" / "1")
        "agent_enabled": {"type": "bool_str"},
        "lapi_enabled": {"type": "bool_str"},
        "firewall_bouncer_enabled": {"type": "bool_str"},
        "lapi_manual_configuration": {"type": "bool_str"},
        "rules_enabled": {"type": "bool_str"},
        "rules_log": {"type": "bool_str"},
        "crowdsec_firewall_verbose": {"type": "bool_str"},
        # LAPI bind address/port used when this host runs the LAPI itself.
        "lapi_listen_address": {"type": "ip"},
        "lapi_listen_port": {"type": "port"},
        # The API enforces alphanumeric-only, 1-63 chars: a hyphen is rejected
        # with "A tag must only contain numbers and letters and must be between
        # 1 and 63 characters." Encoded here so the failure surfaces locally
        # instead of as a 400 from the firewall.
        "rules_tag": {"type": "str", "max_length": 63, "regex": r"^[A-Za-z0-9]*$"},
        "enroll_key": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the CrowdSec settings manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
