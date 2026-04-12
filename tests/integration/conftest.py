"""Integration test fixtures -- requires live OPNsense device."""

from datetime import datetime, timezone

import pytest

from opnsense.client import OpnsenseClient
from opnsense.credentials import get_credentials
from opnsense.logging import configure_logging


def pytest_configure(config):
    """Configure structured logging for integration tests.

    Each test run creates a timestamped log file so previous runs are preserved.
    Tail the latest: ``ls -t tests/integration/logs/inttest-*.log | head -1 | xargs tail -f``
    """
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    log_file = f"tests/integration/logs/inttest-{ts}.log"
    configure_logging(
        level="DEBUG",
        log_file=log_file,
        colorize=True,
    )


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
