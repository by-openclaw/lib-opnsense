"""Smoke tests -- verify imports and basic instantiation work."""

from __future__ import annotations


def test_import_opnsense() -> None:
    """Importing opnsense should succeed."""
    import opnsense

    assert hasattr(opnsense, "__version__")
    assert opnsense.__version__  # just verify it's set


def test_client_can_be_instantiated() -> None:
    """OpnsenseClient can be created without connecting."""
    from opnsense.client import OpnsenseClient

    client = OpnsenseClient(host="localhost", key="k", secret="s")
    assert client._host == "localhost"


def test_manager_classes_importable() -> None:
    """All manager classes can be imported."""
    from opnsense.managers.auth.group import AuthGroupManager
    from opnsense.managers.auth.priv import AuthPrivManager
    from opnsense.managers.auth.user import AuthUserManager

    assert AuthUserManager is not None
    assert AuthGroupManager is not None
    assert AuthPrivManager is not None


def test_ensure_result_creation() -> None:
    """EnsureResult dataclass can be instantiated."""
    from opnsense.models.base import EnsureResult

    result = EnsureResult(changed=False, action="noop")
    assert result.changed is False
    assert result.action == "noop"
    assert result.uuid is None
    assert result.before is None
    assert result.after is None


def test_exception_hierarchy() -> None:
    """All exception classes are importable and have correct inheritance."""
    from opnsense.exceptions import (
        OpnsenseAuthError,
        OpnsenseConnectionError,
        OpnsenseEndpointMissingError,
        OpnsenseError,
        OpnsensePermissionError,
        OpnsenseServerError,
        OpnsenseTimeoutError,
        OpnsenseValidationError,
    )

    assert issubclass(OpnsenseAuthError, OpnsenseError)
    assert issubclass(OpnsensePermissionError, OpnsenseError)
    assert issubclass(OpnsenseEndpointMissingError, OpnsenseError)
    assert issubclass(OpnsenseValidationError, OpnsenseError)
    assert issubclass(OpnsenseServerError, OpnsenseError)
    assert issubclass(OpnsenseTimeoutError, OpnsenseError)
    assert issubclass(OpnsenseConnectionError, OpnsenseError)
