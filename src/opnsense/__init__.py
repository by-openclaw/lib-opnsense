# Copyright (c) 2026 BY-SYSTEMS. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense REST API client library.

Async/await Python client for OPNsense firewall management.
Provides typed managers with ensure() idempotency for all API domains.
"""

__version__ = "0.1.0"

from opnsense.client import OpnsenseClient
from opnsense.exceptions import (
    OpnsenseAuthError,
    OpnsenseConnectionError,
    OpnsenseEndpointMissingError,
    OpnsenseError,
    OpnsenseTimeoutError,
    OpnsenseValidationError,
)

__all__ = [
    "OpnsenseClient",
    "OpnsenseError",
    "OpnsenseAuthError",
    "OpnsenseConnectionError",
    "OpnsenseEndpointMissingError",
    "OpnsenseTimeoutError",
    "OpnsenseValidationError",
]
