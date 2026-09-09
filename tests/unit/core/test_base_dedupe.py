# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests — ensure(dedupe=True) collapses several resources sharing one identity.

Two rows carrying the same match keys make an otherwise idempotent converge fail with
AmbiguousMatchError: the manager refuses to guess which one the catalog meant, and the play
stops. Seen live on a firewall with two catch-all Unbound forwards per resolver.

The catalog declares ONE resource per identity, so a second one is drift like any other
value. With dedupe the lowest UUID survives and converges and the rest are deleted;
without it the raise is unchanged, because deleting is never a silent default.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import AmbiguousMatchError
from opnsense.managers.base import BaseManager


class _Forward(BaseManager):
    _endpoint = "unbound/settings"
    _payload_key = "forward"
    _entity_suffix = "Forward"
    _apply_endpoint = "unbound/service/reconfigure"
    _match_keys = ["domain", "server"]


DESIRED = {"domain": "", "server": "127.0.0.1", "port": "53531", "type": "forward"}
# deliberately out of order: the survivor is chosen by UUID, not by search order
ROWS = [
    {"uuid": "u-b", "domain": "", "server": "127.0.0.1", "port": "53531", "type": "forward"},
    {"uuid": "u-a", "domain": "", "server": "127.0.0.1", "port": "53531", "type": "forward"},
]


@pytest.mark.asyncio
class TestDedupe:
    async def test_without_dedupe_the_ambiguity_still_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = ROWS
        with pytest.raises(AmbiguousMatchError) as exc:
            await _Forward(mock_client).ensure("present", DESIRED)
        assert sorted(exc.value.uuids) == ["u-a", "u-b"]
        mock_client.delete.assert_not_called()

    async def test_lowest_uuid_survives_and_the_rest_are_deleted(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = ROWS
        mock_client.get.return_value = {"forward": ROWS[0]}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        r = await _Forward(mock_client).ensure("present", DESIRED, dedupe=True)
        assert r.changed is True
        assert r.action == "deduped"  # the survivor itself needed no change
        assert r.uuid == "u-a"
        assert r.deduped == ("u-b",)
        assert [(c.args[0], c.args[1]) for c in mock_client.delete.await_args_list] == [
            ("unbound/settings/delForward", "u-b")
        ]

    async def test_check_mode_reports_the_duplicates_without_deleting(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = ROWS
        r = await _Forward(mock_client).ensure("present", DESIRED, dedupe=True, check_mode=True)
        assert r.changed is True
        assert r.deduped == ("u-b",)
        mock_client.delete.assert_not_called()

    async def test_the_survivor_still_converges_its_own_drift(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = ROWS
        mock_client.get.return_value = {"forward": ROWS[0]}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        r = await _Forward(mock_client).ensure("present", {**DESIRED, "port": "5353"}, dedupe=True)
        assert r.action == "updated"  # a real change wins over the dedupe label
        assert r.changed is True
        assert r.deduped == ("u-b",)
        assert mock_client.update.await_args.args[0] == "unbound/settings/setForward"
        assert mock_client.update.await_args.args[1] == "u-a"

    async def test_a_single_match_is_untouched_and_still_idempotent(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = [ROWS[1]]
        r = await _Forward(mock_client).ensure("present", DESIRED, dedupe=True)
        assert (r.changed, r.action, r.uuid, r.deduped) == (False, "noop", "u-a", ())
        mock_client.delete.assert_not_called()

    async def test_no_match_creates_as_usual(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = {"uuid": "u-new"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        r = await _Forward(mock_client).ensure("present", DESIRED, dedupe=True)
        assert (r.changed, r.action, r.deduped) == (True, "created", ())

    async def test_absent_removes_every_copy(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = ROWS
        mock_client.get.return_value = {"forward": ROWS[0]}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        r = await _Forward(mock_client).ensure("absent", DESIRED, dedupe=True)
        assert r.changed is True
        assert r.deduped == ("u-b",)
        deleted = [c.args[1] for c in mock_client.delete.await_args_list]
        assert sorted(deleted) == ["u-a", "u-b"]


@pytest.mark.asyncio
class TestFindMatching:
    async def test_matches_come_back_ordered_by_uuid(self, mock_client: AsyncMock) -> None:
        mgr = _Forward(mock_client)
        mock_client.search.return_value = ROWS
        found = await mgr._identity.find_matching(DESIRED, mgr.list)
        assert [row["uuid"] for row in found] == ["u-a", "u-b"]

    async def test_non_matching_rows_are_filtered_out(self, mock_client: AsyncMock) -> None:
        mgr = _Forward(mock_client)
        mock_client.search.return_value = [
            *ROWS,
            {"uuid": "u-z", "domain": "example.invalid", "server": "127.0.0.1"},
        ]
        found = await mgr._identity.find_matching(DESIRED, mgr.list)
        assert [row["uuid"] for row in found] == ["u-a", "u-b"]

    async def test_no_rows_is_an_empty_list_not_an_error(self, mock_client: AsyncMock) -> None:
        mgr = _Forward(mock_client)
        mock_client.search.return_value = []
        assert await mgr._identity.find_matching(DESIRED, mgr.list) == []
