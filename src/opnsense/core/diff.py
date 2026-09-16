# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Diff engine — state comparison with OPNsense enum normalization.

Compares current API state against desired state and returns changed fields.
Handles OPNsense-specific enum dict formats transparently.

Zero imports from managers/ or client.py — independently reusable.

Usage::

    from opnsense.core.diff import DiffEngine

    engine = DiffEngine()
    changes = engine.compute_diff(current_state, desired_state)
"""

from __future__ import annotations

import logging
import re
from typing import Any

try:
    import bcrypt

    _HAS_BCRYPT = True
except ImportError:  # pragma: no cover — optional dependency
    _HAS_BCRYPT = False

logger = logging.getLogger(__name__)

# OPNsense UpdateOnlyTextField stores bcrypt hashes ($2y$ prefix).
# The search endpoint returns the hash; the get endpoint returns "".
# We use bcrypt.checkpw() to compare plaintext input against stored hash.
_BCRYPT_PREFIX_RE = "$2y$"

# Write-only fields (UpdateOnlyTextField and friends): the get endpoint returns "" for them, so an
# empty current value carries no information — it is not "the password is empty". Diffing it
# against the desired plaintext would re-write the same secret on every run. Compared only when
# the API hands back something (a hash, see above); otherwise left to create/rotation paths.
_WRITE_ONLY_KEY_RE = re.compile(r"(?i)(^|_)(password|passwd|secret|psk|apikey|api_key)($|_)")


class DiffEngine:
    """Stateless diff engine for OPNsense resource comparison.

    Handles two OPNsense enum dict formats:
        Format 1: ``{"selected": "1"}`` — simple selected value
        Format 2: ``{"lan": {"value": "LAN", "selected": 1}, ...}`` — enum dict
    """

    @staticmethod
    def normalize_value(value: Any) -> str:
        """Normalize an OPNsense API value for comparison.

        Handles enum dict formats and converts everything to string.

        Args:
            value: Raw value from the OPNsense API.

        Returns:
            Normalized string value suitable for comparison.
        """
        try:
            if isinstance(value, dict):
                if "selected" in value:
                    return str(value.get("selected", ""))
                # Format 2 option dict: single-select yields one key; a
                # multi-select yields every selected key as CSV, and none
                # selected yields "" (the API's "all"/unset value) — NOT the
                # dict's repr, which could never equal a desired string.
                if value and all(isinstance(opt, dict) for opt in value.values()):
                    return ",".join(
                        str(opt_key)
                        for opt_key, opt_val in value.items()
                        if opt_val.get("selected") in (1, "1", True)
                    )
            # OPNsense search endpoint returns native bool for "0"/"1" fields.
            # Normalize to "1"/"0" to match the string format used in create/update.
            if isinstance(value, bool):
                return "1" if value else "0"
            return str(value)
        except Exception as exc:
            logger.error(
                "normalize_value failed: %s",
                exc,
                extra={"action": "normalize_value_failed", "error": str(exc)},
            )
            raise

    @staticmethod
    def _csv_set(value: str) -> set[str]:
        """Split a CSV string into its non-empty, stripped tokens."""
        return {tok.strip() for tok in value.split(",") if tok.strip()}

    def compute_diff(
        self,
        current: dict[str, Any],
        desired: dict[str, Any],
    ) -> dict[str, str] | None:
        """Compare current state against desired and return changed fields.

        Only compares fields present in ``desired`` — extra fields in
        ``current`` are ignored (OPNsense returns many computed fields).

        Args:
            current: Current resource state from the API.
            desired: Desired resource parameters.

        Returns:
            Dict of field: desired_value for fields that differ, or None
            if no changes are needed.
        """
        try:
            diff: dict[str, str] = {}
            for key, desired_value in desired.items():
                current_value = current.get(key)
                if current_value is None and key not in current:
                    continue
                if (
                    current_value == ""
                    and str(desired_value) != ""
                    and _WRITE_ONLY_KEY_RE.search(key)
                ):
                    continue  # write-only field: the API never returns it — nothing to compare
                # Nested dict — recurse and compare sub-fields
                if isinstance(desired_value, dict) and isinstance(current_value, dict):
                    sub_diff = self.compute_diff(current_value, desired_value)
                    if sub_diff is not None:
                        diff[key] = str(desired_value)
                    continue
                normalized = self.normalize_value(current_value)
                desired_str = str(desired_value)
                # Multi-select option dicts compare as a SET of selected keys:
                # the caller's CSV order must not matter.
                if (
                    isinstance(current_value, dict)
                    and "selected" not in current_value
                    and "," in f"{normalized}{desired_str}"
                    and self._csv_set(normalized) == self._csv_set(desired_str)
                ):
                    continue
                if normalized != desired_str:
                    # OPNsense UpdateOnlyTextField: API returns bcrypt hash
                    # ($2y$...), input is plaintext. Use bcrypt.checkpw()
                    # to verify match instead of string comparison.
                    if (
                        _HAS_BCRYPT
                        and isinstance(normalized, str)
                        and normalized.startswith(_BCRYPT_PREFIX_RE)
                        and not desired_str.startswith(_BCRYPT_PREFIX_RE)
                    ):
                        try:
                            if bcrypt.checkpw(
                                desired_str.encode("utf-8"),
                                normalized.encode("utf-8"),
                            ):
                                continue  # password matches — no diff
                        except Exception:
                            pass  # bcrypt error — fall through to diff
                    diff[key] = desired_str
            return diff if diff else None
        except Exception as exc:
            logger.error(
                "compute_diff failed: %s",
                exc,
                extra={"action": "compute_diff_failed", "error": str(exc)},
            )
            raise
