# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME action model — typed frozen dataclass.

Maps to OPNsense API: ``/api/acmeclient/actions`` (os-acme-client plugin)
Payload key: ``action``
Match key: ``name``

An action is an automation run after a certificate is issued/renewed — most
commonly restarting a local service so it picks up the new leaf. The platform
uses ``type='configd_restart_gui'`` to restart the OPNsense WebGUI so the new
ACME cert is served without a browser warning.

The action model is polymorphic on ``type``: each type uses a different subset
of fields. This dataclass types the **identity** fields plus the **local
service** types we use (``configd_restart_gui`` / ``configd_generic_command``)
and the generic ``sftp`` / ``remote_ssh`` upload types. The many remote-target
provider fields (``acme_proxmoxve_*``, ``acme_synology_dsm_*``, ``acme_truenas_*``,
…) are NOT enumerated here but pass straight through
``AcmeActionManager.ensure(params=...)``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcmeAction:
    """ACME automation action entity from os-acme-client ``actions`` API.

    Attributes:
        name:                    Action name (match key, required).
        description:             Free-text description.
        type:                    Action type — e.g. ``configd_restart_gui``,
                                 ``configd_restart_haproxy``, ``configd_restart_nginx``,
                                 ``configd_reload_caddy``, ``configd_upload_sftp``,
                                 ``configd_remote_ssh``, ``configd_generic``,
                                 ``acme_*`` remote-target types.
        enabled:                 ``"1"`` / ``"0"``.
        configd:                 configd command (``configd_*`` restart types).
        configd_generic_command: configd command (``configd_generic`` type).
        sftp_host:               SFTP upload host (``configd_upload_sftp``).
        sftp_host_key:           SFTP known-host key.
        sftp_port:               SFTP port.
        sftp_user:               SFTP username.
        sftp_identity_type:      SFTP key type — ``ecdsa`` / ``rsa`` / ``ed25519``.
        sftp_remote_path:        Remote directory for uploaded files.
        remote_ssh_host:         Remote SSH host (``configd_remote_ssh``).
        remote_ssh_host_key:     Remote SSH known-host key.
        remote_ssh_port:         Remote SSH port.
        remote_ssh_user:         Remote SSH username.
        remote_ssh_identity_type: Remote SSH key type.
        remote_ssh_command:      Command to run over SSH after upload.
        id:                      Internal model id (read-only).
        uuid:                    Resource UUID assigned by OPNsense.
    """

    name: str
    description: str = ""
    type: str = "configd_restart_gui"
    enabled: str = "1"
    configd: str = ""
    configd_generic_command: str = ""
    # SFTP upload
    sftp_host: str = ""
    sftp_host_key: str = ""
    sftp_port: str = "22"
    sftp_user: str = ""
    sftp_identity_type: str = ""
    sftp_remote_path: str = ""
    # Remote SSH
    remote_ssh_host: str = ""
    remote_ssh_host_key: str = ""
    remote_ssh_port: str = "22"
    remote_ssh_user: str = ""
    remote_ssh_identity_type: str = ""
    remote_ssh_command: str = ""
    id: str = ""
    uuid: str = ""
