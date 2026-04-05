# Copyright (c) 2026 BY-SYSTEMS. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
# ADR: 0029 (Python Library Design Standard), 0011 (Secret Storage Convention)
"""Credential providers for OPNsense API access.

Supports three sources (in priority order when using auto-detect):
  1. HashiCorp Vault (via hvac) -- production
  2. Environment variables / .env file -- development
  3. Explicit values passed to OpnsenseClient -- fallback / testing

Usage::

    from opnsense.credentials import get_credentials
    creds = get_credentials()
    async with OpnsenseClient(
        host=creds.host, key=creds.key, secret=creds.secret,
        port=creds.port, verify_ssl=creds.verify_ssl,
    ) as client:
        ...
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class OpnsenseCredentials:
    """Resolved credentials for an OPNsense connection.

    Attributes:
        host:       OPNsense hostname or IP address.
        key:        API key (from System > Access > Users > API keys).
        secret:     API secret corresponding to the key.
        port:       HTTPS port (default 443).
        verify_ssl: Verify TLS certificate (default False for self-signed).
    """

    host: str
    key: str
    secret: str
    port: int = 443
    verify_ssl: bool = False


class EnvCredentialProvider:
    """Load OPNsense credentials from environment variables or .env file.

    Reads: OPN_HOST, OPN_KEY, OPN_SECRET, OPN_PORT, OPN_VERIFY_SSL.
    Optionally loads a .env file if python-dotenv is installed.
    """

    def __init__(self, env_file: str | None = ".env") -> None:
        """Initialise the provider.

        Args:
            env_file: Path to .env file. Pass None to skip dotenv loading.
        """
        self._env_file = env_file

    def _load_dotenv(self) -> None:
        """Attempt to load the .env file if present and python-dotenv is installed."""
        if self._env_file and os.path.exists(self._env_file):
            try:
                from dotenv import load_dotenv

                load_dotenv(self._env_file, override=False)
            except ImportError:
                pass

    def get(self) -> OpnsenseCredentials:
        """Resolve and return credentials from environment variables.

        Returns:
            OpnsenseCredentials populated from OPN_* environment variables.

        Raises:
            RuntimeError: If OPN_HOST, OPN_KEY, or OPN_SECRET are not set.
        """
        self._load_dotenv()

        host = os.environ.get("OPN_HOST")
        key = os.environ.get("OPN_KEY")
        secret = os.environ.get("OPN_SECRET")

        missing = []
        if not host:
            missing.append("OPN_HOST")
        if not key:
            missing.append("OPN_KEY")
        if not secret:
            missing.append("OPN_SECRET")

        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Copy .env.example to .env and fill in values."
            )

        verify_raw = os.environ.get("OPN_VERIFY_SSL", "false").lower()
        verify_ssl = verify_raw in ("true", "1", "yes")

        return OpnsenseCredentials(
            host=host,
            key=key,
            secret=secret,
            port=int(os.environ.get("OPN_PORT", "443")),
            verify_ssl=verify_ssl,
        )


class VaultCredentialProvider:
    """Load OPNsense credentials from HashiCorp Vault KV v2.

    Vault path follows ADR-0011: ``secret/{scope}/{service}/{env}``
    Example: ``secret/net/opnsense/poc``

    Requires: ``hvac`` package (optional dependency, install with ``pip install opnsense[vault]``).
    """

    def __init__(
        self,
        vault_addr: str | None = None,
        vault_token: str | None = None,
        vault_path: str = "secret/net/opnsense/poc",
        mount_point: str = "secret",
    ) -> None:
        """Initialise the Vault provider.

        Args:
            vault_addr:   Vault server URL. Defaults to VAULT_ADDR env var.
            vault_token:  Vault token. Defaults to VAULT_TOKEN env var.
            vault_path:   KV v2 path to the OPNsense credential entry.
            mount_point:  KV v2 mount point (default ``secret``).
        """
        self._vault_addr = vault_addr or os.environ.get("VAULT_ADDR", "")
        self._vault_token = vault_token or os.environ.get("VAULT_TOKEN", "")
        self._vault_path = vault_path
        self._mount_point = mount_point

    def get(self) -> OpnsenseCredentials:
        """Resolve and return credentials from Vault.

        Expected Vault KV fields (ADR-0011 schema):
            - ``host``: OPNsense hostname or IP
            - ``key``: API key
            - ``secret``: API secret
            - ``port`` (optional): HTTPS port, default 443
            - ``verify_ssl`` (optional): ``true``/``false``, default ``false``

        Returns:
            OpnsenseCredentials populated from Vault KV entry.

        Raises:
            ImportError: If hvac is not installed.
            RuntimeError: If Vault is not configured or credential is missing.
        """
        try:
            import hvac
        except ImportError as exc:
            raise ImportError(
                "hvac is required for Vault credential provider. "
                "Install with: pip install opnsense[vault]"
            ) from exc

        if not self._vault_addr:
            raise RuntimeError(
                "VAULT_ADDR not set. Provide vault_addr parameter or set VAULT_ADDR env var."
            )
        if not self._vault_token:
            raise RuntimeError(
                "VAULT_TOKEN not set. Provide vault_token parameter or set VAULT_TOKEN env var."
            )

        client = hvac.Client(url=self._vault_addr, token=self._vault_token)

        # Strip mount_point prefix from path if present
        path = self._vault_path
        if path.startswith(f"{self._mount_point}/"):
            path = path[len(self._mount_point) + 1 :]

        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self._mount_point,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to read Vault path '{self._vault_path}': {exc}"
            ) from exc

        data = response.get("data", {}).get("data", {})
        if not data:
            raise RuntimeError(
                f"Vault path '{self._vault_path}' returned empty data."
            )

        host = data.get("host")
        key = data.get("key")
        secret = data.get("secret")

        missing = []
        if not host:
            missing.append("host")
        if not key:
            missing.append("key")
        if not secret:
            missing.append("secret")

        if missing:
            raise RuntimeError(
                f"Vault path '{self._vault_path}' missing fields: {', '.join(missing)}"
            )

        verify_raw = str(data.get("verify_ssl", "false")).lower()
        verify_ssl = verify_raw in ("true", "1", "yes")

        return OpnsenseCredentials(
            host=host,
            key=key,
            secret=secret,
            port=int(data.get("port", "443")),
            verify_ssl=verify_ssl,
        )


def get_credentials(
    env_file: str | None = ".env",
    vault_path: str | None = None,
) -> OpnsenseCredentials:
    """Auto-detect credential source and return OPNsense credentials.

    Priority:
      1. Vault (if vault_path is provided or VAULT_ADDR is set)
      2. Environment variables / .env file

    Args:
        env_file:    Path to .env file for dotenv loading.
        vault_path:  Vault KV v2 path. If provided, Vault is tried first.

    Returns:
        OpnsenseCredentials from the first available source.
    """
    # Try Vault first if configured
    if vault_path or os.environ.get("VAULT_ADDR"):
        try:
            return VaultCredentialProvider(
                vault_path=vault_path or "secret/net/opnsense/poc",
            ).get()
        except (ImportError, RuntimeError):
            pass  # Fall through to env

    return EnvCredentialProvider(env_file=env_file).get()
