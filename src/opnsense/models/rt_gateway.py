# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense routing gateway model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/routing/settings``
Payload key: ``gateway_item``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RtGateway:
    """Routing gateway entity from OPNsense routing/settings API.

    Attributes:
        name:        Gateway name (required, match key).
        interface:   Interface name (required).
        gateway:     Gateway IP address (required).
        ipprotocol:  IP protocol ('inet' or 'inet6').
        defaultgw:   Default gateway flag ('0' or '1').
        disabled:    Disabled flag ('0' or '1').
        descr:       Description.
        priority:    Priority (0-255).
        weight:      Weight (1-5).
        fargw:       Far gateway ('0' or '1').
        force_down:  Force gateway down ('0' or '1').
        monitor:     Monitor IP address.
        monitor_disable:             Disable monitoring ('0' or '1').
        monitor_noroute:             Monitor no-route ('0' or '1').
        monitor_killstates:          Kill states on down ('0' or '1').
        monitor_killstates_priority: Kill states priority ('0' or '1').
        latencylow:  Low latency threshold (ms).
        latencyhigh: High latency threshold (ms).
        losslow:     Low loss threshold (%).
        losshigh:    High loss threshold (%).
        interval:    Probe interval.
        time_period: Time period.
        loss_interval: Loss interval.
        data_length: Probe data length.
        uuid:        Resource UUID assigned by OPNsense.
    """

    name: str
    interface: str = ""
    gateway: str = ""
    ipprotocol: str = "inet"
    defaultgw: str = "0"
    disabled: str = "0"
    descr: str = ""
    priority: str = "255"
    weight: str = "1"
    fargw: str = "0"
    force_down: str = "0"
    monitor: str = ""
    monitor_disable: str = "1"
    monitor_noroute: str = "0"
    monitor_killstates: str = "0"
    monitor_killstates_priority: str = "0"
    latencylow: str = ""
    latencyhigh: str = ""
    losslow: str = ""
    losshigh: str = ""
    interval: str = ""
    time_period: str = ""
    loss_interval: str = ""
    data_length: str = ""
    uuid: str = ""
