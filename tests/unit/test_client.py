"""Unit tests for opnsense.client.OpnsenseClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import (
    OpnsenseAuthError,
    OpnsenseEndpointMissingError,
    OpnsenseError,
    OpnsensePermissionError,
    OpnsenseServerError,
    OpnsenseValidationError,
)


class TestClientConstructor:
    """Tests for OpnsenseClient initialisation."""

    def test_stores_host(self) -> None:
        client = OpnsenseClient(host="fw.test", key="k", secret="s")
        assert client._host == "fw.test"

    def test_stores_key_and_secret(self) -> None:
        client = OpnsenseClient(host="fw", key="mykey", secret="mysecret")
        assert client._key == "mykey"
        assert client._secret == "mysecret"

    def test_default_port(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        assert client._port == 443

    def test_custom_port(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s", port=8443)
        assert client._port == 8443

    def test_default_verify_ssl(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        assert client._verify_ssl is False

    def test_custom_verify_ssl(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s", verify_ssl=True)
        assert client._verify_ssl is True

    def test_default_timeout(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        assert client._timeout == 30

    def test_default_max_retries(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        assert client._max_retries == 3

    def test_default_retry_backoff(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        assert client._retry_backoff == 2.0

    def test_http_client_none_initially(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        assert client._http is None


class TestBaseUrl:
    """Tests for the base_url property."""

    def test_default_port(self) -> None:
        client = OpnsenseClient(host="opnsense.example.com", key="k", secret="s")
        assert client.base_url == "https://opnsense.example.com:443/api"

    def test_custom_port(self) -> None:
        client = OpnsenseClient(host="fw.local", key="k", secret="s", port=8443)
        assert client.base_url == "https://fw.local:8443/api"


class TestRaiseForStatus:
    """Tests for _raise_for_status (maps HTTP codes to exceptions)."""

    def _make_response(self, status_code: int, json_body: dict | None = None) -> MagicMock:
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.text = ""
        if json_body is not None:
            resp.json.return_value = json_body
        else:
            resp.json.side_effect = Exception("no json")
        return resp

    def test_401_raises_auth_error(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        resp = self._make_response(401, {"message": "unauthorized"})
        with pytest.raises(OpnsenseAuthError):
            client._raise_for_status(resp, "auth/user/search")

    def test_403_raises_permission_error(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        resp = self._make_response(403, {"message": "forbidden"})
        with pytest.raises(OpnsensePermissionError):
            client._raise_for_status(resp, "auth/user/addUser")

    def test_404_raises_endpoint_missing(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        resp = self._make_response(404, {"message": "not found"})
        with pytest.raises(OpnsenseEndpointMissingError):
            client._raise_for_status(resp, "nonexistent/ep")

    def test_400_raises_validation_error(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        resp = self._make_response(400, {"validations": {"name": "required"}})
        with pytest.raises(OpnsenseValidationError) as exc_info:
            client._raise_for_status(resp, "auth/user/addUser")
        assert exc_info.value.validations == {"name": "required"}

    def test_500_raises_server_error(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        resp = self._make_response(500, {"message": "internal"})
        with pytest.raises(OpnsenseServerError):
            client._raise_for_status(resp, "some/ep")

    def test_unknown_status_raises_base_error(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")
        resp = self._make_response(418, {})
        with pytest.raises(OpnsenseError):
            client._raise_for_status(resp, "some/ep")


class TestRedactSecret:
    """Tests for _redact_secret."""

    def test_redacts_secret(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="supersecret123")
        result = client._redact_secret("Error: supersecret123 leaked")
        assert "supersecret123" not in result
        assert "<REDACTED:api_secret>" in result

    def test_redacts_key(self) -> None:
        client = OpnsenseClient(host="fw", key="myapikey", secret="s")
        result = client._redact_secret("Auth failed for myapikey")
        assert "myapikey" not in result
        assert "<REDACTED:api_key>" in result


@pytest.mark.asyncio
class TestRetryLogic:
    """Tests for retry behaviour on transient failures."""

    async def test_succeeds_after_transient_500(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s", max_retries=3, retry_backoff=0.01)

        call_count = 0

        async def mock_post(url: str, json: dict | None = None, **kwargs) -> MagicMock:  # type: ignore[override]
            nonlocal call_count
            call_count += 1
            resp = MagicMock(spec=httpx.Response)
            if call_count < 3:
                resp.status_code = 500
                resp.text = "error"
                resp.json.side_effect = Exception("no json")
            else:
                resp.status_code = 200
                resp.json.return_value = {"rows": [{"name": "test"}]}
            return resp

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = mock_post
        mock_http.is_closed = False
        client._http = mock_http

        result = await client.post("auth/user/searchUser", data={})
        assert result == {"rows": [{"name": "test"}]}
        assert call_count == 3

    async def test_raises_after_max_retries_exhausted(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s", max_retries=2, retry_backoff=0.01)

        async def mock_post(url: str, json: dict | None = None, **kwargs) -> MagicMock:  # type: ignore[override]
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 500
            resp.text = "server error"
            resp.json.return_value = {"message": "internal"}
            return resp

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = mock_post
        mock_http.is_closed = False
        client._http = mock_http

        with pytest.raises(OpnsenseServerError):
            await client.post("auth/user/searchUser", data={})


@pytest.mark.asyncio
class TestSearch:
    """Tests for the search() convenience method."""

    async def test_returns_rows(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")

        async def mock_post(url: str, json: dict | None = None, **kwargs) -> MagicMock:  # type: ignore[override]
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = {
                "rows": [{"uuid": "a1", "name": "alice"}, {"uuid": "b2", "name": "bob"}],
                "rowCount": 2,
                "total": 2,
                "current": 1,
            }
            return resp

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = mock_post
        mock_http.is_closed = False
        client._http = mock_http

        rows = await client.search("auth/user/searchUser")
        assert len(rows) == 2
        assert rows[0]["name"] == "alice"

    async def test_returns_empty_when_no_rows(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")

        async def mock_post(url: str, json: dict | None = None, **kwargs) -> MagicMock:  # type: ignore[override]
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = {"rowCount": 0, "total": 0, "current": 1}
            return resp

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = mock_post
        mock_http.is_closed = False
        client._http = mock_http

        rows = await client.search("auth/user/searchUser")
        assert rows == []


@pytest.mark.asyncio
class TestCreate:
    """Tests for the create() method."""

    async def test_returns_uuid(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")

        async def mock_post(url: str, json: dict | None = None, **kwargs) -> MagicMock:  # type: ignore[override]
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = {"uuid": "abc-123"}
            return resp

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = mock_post
        mock_http.is_closed = False
        client._http = mock_http

        uuid = await client.create("auth/user/addUser", "user", {"name": "test"})
        assert uuid == "abc-123"

    async def test_raises_when_no_uuid(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")

        async def mock_post(url: str, json: dict | None = None, **kwargs) -> MagicMock:  # type: ignore[override]
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = {"result": "saved"}
            return resp

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = mock_post
        mock_http.is_closed = False
        client._http = mock_http

        with pytest.raises(OpnsenseError, match="no UUID"):
            await client.create("auth/user/addUser", "user", {"name": "test"})


@pytest.mark.asyncio
class TestValidationOnSuccess:
    """Tests for validation error detection on HTTP 200 responses."""

    async def test_result_failed_raises_validation_error(self) -> None:
        client = OpnsenseClient(host="fw", key="k", secret="s")

        async def mock_post(url: str, json: dict | None = None, **kwargs) -> MagicMock:  # type: ignore[override]
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = {
                "result": "failed",
                "validations": {"user.name": "This field is required"},
            }
            return resp

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = mock_post
        mock_http.is_closed = False
        client._http = mock_http

        with pytest.raises(OpnsenseValidationError) as exc_info:
            await client.post("auth/user/addUser", data={"user": {}})
        assert "user.name" in exc_info.value.validations
