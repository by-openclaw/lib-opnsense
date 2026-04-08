# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense traffic shaper pipe model — typed frozen dataclass.

Maps to OPNsense API: ``/api/trafficshaper/settings``
Payload key: ``pipe``
Match keys: ``['description', 'bandwidth', 'bandwidthMetric']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TsPipe:
    """Traffic shaper pipe entity from OPNsense trafficshaper/settings API.

    Attributes:
        description:      Pipe description (required, max 255).
        bandwidth:        Bandwidth value (required, min 1).
        bandwidthMetric:  Bandwidth unit ('bit', 'Kbit', 'Mbit', 'Gbit').
        enabled:          Whether the pipe is enabled ('0' or '1').
        uuid:             Resource UUID assigned by OPNsense.
    """

    description: str
    bandwidth: str = ""
    bandwidthMetric: str = "Mbit"
    enabled: str = "1"
    uuid: str = ""
