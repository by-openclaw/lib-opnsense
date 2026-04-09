# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.auth_priv.AuthPrivManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseError
from opnsense.managers.auth.priv import AuthPrivManager


@pytest.mark.asyncio
class TestListPrivileges:
    async def test_returns_parsed_list(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "rows": [
                {"id": "page-all", "name": "All Pages"},
                {"id": "user-shell-access", "name": "Shell Access"},
            ]
        }
        mgr = AuthPrivManager(mock_client)
        result = await mgr.list_privileges()
        assert len(result) == 2
        assert result[0]["id"] == "page-all"
        mock_client.get.assert_awaited_once_with("auth/priv/get")

    async def test_returns_empty_for_non_dict(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = "unexpected"
        mgr = AuthPrivManager(mock_client)
        result = await mgr.list_privileges()
        assert result == []

    async def test_handles_dict_of_dicts_format(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "privileges": {
                "page-all": {"name": "All Pages", "description": "Full access"},
                "user-shell": "Shell Access",
            }
        }
        mgr = AuthPrivManager(mock_client)
        result = await mgr.list_privileges()
        assert len(result) == 2
        ids = {r["id"] for r in result}
        assert ids == {"page-all", "user-shell"}


@pytest.mark.asyncio
class TestGetAssignment:
    async def test_returns_assignment_data(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "priv": "page-all",
            "users": "alice,bob",
            "groups": "admins",
        }
        mgr = AuthPrivManager(mock_client)
        result = await mgr.get_assignment("page-all")
        assert result["users"] == "alice,bob"
        mock_client.get.assert_awaited_once_with("auth/priv/get_item/page-all")


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_assigns_privilege_to_user(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "priv": {
                "users": {
                    "uuid-alice": {"selected": "1", "value": "alice"},
                },
                "groups": {},
            }
        }
        mock_client.post.return_value = {"result": "saved"}
        mgr = AuthPrivManager(mock_client)

        result = await mgr.ensure(
            priv_id="page-all",
            target_type="user",
            target_name="bob",
            state="present",
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.call_args
        data = call_args.kwargs.get("data", call_args[1].get("data", {}))
        # bob has no UUID in the assignment, so it's passed as-is
        assert "bob" in data["priv"]["users"]

    async def test_noop_when_already_assigned(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "priv": {
                "users": {
                    "uuid-alice": {"selected": "1", "value": "alice"},
                    "uuid-bob": {"selected": "1", "value": "bob"},
                },
                "groups": {},
            }
        }
        mgr = AuthPrivManager(mock_client)

        result = await mgr.ensure(
            priv_id="page-all",
            target_type="user",
            target_name="bob",
            state="present",
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_assigns_privilege_to_group(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"priv": {"users": {}, "groups": {}}}
        mock_client.post.return_value = {"result": "saved"}
        mgr = AuthPrivManager(mock_client)

        result = await mgr.ensure(
            priv_id="page-all",
            target_type="group",
            target_name="admins",
            state="present",
        )

        assert result.changed is True
        assert result.action == "created"
        call_args = mock_client.post.call_args
        data = call_args.kwargs.get("data", call_args[1].get("data", {}))
        assert "admins" in data["priv"]["groups"]


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_unassigns_privilege_from_user(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "priv": {
                "users": {
                    "uuid-alice": {"selected": "1", "value": "alice"},
                    "uuid-bob": {"selected": "1", "value": "bob"},
                },
                "groups": {},
            }
        }
        mock_client.post.return_value = {"result": "saved"}
        mgr = AuthPrivManager(mock_client)

        result = await mgr.ensure(
            priv_id="page-all",
            target_type="user",
            target_name="bob",
            state="absent",
        )

        assert result.changed is True
        assert result.action == "deleted"
        call_args = mock_client.post.call_args
        data = call_args.kwargs.get("data", call_args[1].get("data", {}))
        assert "uuid-bob" not in data["priv"]["users"]
        assert "uuid-alice" in data["priv"]["users"]

    async def test_noop_when_not_assigned(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "priv": {
                "users": {"uuid-alice": {"selected": "1", "value": "alice"}},
                "groups": {},
            }
        }
        mgr = AuthPrivManager(mock_client)

        result = await mgr.ensure(
            priv_id="page-all",
            target_type="user",
            target_name="bob",
            state="absent",
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    async def test_check_mode_present_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"priv": {"users": {}, "groups": {}}}
        mgr = AuthPrivManager(mock_client)

        result = await mgr.ensure(
            priv_id="page-all",
            target_type="user",
            target_name="alice",
            state="present",
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.after is not None
        assert result.after["state"] == "present"
        mock_client.post.assert_not_awaited()

    async def test_check_mode_absent_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "priv": {
                "users": {"uuid-alice": {"selected": "1", "value": "alice"}},
                "groups": {},
            }
        }
        mgr = AuthPrivManager(mock_client)

        result = await mgr.ensure(
            priv_id="page-all",
            target_type="user",
            target_name="alice",
            state="absent",
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.post.assert_not_awaited()


class TestExtractTargets:
    def test_dict_enum_format(self) -> None:
        mgr = AuthPrivManager(AsyncMock())
        assignment = {
            "priv": {
                "users": {
                    "uuid1": {"selected": "1", "value": "alice"},
                    "uuid2": {"selected": "0", "value": "bob"},
                    "uuid3": {"selected": 1, "value": "carol"},
                }
            }
        }
        name_to_uuid, assigned = mgr._extract_targets(assignment, "user")
        assert assigned == {"alice", "carol"}
        assert name_to_uuid["alice"] == "uuid1"
        assert name_to_uuid["carol"] == "uuid3"

    def test_list_format(self) -> None:
        mgr = AuthPrivManager(AsyncMock())
        assignment = {"priv": {"users": ["alice", "bob"]}}
        _, assigned = mgr._extract_targets(assignment, "user")
        assert assigned == {"alice", "bob"}

    def test_empty_string(self) -> None:
        mgr = AuthPrivManager(AsyncMock())
        assignment = {"priv": {"users": ""}}
        _, assigned = mgr._extract_targets(assignment, "user")
        assert assigned == set()

    def test_csv_string(self) -> None:
        mgr = AuthPrivManager(AsyncMock())
        assignment = {"priv": {"users": "alice,bob"}}
        _, assigned = mgr._extract_targets(assignment, "user")
        assert assigned == {"alice", "bob"}

    def test_missing_key(self) -> None:
        mgr = AuthPrivManager(AsyncMock())
        assignment = {"priv": {}}
        _, assigned = mgr._extract_targets(assignment, "user")
        assert assigned == set()


@pytest.mark.asyncio
class TestEnsureValidation:
    async def test_invalid_target_type_raises(self, mock_client: AsyncMock) -> None:
        mgr = AuthPrivManager(mock_client)
        with pytest.raises(ValueError, match="Invalid target_type"):
            await mgr.ensure(
                priv_id="page-all",
                target_type="invalid",
                target_name="alice",
            )

    async def test_invalid_state_raises(self, mock_client: AsyncMock) -> None:
        mgr = AuthPrivManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(
                priv_id="page-all",
                target_type="user",
                target_name="alice",
                state="invalid",
            )


@pytest.mark.asyncio
class TestPrivErrorHandling:
    """Tests for try/except — privilege errors are logged then re-raised."""

    async def test_assign_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When set_item fails, manager logs ERROR and re-raises."""
        mock_client.get.return_value = {
            "priv": {
                "users": {},
                "groups": {"uuid-g1": {"selected": "0", "value": "admins"}},
            }
        }
        mock_client.post.side_effect = OpnsenseError(message="server error", status_code=500)

        mgr = AuthPrivManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.auth_priv"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(
                priv_id="page-all",
                target_type="group",
                target_name="admins",
                state="present",
            )

        assert any("privilege" in r.message and "failed" in r.message for r in caplog.records)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        """Re-raised exception keeps its original type."""
        mock_client.get.return_value = {"priv": {"users": {}, "groups": {}}}
        mock_client.post.side_effect = OpnsenseError(message="timeout", status_code=None)

        mgr = AuthPrivManager(mock_client)
        with pytest.raises(OpnsenseError) as exc_info:
            await mgr.ensure(
                priv_id="page-all",
                target_type="group",
                target_name="admins",
            )

        assert exc_info.value.message == "timeout"
