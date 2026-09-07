# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense mDNS repeater (os-mdns-repeater) service controller.

API domain: /api/mdnsrepeater/service
Pattern:    BaseServiceManager — idempotent state transitions.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class MdnsRepeaterServiceManager(BaseServiceManager):
    """Control the mDNS repeater service (``disabled`` while switched off in its settings)."""

    _endpoint = "mdnsrepeater/service"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
