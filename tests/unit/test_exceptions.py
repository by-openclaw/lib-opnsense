"""Unit tests for opnsense.exceptions."""

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


class TestOpnsenseError:
    """Tests for the base OpnsenseError exception."""

    def test_message_only(self) -> None:
        exc = OpnsenseError("something broke")
        assert exc.message == "something broke"
        assert exc.status_code is None
        assert exc.endpoint is None

    def test_with_status_and_endpoint(self) -> None:
        exc = OpnsenseError("fail", status_code=418, endpoint="auth/user/get")
        assert exc.status_code == 418
        assert exc.endpoint == "auth/user/get"

    def test_str_with_context(self) -> None:
        exc = OpnsenseError("fail", status_code=500, endpoint="auth/user/get")
        result = str(exc)
        assert "fail" in result
        assert "500" in result
        assert "auth/user/get" in result

    def test_str_without_context(self) -> None:
        exc = OpnsenseError("plain error")
        assert str(exc) == "plain error"


class TestOpnsenseAuthError:
    """Tests for OpnsenseAuthError."""

    def test_default_message(self) -> None:
        exc = OpnsenseAuthError()
        assert exc.status_code == 401
        assert "Authentication failed" in exc.message

    def test_custom_message_with_endpoint(self) -> None:
        exc = OpnsenseAuthError(message="bad key", endpoint="auth/user/search")
        assert exc.status_code == 401
        assert exc.endpoint == "auth/user/search"
        assert "bad key" in str(exc)


class TestOpnsensePermissionError:
    """Tests for OpnsensePermissionError."""

    def test_default_message(self) -> None:
        exc = OpnsensePermissionError()
        assert exc.status_code == 403
        assert "Permission denied" in exc.message

    def test_str_includes_endpoint(self) -> None:
        exc = OpnsensePermissionError(endpoint="firewall/rule/add")
        assert "firewall/rule/add" in str(exc)


class TestOpnsenseEndpointMissingError:
    """Tests for OpnsenseEndpointMissingError."""

    def test_default_message(self) -> None:
        exc = OpnsenseEndpointMissingError()
        assert exc.status_code == 404
        assert "not found" in exc.message.lower()

    def test_custom_message(self) -> None:
        exc = OpnsenseEndpointMissingError(message="plugin missing")
        assert exc.message == "plugin missing"


class TestOpnsenseValidationError:
    """Tests for OpnsenseValidationError."""

    def test_default_empty_validations(self) -> None:
        exc = OpnsenseValidationError()
        assert exc.status_code == 400
        assert exc.validations == {}

    def test_with_validations_dict(self) -> None:
        validations = {"name": "Name is required", "email": "Invalid format"}
        exc = OpnsenseValidationError(
            message="Validation failed",
            endpoint="auth/user/addUser",
            validations=validations,
        )
        assert exc.validations == validations
        result = str(exc)
        assert "name: Name is required" in result
        assert "email: Invalid format" in result

    def test_str_without_validations(self) -> None:
        exc = OpnsenseValidationError(message="fail", endpoint="ep")
        result = str(exc)
        # Should not include the separator when no validations
        assert "fail" in result


class TestOpnsenseTimeoutError:
    """Tests for OpnsenseTimeoutError."""

    def test_no_status_code(self) -> None:
        exc = OpnsenseTimeoutError()
        assert exc.status_code is None

    def test_message(self) -> None:
        exc = OpnsenseTimeoutError(message="timed out after 30s", endpoint="ep")
        assert "timed out" in str(exc)


class TestOpnsenseConnectionError:
    """Tests for OpnsenseConnectionError."""

    def test_no_status_code(self) -> None:
        exc = OpnsenseConnectionError()
        assert exc.status_code is None

    def test_message_and_endpoint(self) -> None:
        exc = OpnsenseConnectionError(message="Connection refused", endpoint="auth/user/search")
        assert exc.endpoint == "auth/user/search"
        assert "Connection refused" in str(exc)


class TestOpnsenseServerError:
    """Tests for OpnsenseServerError."""

    def test_status_code_500(self) -> None:
        exc = OpnsenseServerError()
        assert exc.status_code == 500

    def test_custom_message(self) -> None:
        exc = OpnsenseServerError(message="backend crashed")
        assert exc.message == "backend crashed"
