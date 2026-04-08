# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.models.base — EnsureResult."""

from __future__ import annotations

import pytest

from opnsense.models.base import EnsureResult


class TestEnsureResult:
    """EnsureResult frozen dataclass."""

    def test_frozen(self) -> None:
        r = EnsureResult(changed=False, action="noop")
        with pytest.raises(AttributeError):
            r.uuid = "changed"  # type: ignore[misc]

    def test_noop(self) -> None:
        r = EnsureResult(changed=False, action="noop")
        assert r.changed is False
        assert r.uuid is None
        assert r.before is None
        assert r.after is None

    def test_created(self) -> None:
        r = EnsureResult(changed=True, action="created", uuid="abc", after={"name": "rune"})
        assert r.changed is True
        assert r.uuid == "abc"
        assert r.after == {"name": "rune"}
