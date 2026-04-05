# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.auth_priv.AuthPrivManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.managers.auth_priv import AuthPrivManager


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
        mock_client.get.return_value = {"users": "alice", "groups": ""}
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
        assert "bob" in call_args.kwargs.get("data", call_args[1].get("data", {}))["users"]

    async def test_noop_when_already_assigned(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"users": "alice,bob", "groups": ""}
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
        mock_client.get.return_value = {"users": "", "groups": ""}
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
        assert "admins" in data["groups"]


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_unassigns_privilege_from_user(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"users": "alice,bob", "groups": ""}
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
        assert "bob" not in data["users"]
        assert "alice" in data["users"]

    async def test_noop_when_not_assigned(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"users": "alice", "groups": ""}
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
        mock_client.get.return_value = {"users": "", "groups": ""}
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
        mock_client.get.return_value = {"users": "alice", "groups": ""}
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
            "users": {
                "uuid1": {"selected": "1", "value": "alice"},
                "uuid2": {"selected": "0", "value": "bob"},
                "uuid3": {"selected": 1, "value": "carol"},
            }
        }
        result = mgr._extract_targets(assignment, "user")
        assert result == {"alice", "carol"}

    def test_list_format(self) -> None:
        mgr = AuthPrivManager(AsyncMock())
        assignment = {"users": ["alice", "bob"]}
        result = mgr._extract_targets(assignment, "user")
        assert result == {"alice", "bob"}

    def test_empty_string(self) -> None:
        mgr = AuthPrivManager(AsyncMock())
        assignment = {"users": ""}
        result = mgr._extract_targets(assignment, "user")
        assert result == set()

    def test_csv_string(self) -> None:
        mgr = AuthPrivManager(AsyncMock())
        assignment = {"users": "alice,bob"}
        result = mgr._extract_targets(assignment, "user")
        assert result == {"alice", "bob"}

    def test_missing_key(self) -> None:
        mgr = AuthPrivManager(AsyncMock())
        assignment = {}
        result = mgr._extract_targets(assignment, "user")
        assert result == set()


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
