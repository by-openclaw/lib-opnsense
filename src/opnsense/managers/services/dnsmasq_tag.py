# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq DHCP tag manager.

API domain: /api/dnsmasq/settings
Payload key: tag
Match key:   tag (the unique tag name)
Entity suffix: Tag

Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class DnsmasqTagManager(BaseManager):
    """Manage named Dnsmasq DHCP tags.

    Identity is the ``tag`` field. **Server enforces uniqueness** —
    creating a second entry with the same tag raises
    ``OpnsenseValidationError`` (``'Tag names should be unique'``), so
    ``AmbiguousMatchError`` is only reachable in unit tests via mocked
    duplicate search results.

    Input (ensure present):
        tag: Tag name (required, identity). Must be **alphanumeric only** —
             OPNsense rejects hyphens and underscores with
             ``'Text does not validate'`` (verified via probe).

    Output (EnsureResult): standard CRUD result.
    """

    _endpoint = "dnsmasq/settings"
    _payload_key = "tag"
    _entity_suffix = "Tag"
    _apply_endpoint = "dnsmasq/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["tag"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "tag": {"type": "str", "required": True, "max_length": 64},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Dnsmasq tag manager."""
        super().__init__(client)
