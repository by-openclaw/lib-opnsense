"""Integration test fixtures -- requires live OPNsense device."""

import pytest

from opnsense.client import OpnsenseClient
from opnsense.credentials import get_credentials


@pytest.fixture
async def opn_client():
    """Create a live OpnsenseClient from env credentials."""
    creds = get_credentials()
    async with OpnsenseClient(
        host=creds.host,
        key=creds.key,
        secret=creds.secret,
        port=creds.port,
        verify_ssl=creds.verify_ssl,
    ) as client:
        yield client
