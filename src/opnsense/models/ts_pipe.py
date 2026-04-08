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
        delay:            Pipe delay in ms.
        mask:             Mask type (none, src-ip, dst-ip, src-ip6, dst-ip6).
        buckets:          Hash buckets.
        scheduler:        Scheduler ('', fifo, wf2q+, rr, qfq, fq_codel, fq_pie).
        codel_enable:     Whether CoDel AQM is enabled ('0' or '1').
        codel_target:     CoDel target delay.
        codel_interval:   CoDel interval.
        codel_ecn_enable: Whether CoDel ECN is enabled ('0' or '1').
        pie_enable:       Whether PIE AQM is enabled ('0' or '1').
        fqcodel_flows:    FQ-CoDel flows.
        fqcodel_limit:    FQ-CoDel limit.
        fqcodel_quantum:  FQ-CoDel quantum.
        uuid:             Resource UUID assigned by OPNsense.
    """

    description: str
    bandwidth: str = ""
    bandwidthMetric: str = "Mbit"
    enabled: str = "1"
    delay: str = ""
    mask: str = "none"
    buckets: str = ""
    scheduler: str = ""
    codel_enable: str = "0"
    codel_target: str = ""
    codel_interval: str = ""
    codel_ecn_enable: str = "0"
    pie_enable: str = "0"
    fqcodel_flows: str = ""
    fqcodel_limit: str = ""
    fqcodel_quantum: str = ""
    uuid: str = ""
