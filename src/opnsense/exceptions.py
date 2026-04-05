# Copyright (c) 2026 BY-SYSTEMS. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense — typed exception hierarchy.

All exceptions carry optional ``status_code`` and ``endpoint`` attributes
for structured error handling in automation drivers.

HTTP status code mapping:
    401 -> OpnsenseAuthError
    403 -> OpnsensePermissionError
    404 -> OpnsenseEndpointMissingError (plugin not installed or legacy PHP)
    400 -> OpnsenseValidationError (also raised on result=failed)
    500 -> OpnsenseServerError
    timeout -> OpnsenseTimeoutError
    network -> OpnsenseConnectionError
"""

from __future__ import annotations


class OpnsenseError(Exception):
    """Base exception for all OPNsense API errors.

    Attributes:
        message:     Human-readable error description.
        status_code: HTTP status code, or None for non-HTTP errors.
        endpoint:    API endpoint that triggered the error, or None.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialise the exception.

        Args:
            message:     Human-readable error description.
            status_code: HTTP status code, or None for non-HTTP errors.
            endpoint:    API endpoint path, or None.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.endpoint = endpoint

    def __str__(self) -> str:
        """Format as 'message [status_code endpoint]' when context is available."""
        parts = [self.message]
        if self.status_code is not None or self.endpoint is not None:
            ctx = " ".join(
                str(v)
                for v in [self.status_code, self.endpoint]
                if v is not None
            )
            parts.append(f"[{ctx}]")
        return " ".join(parts)


class OpnsenseAuthError(OpnsenseError):
    """Authentication failure — HTTP 401.

    Raised when the API key/secret pair is invalid or revoked.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        endpoint: str | None = None,
    ) -> None:
        """Initialise with status_code fixed to 401."""
        super().__init__(message, status_code=401, endpoint=endpoint)


class OpnsensePermissionError(OpnsenseError):
    """Insufficient permissions — HTTP 403.

    Raised when the API key lacks privileges for the requested endpoint.
    """

    def __init__(
        self,
        message: str = "Permission denied",
        endpoint: str | None = None,
    ) -> None:
        """Initialise with status_code fixed to 403."""
        super().__init__(message, status_code=403, endpoint=endpoint)


class OpnsenseEndpointMissingError(OpnsenseError):
    """Endpoint not found — HTTP 404.

    Raised when the API endpoint does not exist. Common causes:
    - Required OPNsense plugin is not installed
    - Endpoint path changed between OPNsense versions
    - Legacy PHP endpoint not available on this firmware
    """

    def __init__(
        self,
        message: str = "Endpoint not found (plugin not installed?)",
        endpoint: str | None = None,
    ) -> None:
        """Initialise with status_code fixed to 404."""
        super().__init__(message, status_code=404, endpoint=endpoint)


class OpnsenseValidationError(OpnsenseError):
    """Validation failure — HTTP 400 or API result=failed.

    Carries a ``validations`` dict mapping field names to error messages,
    as returned by the OPNsense API validation layer.

    Attributes:
        validations: Dict of field-level validation errors from the API.
    """

    def __init__(
        self,
        message: str = "Validation failed",
        endpoint: str | None = None,
        validations: dict[str, str] | None = None,
    ) -> None:
        """Initialise with status_code 400 and optional validations dict.

        Args:
            message:     Human-readable error description.
            endpoint:    API endpoint path, or None.
            validations: Field-level validation errors from the OPNsense API.
        """
        super().__init__(message, status_code=400, endpoint=endpoint)
        self.validations = validations or {}

    def __str__(self) -> str:
        """Include validation details when present."""
        base = super().__str__()
        if self.validations:
            fields = "; ".join(
                f"{k}: {v}" for k, v in self.validations.items()
            )
            return f"{base} — {fields}"
        return base


class OpnsenseTimeoutError(OpnsenseError):
    """Request timed out.

    Wraps asyncio.TimeoutError so callers can catch OPNsense-specific
    timeouts without importing asyncio.
    """

    def __init__(
        self,
        message: str = "Request timed out",
        endpoint: str | None = None,
    ) -> None:
        """Initialise with no status_code (timeout is not an HTTP status)."""
        super().__init__(message, status_code=None, endpoint=endpoint)


class OpnsenseConnectionError(OpnsenseError):
    """Network-level failure — cannot reach the OPNsense host.

    Wraps httpx connection errors (DNS failure, connection refused, TLS error)
    so callers never need to import httpx internals.
    """

    def __init__(
        self,
        message: str = "Connection failed",
        endpoint: str | None = None,
    ) -> None:
        """Initialise with no status_code (network errors have no HTTP response)."""
        super().__init__(message, status_code=None, endpoint=endpoint)


class OpnsenseServerError(OpnsenseError):
    """Server-side error — HTTP 500.

    Indicates an internal OPNsense error. These are typically transient
    and may succeed on retry (handled by client retry logic).
    """

    def __init__(
        self,
        message: str = "Internal server error",
        endpoint: str | None = None,
    ) -> None:
        """Initialise with status_code fixed to 500."""
        super().__init__(message, status_code=500, endpoint=endpoint)
