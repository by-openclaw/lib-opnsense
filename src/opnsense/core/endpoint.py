# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Endpoint resolution — URL construction from config.

Replaces inline f-strings in BaseManager with a declarative config
that maps CRUD actions to OPNsense API endpoint paths.

Zero imports from managers/ or client.py — independently reusable.

Usage::

    from opnsense.core.endpoint import EndpointConfig, EndpointResolver

    config = EndpointConfig(
        base="firewall/filter",
        payload_key="rule",
        entity_suffix="Rule",
        apply_endpoint="firewall/filter/apply",
    )
    resolver = EndpointResolver(config)
    url = resolver.search()   # "firewall/filter/searchRule"
    url = resolver.add()      # "firewall/filter/addRule"
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EndpointConfig:
    """Declarative endpoint configuration for a manager.

    Args:
        base:           API domain path (e.g. 'firewall/filter').
        payload_key:    Top-level JSON key for payloads (e.g. 'rule').
        entity_suffix:  Suffix appended to CRUD actions (e.g. 'Rule', 'Item', '').
                        None = auto-capitalize payload_key.
        apply_endpoint: Reconfigure endpoint, or None if changes are immediate.
    """

    base: str
    payload_key: str
    entity_suffix: str | None = None
    apply_endpoint: str | None = None

    @property
    def suffix(self) -> str:
        """Resolve entity suffix for endpoint URLs."""
        if self.entity_suffix is not None:
            return self.entity_suffix
        return self.payload_key.capitalize()


class EndpointResolver:
    """Construct OPNsense API endpoint URLs from config.

    Args:
        config: An :class:`EndpointConfig` instance.
    """

    def __init__(self, config: EndpointConfig) -> None:
        """Initialise the resolver with endpoint configuration."""
        self._config = config

    @property
    def config(self) -> EndpointConfig:
        """Return the endpoint configuration."""
        return self._config

    def search(self) -> str:
        """Search endpoint: ``{base}/search{Suffix}``."""
        return f"{self._config.base}/search{self._config.suffix}"

    def get(self, uuid: str = "") -> str:
        """Get endpoint: ``{base}/get{Suffix}/{uuid}`` or schema if no uuid."""
        if uuid:
            return f"{self._config.base}/get{self._config.suffix}/{uuid}"
        return f"{self._config.base}/get{self._config.suffix}"

    def add(self) -> str:
        """Add endpoint: ``{base}/add{Suffix}``."""
        return f"{self._config.base}/add{self._config.suffix}"

    def set(self) -> str:
        """Set endpoint: ``{base}/set{Suffix}``."""
        return f"{self._config.base}/set{self._config.suffix}"

    def delete(self) -> str:
        """Delete endpoint: ``{base}/del{Suffix}``."""
        return f"{self._config.base}/del{self._config.suffix}"

    def apply(self) -> str | None:
        """Apply/reconfigure endpoint, or None if changes are immediate."""
        return self._config.apply_endpoint
