# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME action manager — CRUD + ensure().

API domain: /api/acmeclient/actions  (os-acme-client plugin)
Payload key: action
Match key:   name
Entity suffix: '' (bare: search, get, add, set, del, toggle)

An action is automation run after a certificate is issued/renewed — typically
restarting a local service so it serves the new leaf. The platform uses
``type='configd_restart_gui'`` to restart the OPNsense WebGUI (so the new ACME
cert is served without a browser warning). The action is then attached to a
certificate via its ``restartActions`` field.

Endpoints:
    search  GET  acmeclient/actions/search
    get     GET  acmeclient/actions/get/{uuid}
    create  POST acmeclient/actions/add
    update  POST acmeclient/actions/update/{uuid}
    delete  POST acmeclient/actions/del/{uuid}
    apply   None — stored immediately; reconfigure via AcmeServiceManager.

Redact fields: remote-target credentials (passwords / tokens / api keys).
Reference: https://github.com/opnsense/plugins/tree/master/security/acme-client
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class AcmeActionManager(BaseManager):
    """Manage os-acme-client automation actions via /api/acmeclient/actions.

    Inherits the full CRUD + ``ensure()`` lifecycle from :class:`BaseManager`.

    Usage (restart the WebGUI after a cert update)::

        async with OpnsenseClient(...) as client:
            mgr = AcmeActionManager(client)
            await mgr.ensure("present", {
                "name": "restart-webgui",
                "type": "configd_restart_gui",
            })

    Input (ensure present):
        name:        Action name (required, match key).
        type:        Action type — e.g. 'configd_restart_gui',
                     'configd_restart_haproxy', 'configd_restart_nginx',
                     'configd_reload_caddy', 'configd_upload_sftp',
                     'configd_remote_ssh', 'configd_generic', 'acme_*' targets.
        description: Free-text description.
        enabled:     '1' / '0'.
        (Upload/remote types add their own sftp_* / remote_ssh_* / acme_* fields,
        which pass through ``ensure(params=...)``.)

    REDACT_FIELDS: remote-target credentials.

    Output (EnsureResult): standard created/updated/deleted/noop.
    """

    _endpoint = "acmeclient/actions"
    _payload_key = "action"
    _entity_suffix = ""
    _update_action = "update"  # acmeclient: set/{uuid} says "saved" but is the whole-model setter
    _apply_endpoint = None
    _match_key = "name"

    # Credential fields across the remote-target action types.
    REDACT_FIELDS: set[str] = {
        "acme_synology_dsm_password",
        "acme_fritzbox_password",
        "acme_panos_password",
        "acme_proxmoxve_tokenkey",
        "acme_proxmoxbs_tokenkey",
        "acme_ruckus_pass",
        "acme_truenas_apikey",
        "acme_truenas_ws_apikey",
        "acme_truenasws_apikey",
    }

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "description": {"type": "str", "max_length": 255},
        "type": {
            "type": "enum",
            "values": [
                "configd_restart_gui",
                "configd_restart_haproxy",
                "configd_restart_nginx",
                "configd_reload_caddy",
                "configd_upload_sftp",
                "configd_remote_ssh",
                "configd_generic",
                "acme_fritzbox",
                "acme_panos",
                "acme_proxmoxbs",
                "acme_proxmoxve",
                "acme_ruckus",
                "acme_vault",
                "acme_synology_dsm",
                "acme_truenas",
                "acme_truenas_ws",
                "acme_zyxel_gs1900",
                "acme_unifi",
            ],
        },
        "enabled": {"type": "bool_str"},
        "sftp_port": {"type": "str", "max_length": 5},
        "remote_ssh_port": {"type": "str", "max_length": 5},
        "sftp_identity_type": {"type": "enum", "values": ["", "ecdsa", "rsa", "ed25519"]},
        "remote_ssh_identity_type": {"type": "enum", "values": ["", "ecdsa", "rsa", "ed25519"]},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the ACME action manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
