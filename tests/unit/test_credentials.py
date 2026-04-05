"""Unit tests for opnsense.credentials."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from opnsense.credentials import EnvCredentialProvider, OpnsenseCredentials, get_credentials


class TestEnvCredentialProvider:
    """Tests for EnvCredentialProvider."""

    def test_reads_required_env_vars(self) -> None:
        """Provider reads OPN_HOST, OPN_KEY, OPN_SECRET from environment."""
        env = {
            "OPN_HOST": "10.6.224.106",
            "OPN_KEY": "test-key",
            "OPN_SECRET": "test-secret",
        }
        with patch.dict(os.environ, env, clear=False):
            provider = EnvCredentialProvider(env_file=None)
            creds = provider.get()

        assert creds.host == "10.6.224.106"
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
