"""Shared fixtures for unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from opnsense.client import OpnsenseClient


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mocked OpnsenseClient for unit tests."""
    client = AsyncMock(spec=OpnsenseClient)
    client._base_url = "https://opnsense.example.com"
    return client
