# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense data models — one typed frozen dataclass per API entity."""

from opnsense.models.auth_group import AuthGroup
from opnsense.models.auth_user import AuthUser
from opnsense.models.base import EnsureResult
from opnsense.models.cp_zone import CpZone
from opnsense.models.fw_alias import FwAlias
from opnsense.models.fw_category import FwCategory
from opnsense.models.fw_dnat import FwDnatRule
from opnsense.models.fw_filter import FwFilterRule
from opnsense.models.fw_group import FwGroup
from opnsense.models.fw_npt import FwNptRule
from opnsense.models.fw_one_to_one import FwOneToOneRule
from opnsense.models.fw_source_nat import FwSourceNatRule
from opnsense.models.if_bridge import IfBridge
from opnsense.models.if_gif import IfGif
from opnsense.models.if_gre import IfGre
from opnsense.models.if_lagg import IfLagg
from opnsense.models.if_loopback import IfLoopback
from opnsense.models.if_neighbor import IfNeighbor
from opnsense.models.if_vip import IfVip
from opnsense.models.if_vlan import IfVlan
from opnsense.models.if_vxlan import IfVxlan
from opnsense.models.ipsec_child import IpsecChild
from opnsense.models.ipsec_conn import IpsecConn
from opnsense.models.ipsec_keypair import IpsecKeypair
from opnsense.models.ipsec_local import IpsecLocal
from opnsense.models.ipsec_pool import IpsecPool
from opnsense.models.ipsec_psk import IpsecPsk
from opnsense.models.ipsec_remote import IpsecRemote
from opnsense.models.ipsec_vti import IpsecVti
from opnsense.models.kea4_peer import Kea4Peer
from opnsense.models.kea4_reservation import Kea4Reservation
from opnsense.models.kea4_subnet import Kea4Subnet
from opnsense.models.kea6_reservation import Kea6Reservation
from opnsense.models.kea6_subnet import Kea6Subnet
from opnsense.models.ovpn_instance import OvpnInstance
from opnsense.models.rt_gateway import RtGateway
from opnsense.models.rt_route import RtRoute
from opnsense.models.syslog_dest import SyslogDest
from opnsense.models.trust_ca import TrustCa
from opnsense.models.trust_cert import TrustCert
from opnsense.models.ts_pipe import TsPipe
from opnsense.models.ts_queue import TsQueue
from opnsense.models.ts_rule import TsRule
from opnsense.models.ub_acl import UbAcl
from opnsense.models.ub_dot import UbDot
from opnsense.models.ub_forward import UbForward
from opnsense.models.ub_host_alias import UbHostAlias
from opnsense.models.ub_host_override import UbHostOverride
from opnsense.models.wg_client import WgClient
from opnsense.models.wg_server import WgServer

__all__ = [
    "AuthGroup",
    "AuthUser",
    "CpZone",
    "EnsureResult",
    "FwAlias",
    "FwCategory",
    "FwDnatRule",
    "FwFilterRule",
    "FwGroup",
    "FwNptRule",
    "FwOneToOneRule",
    "FwSourceNatRule",
    "Kea4Peer",
    "Kea4Reservation",
    "Kea4Subnet",
    "Kea6Reservation",
    "Kea6Subnet",
    "OvpnInstance",
    "IfBridge",
    "IpsecChild",
    "IpsecConn",
    "IpsecKeypair",
    "IpsecLocal",
    "IpsecPool",
    "IpsecPsk",
    "IpsecRemote",
    "IpsecVti",
    "IfGif",
    "IfGre",
    "IfLagg",
    "IfLoopback",
    "IfNeighbor",
    "IfVip",
    "IfVlan",
    "IfVxlan",
    "RtGateway",
    "RtRoute",
    "SyslogDest",
    "TrustCa",
    "TrustCert",
    "TsPipe",
    "TsQueue",
    "TsRule",
    "UbAcl",
    "UbDot",
    "UbForward",
    "UbHostAlias",
    "UbHostOverride",
    "WgClient",
    "WgServer",
]
