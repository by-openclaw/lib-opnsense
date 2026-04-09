# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense cron job model — typed frozen dataclass.

Maps to OPNsense API: ``/api/cron/settings``
Payload key: ``job``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CronJob:
    """Cron job entity from OPNsense cron/settings API.

    Attributes:
        description: Job description (required).
        enabled:     Whether the job is enabled ('0' or '1').
        minutes:     Cron minutes field (e.g. '0', '*/5').
        hours:       Cron hours field (e.g. '0', '3').
        days:        Cron days field (e.g. '*', '1,15').
        months:      Cron months field (e.g. '*', '1-6').
        weekdays:    Cron weekdays field (e.g. '*', '1-5').
        command:     Command to execute (OPNsense action name).
        who:         User to run as (default 'root').
        parameters:  Additional parameters for the command.
        uuid:        Resource UUID assigned by OPNsense.
    """

    description: str
    enabled: str = "1"
    minutes: str = "0"
    hours: str = "0"
    days: str = "*"
    months: str = "*"
    weekdays: str = "*"
    command: str = ""
    who: str = "root"
    parameters: str = ""
    uuid: str = ""
