"""Unit tests for opnsense.credentials."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from opnsense.credentials import (
    EnvCredentialProvider,
    OpnsenseCredentials,
    VaultCredentialProvider,
    get_credentials,
)


class TestEnvCredentialProvider:
    """Tests for EnvCredentialProvider."""

    def test_reads_required_env_vars(self) -> None:
        """Provider reads OPN_HOST, OPN_KEY, OPN_SECRET from environment."""
        env = {
            "OPN_HOST": "opnsense.example.com",
            "OPN_KEY": "test-key",
            "OPN_SECRET": "test-secret",
        }
        with patch.dict(os.environ, env, clear=False):
            provider = EnvCredentialProvider(env_file=None)
            creds = provider.get()

        assert creds.host == "opnsense.example.com"
        assert creds.key == "test-key"
        assert creds.secret == "test-secret"

    def test_missing_env_vars_raises_runtime_error(self) -> None:
        """Missing required env vars raises RuntimeError listing them."""
        with patch.dict(os.environ, {}, clear=True):
            provider = EnvCredentialProvider(env_file=None)
            with pytest.raises(RuntimeError, match="OPN_HOST"):
                provider.get()

    def test_missing_single_var(self) -> None:
        """Missing just OPN_SECRET raises with that var name."""
        env = {"OPN_HOST": "fw", "OPN_KEY": "k"}
        with patch.dict(os.environ, env, clear=True):
            provider = EnvCredentialProvider(env_file=None)
            with pytest.raises(RuntimeError, match="OPN_SECRET"):
                provider.get()


class TestDefaults:
    """Tests for default values."""

    def test_default_port_443(self) -> None:
        env = {
            "OPN_HOST": "fw",
            "OPN_KEY": "k",
            "OPN_SECRET": "s",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = EnvCredentialProvider(env_file=None).get()
        assert creds.port == 443

    def test_default_verify_ssl_false(self) -> None:
        env = {
            "OPN_HOST": "fw",
            "OPN_KEY": "k",
            "OPN_SECRET": "s",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = EnvCredentialProvider(env_file=None).get()
        assert creds.verify_ssl is False

    def test_custom_port(self) -> None:
        env = {
            "OPN_HOST": "fw",
            "OPN_KEY": "k",
            "OPN_SECRET": "s",
            "OPN_PORT": "8443",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = EnvCredentialProvider(env_file=None).get()
        assert creds.port == 8443

    def test_verify_ssl_true(self) -> None:
        env = {
            "OPN_HOST": "fw",
            "OPN_KEY": "k",
            "OPN_SECRET": "s",
            "OPN_VERIFY_SSL": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = EnvCredentialProvider(env_file=None).get()
        assert creds.verify_ssl is True


class TestVaultCredentialProvider:
    def test_reads_from_vault_successfully(self) -> None:
        mock_hvac = MagicMock()
        mock_client = MagicMock()
        mock_hvac.Client.return_value = mock_client
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "host": "opnsense.example.com",
                    "key": "vault-key",
                    "secret": "vault-secret",
                    "port": "8443",
                    "verify_ssl": "true",
                }
            }
        }

        with patch.dict("sys.modules", {"hvac": mock_hvac}):
            provider = VaultCredentialProvider(
                vault_addr="https://vault.example.com:8200",
                vault_token="test-token",
                vault_path="secret/net/opnsense/poc",
            )
            creds = provider.get()

        assert creds.host == "opnsense.example.com"
        assert creds.key == "vault-key"
        assert creds.secret == "vault-secret"
        assert creds.port == 8443
        assert creds.verify_ssl is True

    def test_raises_import_error_when_hvac_missing(self) -> None:
        import sys

        saved = sys.modules.get("hvac")
        sys.modules["hvac"] = None  # type: ignore[assignment]
        try:
            provider = VaultCredentialProvider(
                vault_addr="https://vault.example.com:8200",
                vault_token="test-token",
            )
            with pytest.raises(ImportError, match="hvac is required"):
                provider.get()
        finally:
            if saved is not None:
                sys.modules["hvac"] = saved
            else:
                sys.modules.pop("hvac", None)

    def test_raises_runtime_error_when_vault_addr_not_set(self) -> None:
        mock_hvac = MagicMock()
        with patch.dict("sys.modules", {"hvac": mock_hvac}):
            provider = VaultCredentialProvider(
                vault_addr="",
                vault_token="test-token",
            )
            with pytest.raises(RuntimeError, match="VAULT_ADDR not set"):
                provider.get()

    def test_raises_runtime_error_when_vault_returns_empty(self) -> None:
        mock_hvac = MagicMock()
        mock_client = MagicMock()
        mock_hvac.Client.return_value = mock_client
        mock_client.secrets.kv.v2.read_secret_version.return_value = {"data": {"data": {}}}

        with patch.dict("sys.modules", {"hvac": mock_hvac}):
            provider = VaultCredentialProvider(
                vault_addr="https://vault.example.com:8200",
                vault_token="test-token",
            )
            with pytest.raises(RuntimeError, match="returned empty data"):
                provider.get()

    def test_raises_runtime_error_when_vault_token_not_set(self) -> None:
        mock_hvac = MagicMock()
        with patch.dict("sys.modules", {"hvac": mock_hvac}):
            provider = VaultCredentialProvider(
                vault_addr="https://vault.example.com:8200",
                vault_token="",
            )
            with pytest.raises(RuntimeError, match="VAULT_TOKEN not set"):
                provider.get()


class TestGetCredentials:
    """Tests for the get_credentials() convenience function."""

    def test_returns_credentials(self) -> None:
        env = {
            "OPN_HOST": "fw",
            "OPN_KEY": "k",
            "OPN_SECRET": "s",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = get_credentials(env_file=None)
        assert isinstance(creds, OpnsenseCredentials)
        assert creds.host == "fw"

    def test_auto_detect_vault_first_when_vault_addr_set(self) -> None:
        mock_hvac = MagicMock()
        mock_client_inst = MagicMock()
        mock_hvac.Client.return_value = mock_client_inst
        mock_client_inst.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "host": "vault-fw.example.com",
                    "key": "vk",
                    "secret": "vs",
                }
            }
        }

        env = {
            "VAULT_ADDR": "https://vault.example.com:8200",
            "VAULT_TOKEN": "tok",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch.dict("sys.modules", {"hvac": mock_hvac}),
        ):
            creds = get_credentials(env_file=None)

        assert creds.host == "vault-fw.example.com"

    def test_fallback_to_env_when_vault_fails(self) -> None:
        env = {
            "VAULT_ADDR": "https://vault.example.com:8200",
            "OPN_HOST": "env-fw.example.com",
            "OPN_KEY": "ek",
            "OPN_SECRET": "es",
        }
        # hvac not importable -> ImportError -> falls through to env
        import sys

        saved = sys.modules.get("hvac")
        sys.modules["hvac"] = None  # type: ignore[assignment]
        try:
            with patch.dict(os.environ, env, clear=True):
                creds = get_credentials(env_file=None)
            assert creds.host == "env-fw.example.com"
        finally:
            if saved is not None:
                sys.modules["hvac"] = saved
            else:
                sys.modules.pop("hvac", None)
