# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense interface LAGG model — typed frozen dataclass.

Maps to OPNsense API: ``/api/interfaces/lagg_settings``
Payload key: ``lagg``
Match key: ``descr``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IfLagg:
    """LAGG interface entity from OPNsense interfaces/lagg_settings API.

    Attributes:
        descr:              Description (match key, required).
        members:            Member interfaces (comma-separated).
        proto:              Aggregation protocol (lacp, failover, etc.).
        lacp_fast_timeout:  LACP fast timeout ('0' or '1').
        mtu:                Maximum transmission unit.
        uuid:               Resource UUID assigned by OPNsense.
    """

    descr: str
    members: str = ""
    proto: str = "lacp"
    lacp_fast_timeout: str = "0"
    mtu: str = ""
    uuid: str = ""
