# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME certificate model — typed frozen dataclass.

Maps to OPNsense API: ``/api/acmeclient/certificates`` (os-acme-client plugin)
Payload key: ``certificate``
Match key: ``name``

A certificate ties together a CN/SANs, an ``account`` (which CA), a
``validationMethod`` (how to prove control) and optional ``restartActions``
(what to run after issue/renew). It is materialised into the OPNsense trust
store under ``certRefId`` once signed (``sign`` verb), so other subsystems
(WebGUI, HAProxy, OpenVPN) can reference the resulting leaf by refid.

Reference fields — ``account``, ``validationMethod``, ``restartActions`` — are
sent as UUID strings on write (``restartActions`` comma-separated for multiple)
and returned as option-dicts on read; the DiffEngine normalises both shapes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcmeCertificate:
    """ACME certificate entity from os-acme-client ``certificates`` API.

    Attributes:
        name:             Certificate name / primary domain (match key, required).
        description:      Free-text description.
        altNames:         Subject Alternative Names (additional domains).
        account:          UUID of the ``AcmeAccount`` (CA) to use.
        validationMethod: UUID of the ``AcmeValidation`` (challenge) to use.
        keyLength:        ``key_2048`` / ``key_3072`` / ``key_4096`` /
                          ``key_ec256`` / ``key_ec384``.
        ocsp:             Enable OCSP Must-Staple (``"1"``/``"0"``).
        profile:          ACME profile name (CA-specific; usually empty).
        restartActions:   UUID(s) of ``AcmeAction`` to run post-issue
                          (comma-separated for multiple).
        autoRenewal:      Auto-renew this certificate (``"1"``/``"0"``).
        renewInterval:    Renew when this many days remain.
        aliasmode:        ``none`` / ``automatic`` / ``domain`` / ``challenge``.
        domainalias:      Domain alias (when ``aliasmode='domain'``).
        challengealias:   Challenge alias (when ``aliasmode='challenge'``).
        certRefId:        Trust-store refid of the issued leaf (read-only).
        enabled:          ``"1"`` / ``"0"``.
        lastUpdate:       Last issue/renew timestamp (read-only).
        statusCode:       Last issue status code (read-only).
        statusLastUpdate: Last status timestamp (read-only).
        id:               Internal model id (read-only).
        uuid:             Resource UUID assigned by OPNsense.
    """

    name: str
    description: str = ""
    altNames: str = ""
    account: str = ""
    validationMethod: str = ""
    keyLength: str = "key_4096"
    ocsp: str = "0"
    profile: str = ""
    restartActions: str = ""
    autoRenewal: str = "1"
    renewInterval: str = "60"
    aliasmode: str = "none"
    domainalias: str = ""
    challengealias: str = ""
    certRefId: str = ""
    enabled: str = "1"
    lastUpdate: str = ""
    statusCode: str = ""
    statusLastUpdate: str = ""
    id: str = ""
    uuid: str = ""
