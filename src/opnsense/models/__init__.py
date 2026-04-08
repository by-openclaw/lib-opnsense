# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense data models — one typed frozen dataclass per API entity."""

from opnsense.models.auth_group import AuthGroup
from opnsense.models.auth_user import AuthUser
from opnsense.models.base import EnsureResult
from opnsense.models.fw_alias import FwAlias
from opnsense.models.fw_category import FwCategory
from opnsense.models.fw_dnat import FwDnatRule
from opnsense.models.fw_filter import FwFilterRule
from opnsense.models.fw_group import FwGroup
from opnsense.models.fw_one_to_one import FwOneToOneRule
from opnsense.models.fw_source_nat import FwSourceNatRule
from opnsense.models.if_vip import IfVip
from opnsense.models.if_vlan import IfVlan
from opnsense.models.ts_pipe import TsPipe

__all__ = [
    "AuthGroup",
    "AuthUser",
    "EnsureResult",
    "FwAlias",
    "FwCategory",
    "FwDnatRule",
    "FwFilterRule",
    "FwGroup",
    "FwOneToOneRule",
    "FwSourceNatRule",
    "IfVip",
    "IfVlan",
    "TsPipe",
]
