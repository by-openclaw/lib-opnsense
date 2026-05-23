# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense radvd entry model — typed frozen dataclass.

Maps to OPNsense API: ``/api/radvd/settings``
Payload key: ``entry``
Match key:   ``interface`` (one RA entry per interface)

Schema discovered from ``GET /api/radvd/settings/getEntry`` on OPNsense 26.1.

Reference: https://docs.opnsense.org/manual/router_advertisements.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RadvdEntry:
    """Per-interface IPv6 Router Advertisement entry from radvd/settings API.

    Attributes:
        interface:        OPNsense interface slot (e.g. ``'opt2'``) — the
                          unique identity key.
        enabled:          Whether the entry is active (``'0'`` or ``'1'``).
        Base6Interface:   Slot of the interface providing the GUA prefix to
                          advertise (``''`` = none, use static).
        mode:             RA mode — one of ``'router'`` (router-only),
                          ``'unmanaged'`` (SLAAC, no DHCPv6),
                          ``'managed'`` (DHCPv6 stateful for addresses),
                          ``'assist'`` (managed addresses + assisted other),
                          ``'stateless'`` (SLAAC + DHCPv6 for DNS/options).
        DeprecatePrefix:  ``''`` (auto) | ``'on'`` | ``'off'``.
        RemoveAdvOnExit:  ``''`` (auto) | ``'on'`` | ``'off'``.
        RemoveRoute:      ``''`` (auto) | ``'on'`` | ``'off'``.
        uuid:             Resource UUID assigned by OPNsense.

    Notes:
        OPNsense exposes additional radvd fields (MTU, prefix lifetimes,
        DNS, etc.) that are not modelled here yet — manager validators
        accept the documented core fields; extras pass through untouched.
        Extend this model and the manager's ``_validators`` when richer
        coverage is needed.
    """

    interface: str
    enabled: str = "1"
    Base6Interface: str = ""  # noqa: N815  matches OPNsense camelCase field
    mode: str = "stateless"
    DeprecatePrefix: str = ""  # noqa: N815  matches OPNsense camelCase field
    RemoveAdvOnExit: str = ""  # noqa: N815  matches OPNsense camelCase field
    RemoveRoute: str = ""  # noqa: N815  matches OPNsense camelCase field
    uuid: str = ""
