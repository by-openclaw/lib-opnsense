# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense REST API client — async/await with httpx.

Provides low-level CRUD operations against the OPNsense API with:
- Automatic retry with exponential backoff for 500/network errors
- Status code -> typed exception mapping
- Secret redaction in error messages
- Async context manager lifecycle
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import httpx

from .exceptions import (
    OpnsenseAuthError,
    OpnsenseConnectionError,
    OpnsenseEndpointMissingError,
    OpnsenseError,
    OpnsensePermissionError,
    OpnsenseServerError,
    OpnsenseTimeoutError,
    OpnsenseValidationError,
)

logger = logging.getLogger(__name__)

# Map HTTP status codes to typed exceptions.
_STATUS_MAP: dict[int, type[OpnsenseError]] = {
    400: OpnsenseValidationError,
    401: OpnsenseAuthError,
    403: OpnsensePermissionError,
    404: OpnsenseEndpointMissingError,
    500: OpnsenseServerError,
}


class OpnsenseClient:
    """Async OPNsense REST API client.

    All configuration is injected via constructor (ADR-0029).
    Uses httpx.AsyncClient internally for HTTP/2 and connection pooling.

    Usage::

        async with OpnsenseClient(host="fw.example.com", key="...", secret="...") as client:
            users = await client.search("auth/user/searchUser")
            print(users)
    """

    def __init__(
        self,
        host: str,
        key: str,
        secret: str,
        port: int = 443,
        verify_ssl: bool = False,
        timeout: int = 30,
        async_timeout: int = 300,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
    ) -> None:
        """Initialise the OPNsense API client.

        Args:
            host:          OPNsense hostname or IP address.
            key:           API key (from System > Access > Users > API keys).
            secret:        API secret corresponding to the key.
            port:          HTTPS port (default 443).
            verify_ssl:    Verify TLS certificate. False for self-signed certs.
            timeout:       Default HTTP request timeout in seconds.
            async_timeout: Timeout for long-running operations (wait_for_ready).
            max_retries:   Maximum retry attempts for 500/network errors.
            retry_backoff: Base delay multiplier for exponential backoff.
        """
        self._host = host
        self._key = key
        self._secret = secret
        self._port = port
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._async_timeout = async_timeout
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._http: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        """Build base URL from host and port."""
        return f"https://{self._host}:{self._port}/api"

    async def _ensure_http(self) -> httpx.AsyncClient:
        """Return the httpx client, creating it if needed."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                auth=(self._key, self._secret),
                verify=self._verify_ssl,
                timeout=httpx.Timeout(self._timeout),
            )
        return self._http

    async def __aenter__(self) -> OpnsenseClient:
        """Enter the async context manager."""
        await self._ensure_http()
        return self

    async def __aexit__(self, *_: Any) -> None:
        """Exit the async context manager — close the HTTP client."""
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    def _redact_secret(self, text: str) -> str:
        """Replace API secret in error messages with <REDACTED:api_secret>."""
        if self._secret and self._secret in text:
            text = text.replace(self._secret, "<REDACTED:api_secret>")
        if self._key and self._key in text:
            text = text.replace(self._key, "<REDACTED:api_key>")
        return text

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with retry logic and exception mapping.

        Args:
            method:   HTTP method ('GET' or 'POST').
            endpoint: API path relative to /api/ (e.g. 'auth/user/searchUser').
            data:     JSON body for POST requests.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            OpnsenseAuthError:            On HTTP 401.
            OpnsensePermissionError:      On HTTP 403.
            OpnsenseEndpointMissingError: On HTTP 404.
            OpnsenseValidationError:      On HTTP 400 or result=failed.
            OpnsenseServerError:          On HTTP 500 (after retries exhausted).
            OpnsenseTimeoutError:         On request timeout.
            OpnsenseConnectionError:      On network-level failure.
        """
        http = await self._ensure_http()
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = await http.get(f"/{endpoint}")
                else:
                    response = await http.post(
                        f"/{endpoint}",
                        json=data or {},
                        headers={"Content-Type": "application/json"},
                    )

                # Non-retryable HTTP errors — raise immediately
                if response.status_code in (400, 401, 403, 404):
                    self._raise_for_status(response, endpoint)

                # Retryable server error
                if response.status_code >= 500:
                    if attempt < self._max_retries:
                        delay = self._retry_backoff**attempt
                        logger.error(
                            "OPNsense %s %s returned %d, retrying in %.1fs (attempt %d/%d)",
                            method,
                            endpoint,
                            response.status_code,
                            delay,
                            attempt,
                            self._max_retries,
                        )
                        await asyncio.sleep(delay)
                        continue
                    self._raise_for_status(response, endpoint)

                # Success — parse JSON
                body: dict[str, Any] = response.json()

                # OPNsense returns result=failed for validation errors on 200
                if isinstance(body, dict) and body.get("result") == "failed":
                    validations = body.get("validations", {})
                    raise OpnsenseValidationError(
                        message=f"Validation failed on {endpoint}",
                        endpoint=endpoint,
                        validations=validations,
                    )

                return body

            except (
                OpnsenseAuthError,
                OpnsensePermissionError,
                OpnsenseEndpointMissingError,
                OpnsenseValidationError,
            ):
                raise  # Non-retryable — propagate immediately

            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = self._retry_backoff**attempt
                    logger.error(
                        "OPNsense %s %s timed out, retrying in %.1fs (attempt %d/%d)",
                        method,
                        endpoint,
                        delay,
                        attempt,
                        self._max_retries,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise OpnsenseTimeoutError(
                    message=self._redact_secret(
                        f"Request timed out after {self._timeout}s: {method} {endpoint}"
                    ),
                    endpoint=endpoint,
                ) from exc

            except httpx.ConnectError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = self._retry_backoff**attempt
                    logger.error(
                        "OPNsense %s %s connection error, retrying in %.1fs (attempt %d/%d)",
                        method,
                        endpoint,
                        delay,
                        attempt,
                        self._max_retries,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise OpnsenseConnectionError(
                    message=self._redact_secret(f"Connection failed: {method} {endpoint}: {exc}"),
                    endpoint=endpoint,
                ) from exc

        # Should not reach here, but guard against it
        raise OpnsenseError(
            message=f"Request failed after {self._max_retries} attempts: {method} {endpoint}",
            endpoint=endpoint,
        ) from last_exc

    def _raise_for_status(
        self,
        response: httpx.Response,
        endpoint: str,
    ) -> None:
        """Map HTTP status code to typed exception and raise.

        Args:
            response: The httpx response object.
            endpoint: API endpoint for error context.

        Raises:
            OpnsenseError: Always raises a typed subclass.
        """
        status = response.status_code
        exc_class = _STATUS_MAP.get(status, OpnsenseError)

        # Try to extract message from response body
        try:
            body = response.json()
            detail = body.get("message", body.get("errorMessage", ""))
        except Exception:
            detail = response.text[:200] if response.text else ""

        message = self._redact_secret(
            f"HTTP {status} on {endpoint}" + (f": {detail}" if detail else "")
        )

        if exc_class is OpnsenseValidationError:
            validations: dict[str, str] = {}
            with contextlib.suppress(Exception):
                validations = response.json().get("validations", {})
            raise OpnsenseValidationError(
                message=message,
                endpoint=endpoint,
                validations=validations,
            )

        if exc_class in (
            OpnsenseAuthError,
            OpnsensePermissionError,
            OpnsenseEndpointMissingError,
            OpnsenseServerError,
        ):
            raise exc_class(message=message, endpoint=endpoint)

        raise OpnsenseError(
            message=message,
            status_code=status,
            endpoint=endpoint,
        )

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def get(self, endpoint: str) -> dict[str, Any]:
        """GET an API endpoint.

        Args:
            endpoint: API path relative to /api/ (e.g. 'auth/user/getUser/uuid').

        Returns:
            Parsed JSON response dict.
        """
        return await self._request("GET", endpoint)

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST to an API endpoint.

        Args:
            endpoint: API path relative to /api/.
            data:     JSON body payload.

        Returns:
            Parsed JSON response dict.
        """
        return await self._request("POST", endpoint, data=data)

    async def search(
        self,
        endpoint: str,
        search_phrase: str = "",
        row_count: int = 50,
    ) -> list[dict[str, Any]]:
        """Search an API endpoint with pagination.

        OPNsense search endpoints return ``{"rows": [...], "rowCount": N, ...}``.
        This method extracts and returns the ``rows`` list.

        Args:
            endpoint:      Search endpoint (e.g. 'auth/user/searchUser').
            search_phrase: Optional filter string.
            row_count:     Maximum rows to return (default 50).

        Returns:
            List of result dicts from the ``rows`` key.
        """
        body = await self.post(
            endpoint,
            data={
                "searchPhrase": search_phrase,
                "rowCount": row_count,
                "current": 1,
            },
        )
        return body.get("rows", [])

    async def get_schema(self, endpoint: str) -> dict[str, Any]:
        """GET an empty schema for a resource type.

        Used to discover available fields and defaults before creating.

        Args:
            endpoint: Schema endpoint (e.g. 'auth/user/getUser').

        Returns:
            Parsed JSON schema dict.
        """
        return await self.get(endpoint)

    async def create(
        self,
        endpoint: str,
        payload_key: str,
        params: dict[str, Any],
    ) -> str:
        """Create a resource and return its UUID.

        Args:
            endpoint:    Create endpoint (e.g. 'auth/user/addUser').
            payload_key: Top-level key wrapping the params (e.g. 'user').
            params:      Resource field values.

        Returns:
            UUID of the created resource.

        Raises:
            OpnsenseValidationError: If validation fails.
            OpnsenseError:           If the response lacks a uuid field.
        """
        body = await self.post(endpoint, data={payload_key: params})
        uuid = body.get("uuid")
        if not uuid:
            raise OpnsenseError(
                message=f"Create succeeded but no UUID in response: {endpoint}",
                endpoint=endpoint,
            )
        return uuid

    async def update(
        self,
        endpoint: str,
        uuid: str,
        payload_key: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a resource by UUID.

        Args:
            endpoint:    Update endpoint base (e.g. 'auth/user/setUser').
            uuid:        Resource UUID.
            payload_key: Top-level key wrapping the params (e.g. 'user').
            params:      Fields to update.

        Returns:
            Parsed JSON response dict.
        """
        return await self.post(
            f"{endpoint}/{uuid}",
            data={payload_key: params},
        )

    async def delete(
        self,
        endpoint: str,
        uuid: str,
    ) -> dict[str, Any]:
        """Delete a resource by UUID.

        Args:
            endpoint: Delete endpoint base (e.g. 'auth/user/delUser').
            uuid:     Resource UUID.

        Returns:
            Parsed JSON response dict.
        """
        return await self.post(f"{endpoint}/{uuid}")

    async def reconfigure(self, endpoint: str) -> dict[str, Any]:
        """Trigger a service reconfigure/apply.

        Many OPNsense modules require an explicit reconfigure call after
        CRUD operations to apply changes to the running configuration.

        Args:
            endpoint: Reconfigure endpoint (e.g. 'unbound/service/reconfigure').

        Returns:
            Parsed JSON response dict.
        """
        return await self.post(endpoint)

    async def wait_for_ready(
        self,
        check_endpoint: str,
        timeout: float | None = None,
        interval: float = 3.0,
    ) -> dict[str, Any]:
        """Poll an endpoint until the service reports ready.

        Useful after reconfigure or firmware update operations that take
        an indeterminate amount of time.

        Args:
            check_endpoint: Status endpoint to poll (e.g. 'core/firmware/status').
            timeout:        Maximum wait time in seconds. Defaults to async_timeout.
            interval:       Seconds between polls.

        Returns:
            The final successful response dict.

        Raises:
            OpnsenseTimeoutError: If the timeout expires before ready.
        """
        effective_timeout = timeout if timeout is not None else self._async_timeout
        elapsed = 0.0

        while elapsed < effective_timeout:
            try:
                result = await self.get(check_endpoint)
                status = result.get("status", "")
                if status in ("running", "done", "ok"):
                    return result
            except (OpnsenseConnectionError, OpnsenseTimeoutError, OpnsenseServerError):
                pass  # Transient — keep polling

            await asyncio.sleep(interval)
            elapsed += interval

        raise OpnsenseTimeoutError(
            message=(f"Service not ready after {effective_timeout}s polling {check_endpoint}"),
            endpoint=check_endpoint,
        )
