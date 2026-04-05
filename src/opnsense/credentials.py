"""Credential providers for lib-opnsense.

Supports two sources:
  1. Environment variables / .env file — development
  2. Explicit values passed to OpnsenseClient — fallback / testing

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

    Reads: OPN_HOST, OPN_KEY, OPN_SECRET, OPN_PORT, OPN_VERIFY_SSL
    Optionally loads a .env file if python-dotenv is installed.
    """

    def __init__(self, env_file: str | None = ".env") -> None:
        """Initialise the provider.

        Args:
            env_file: Path to .env file. Pass None to skip dotenv loading.
        """
        self._env_file = env_file

    def _load_dotenv(self) -> None:
        """Attempt to load the .env file if present and python-dotenv is installed.

        Silently skips if the file does not exist or dotenv is not installed.
        Uses override=False so existing environment variables take precedence.
        """
        if self._env_file and os.path.exists(self._env_file):
            try:
                from dotenv import load_dotenv

                load_dotenv(self._env_file, override=False)
            except ImportError:
                pass  # python-dotenv not installed; fall through to raw env

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


def get_credentials(env_file: str | None = ".env") -> OpnsenseCredentials:
    """Auto-detect credential source and return OPNsense credentials.

    Currently supports environment variables only. Vault integration
    will be added when Vault is deployed (Phase 2).

    Args:
        env_file: Path to .env file for dotenv loading.

    Returns:
        OpnsenseCredentials from the first available source.
    """
    return EnvCredentialProvider(env_file=env_file).get()
