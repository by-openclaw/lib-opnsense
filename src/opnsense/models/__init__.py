# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense data models — one typed frozen dataclass per API entity."""

from opnsense.models.acme.account import AcmeAccount
from opnsense.models.acme.action import AcmeAction
from opnsense.models.acme.certificate import AcmeCertificate
from opnsense.models.acme.settings import AcmeSettings
from opnsense.models.acme.validation import AcmeValidation
from opnsense.models.auth.group import AuthGroup
from opnsense.models.auth.user import AuthUser
from opnsense.models.base import EnsureResult
from opnsense.models.dhcp.kea4_peer import Kea4Peer
from opnsense.models.dhcp.kea4_reservation import Kea4Reservation
from opnsense.models.dhcp.kea4_subnet import Kea4Subnet
from opnsense.models.dhcp.kea6_reservation import Kea6Reservation
from opnsense.models.dhcp.kea6_subnet import Kea6Subnet
from opnsense.models.dns.ub_acl import UbAcl
from opnsense.models.dns.ub_dot import UbDot
from opnsense.models.dns.ub_forward import UbForward
from opnsense.models.dns.ub_host_alias import UbHostAlias
from opnsense.models.dns.ub_host_override import UbHostOverride
from opnsense.models.firewall.alias import FwAlias
from opnsense.models.firewall.category import FwCategory
from opnsense.models.firewall.dnat import FwDnatRule
from opnsense.models.firewall.filter import FwFilterRule
from opnsense.models.firewall.group import FwGroup
from opnsense.models.firewall.npt import FwNptRule
from opnsense.models.firewall.one_to_one import FwOneToOneRule
from opnsense.models.firewall.source_nat import FwSourceNatRule
from opnsense.models.interfaces.bridge import IfBridge
from opnsense.models.interfaces.gif import IfGif
from opnsense.models.interfaces.gre import IfGre
from opnsense.models.interfaces.lagg import IfLagg
from opnsense.models.interfaces.loopback import IfLoopback
from opnsense.models.interfaces.neighbor import IfNeighbor
from opnsense.models.interfaces.vip import IfVip
from opnsense.models.interfaces.vlan import IfVlan
from opnsense.models.interfaces.vxlan import IfVxlan
from opnsense.models.routing.gateway import RtGateway
from opnsense.models.routing.route import RtRoute
from opnsense.models.services.cp_zone import CpZone
from opnsense.models.services.cron_job import CronJob
from opnsense.models.services.ddns_account import DdnsAccount
from opnsense.models.services.syslog_dest import SyslogDest
from opnsense.models.shaper.ts_pipe import TsPipe
from opnsense.models.shaper.ts_queue import TsQueue
from opnsense.models.shaper.ts_rule import TsRule
from opnsense.models.trust.ca import TrustCa
from opnsense.models.trust.cert import TrustCert
from opnsense.models.vpn.ipsec_child import IpsecChild
from opnsense.models.vpn.ipsec_conn import IpsecConn
from opnsense.models.vpn.ipsec_keypair import IpsecKeypair
from opnsense.models.vpn.ipsec_local import IpsecLocal
from opnsense.models.vpn.ipsec_pool import IpsecPool
from opnsense.models.vpn.ipsec_psk import IpsecPsk
from opnsense.models.vpn.ipsec_remote import IpsecRemote
from opnsense.models.vpn.ipsec_vti import IpsecVti
from opnsense.models.vpn.ovpn_instance import OvpnInstance
from opnsense.models.vpn.wg_client import WgClient
from opnsense.models.vpn.wg_server import WgServer

__all__ = [
    "AcmeAccount",
    "AcmeAction",
    "AcmeCertificate",
    "AcmeSettings",
    "AcmeValidation",
    "AuthGroup",
    "AuthUser",
    "CpZone",
    "CronJob",
    "DdnsAccount",
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
