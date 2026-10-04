# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for NetflowSettingsManager (diagnostics/netflow getconfig / setconfig).

Covers ADR ``lib/python/0001 §10.2`` for the singleton pattern on a controller whose read and
write actions are not named get/set: endpoint binding, nested diff, multi-select set
comparison, update + reconfigure, check_mode, validation, state handling, error propagation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.services.netflow_settings import NetflowSettingsManager


def _opts(*selected: str, extra: tuple[str, ...] = ()) -> dict[str, dict[str, object]]:
    d: dict[str, dict[str, object]] = {k: {"value": k, "selected": 1} for k in selected}
    d.update({k: {"value": k, "selected": 0} for k in extra})
    return d


def _doc(
    interfaces: tuple[str, ...] = ("opt1", "lan"),
    egress: tuple[str, ...] = (),
    version: str = "v9",
    collect: str = "1",
) -> dict[str, object]:
    """The getconfig document as the API returns it (option dicts for the selects)."""
    all_ifs = ("lan", "opt1", "opt2", "wan")
    return {
        "netflow": {
            "capture": {
                "interfaces": _opts(*interfaces, extra=tuple(set(all_ifs) - set(interfaces))),
                "egress_only": _opts(*egress, extra=tuple(set(all_ifs) - set(egress))),
                "version": _opts(version, extra=tuple({"v5", "v9"} - {version})),
                "targets": _opts("127.0.0.1:2056"),
            },
            "collect": {"enable": collect},
            "activeTimeout": "1800",
            "inactiveTimeout": "15",
        }
    }


DESIRED = {
    "capture": {
        "interfaces": ["lan", "opt1"],
        "egress_only": [],
        "version": "v9",
        "targets": ["127.0.0.1:2056"],
    },
    "collect": {"enable": "1"},
}


@pytest.mark.asyncio
class TestNetflowSettings:
    async def test_get_uses_getconfig_and_unwraps(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _doc()
        got = await NetflowSettingsManager(mock_client).get()
        assert set(got) == {"capture", "collect", "activeTimeout", "inactiveTimeout"}
        mock_client.get.assert_awaited_once_with("diagnostics/netflow/getconfig")

    async def test_noop_when_matching_whatever_the_order(self, mock_client: AsyncMock) -> None:
        # the device lists opt1 before lan; the caller declares lan first
        mock_client.get.return_value = _doc(interfaces=("opt1", "lan"))
        result = await NetflowSettingsManager(mock_client).ensure("present", DESIRED)
        assert result.changed is False and result.action == "noop"
        mock_client.post.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_posts_setconfig_and_reconfigures(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            _doc(interfaces=("lan",)),
            _doc(interfaces=("opt1", "lan")),
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        result = await NetflowSettingsManager(mock_client).ensure("present", DESIRED)
        assert result.changed is True and result.action == "updated"
        mock_client.post.assert_awaited_once_with(
            "diagnostics/netflow/setconfig",
            {
                "netflow": {
                    "capture": {
                        "interfaces": "lan,opt1",
                        "egress_only": "",
                        "version": "v9",
                        "targets": "127.0.0.1:2056",
                    },
                    "collect": {"enable": "1"},
                }
            },
        )
        mock_client.reconfigure.assert_awaited_once_with(
            "diagnostics/netflow/reconfigure", timeout=60
        )

    async def test_egress_and_collect_drift_detected(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _doc(egress=("wan",), collect="0")
        result = await NetflowSettingsManager(mock_client).ensure(
            "present", DESIRED, check_mode=True
        )
        assert result.changed is True and result.action == "updated"
        mock_client.post.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_partial_document_only_diffs_what_is_passed(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _doc(interfaces=("lan",), collect="1")
        result = await NetflowSettingsManager(mock_client).ensure(
            "present", {"collect": {"enable": "1"}}
        )
        assert result.changed is False

    async def test_csv_string_is_accepted(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _doc(interfaces=("opt1", "lan"))
        result = await NetflowSettingsManager(mock_client).ensure(
            "present", {"capture": {"interfaces": "lan,opt1"}}
        )
        assert result.changed is False

    async def test_invalid_version_fails_before_any_call(self, mock_client: AsyncMock) -> None:
        with pytest.raises(FieldValidationError):
            await NetflowSettingsManager(mock_client).ensure(
                "present", {"capture": {"version": "v10"}}
            )
        mock_client.get.assert_not_awaited()

    async def test_absent_is_refused(self, mock_client: AsyncMock) -> None:
        with pytest.raises(ValueError, match="only support state='present'"):
            await NetflowSettingsManager(mock_client).ensure("absent", {})

    async def test_api_validation_error_propagates(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _doc(interfaces=("lan",))
        mock_client.post.side_effect = OpnsenseValidationError(
            "validation failed",
            validations={"netflow.capture.interfaces": "Option [nosuchif] not in list."},
        )
        with pytest.raises(OpnsenseValidationError):
            await NetflowSettingsManager(mock_client).ensure(
                "present", {"capture": {"interfaces": ["nosuchif"]}}
            )
        mock_client.reconfigure.assert_not_awaited()
