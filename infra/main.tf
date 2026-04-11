################################################################################
# lib-opnsense — Integration Test Infrastructure (ADR-0032)
#
# Self-contained TF config for devs who want to run integration tests.
# Creates: SDN zone test (9 VLANs) + OPNsense VM + 3 LXCs
#
# Usage:
#   cd infra/
#   cp terraform.tfvars.example terraform.tfvars  # fill in Proxmox creds
#   terraform init
#   terraform plan
#   terraform apply
#   # Then: bootstrap OPNsense via console (see README.md)
#
# ISO download: https://opnsense.org/download/
#   Architecture: amd64, Type: dvd
#   Upload to Proxmox: poc-iso storage
################################################################################

locals {
  standard_ssh_keys = [
    var.ssh_pubkey,
  ]
}

################################################################################
# SDN Zone: test — 9 segments (ADR-0032)
# All dual-stack IPv4 + IPv6 ULA (IPv6 configured on OPNsense, not SDN)
################################################################################

resource "proxmox_sdn_zone_vlan" "test" {
  id     = "test"
  bridge = "vmbrAPPS"
  mtu    = 1500
  nodes  = [var.target_node]
}

# --- VNets ---

resource "proxmox_sdn_vnet" "tmgmt" {
  id         = "tmgmt"
  zone       = proxmox_sdn_zone_vlan.test.id
  alias      = "Test Management"
  tag        = 2010
  depends_on = [proxmox_sdn_zone_vlan.test]
}

resource "proxmox_sdn_vnet" "tdmz" {
  id         = "tdmz"
  zone       = proxmox_sdn_zone_vlan.test.id
  alias      = "Test DMZ"
  tag        = 2020
  depends_on = [proxmox_sdn_zone_vlan.test]
}

resource "proxmox_sdn_vnet" "tsvc" {
  id         = "tsvc"
  zone       = proxmox_sdn_zone_vlan.test.id
  alias      = "Test Services"
  tag        = 2030
  depends_on = [proxmox_sdn_zone_vlan.test]
}

resource "proxmox_sdn_vnet" "tvpn" {
  id         = "tvpn"
  zone       = proxmox_sdn_zone_vlan.test.id
  alias      = "Test VPN"
  tag        = 2040
  depends_on = [proxmox_sdn_zone_vlan.test]
}

resource "proxmox_sdn_vnet" "tiot" {
  id         = "tiot"
  zone       = proxmox_sdn_zone_vlan.test.id
  alias      = "Test IoT"
  tag        = 2100
  depends_on = [proxmox_sdn_zone_vlan.test]
}

resource "proxmox_sdn_vnet" "tvoip" {
  id         = "tvoip"
  zone       = proxmox_sdn_zone_vlan.test.id
  alias      = "Test VoIP"
  tag        = 2110
  depends_on = [proxmox_sdn_zone_vlan.test]
}

resource "proxmox_sdn_vnet" "tstor" {
  id         = "tstor"
  zone       = proxmox_sdn_zone_vlan.test.id
  alias      = "Test Storage"
  tag        = 2200
  depends_on = [proxmox_sdn_zone_vlan.test]
}

resource "proxmox_sdn_vnet" "tmedia" {
  id         = "tmedia"
  zone       = proxmox_sdn_zone_vlan.test.id
  alias      = "Test Media"
  tag        = 2300
  depends_on = [proxmox_sdn_zone_vlan.test]
}

resource "proxmox_sdn_vnet" "tcctv" {
  id         = "tcctv"
  zone       = proxmox_sdn_zone_vlan.test.id
  alias      = "Test CCTV"
  tag        = 2400
  depends_on = [proxmox_sdn_zone_vlan.test]
}

# --- Subnets ---

resource "proxmox_sdn_subnet" "tmgmt" {
  vnet       = proxmox_sdn_vnet.tmgmt.id
  cidr       = "10.11.1.0/24"
  gateway    = "10.11.1.1"
  depends_on = [proxmox_sdn_vnet.tmgmt]
}

resource "proxmox_sdn_subnet" "tdmz" {
  vnet       = proxmox_sdn_vnet.tdmz.id
  cidr       = "10.11.2.0/24"
  gateway    = "10.11.2.1"
  depends_on = [proxmox_sdn_vnet.tdmz]
}

resource "proxmox_sdn_subnet" "tsvc" {
  vnet       = proxmox_sdn_vnet.tsvc.id
  cidr       = "10.11.3.0/24"
  gateway    = "10.11.3.1"
  depends_on = [proxmox_sdn_vnet.tsvc]
}

resource "proxmox_sdn_subnet" "tvpn" {
  vnet       = proxmox_sdn_vnet.tvpn.id
  cidr       = "10.11.4.0/24"
  gateway    = "10.11.4.1"
  depends_on = [proxmox_sdn_vnet.tvpn]
}

resource "proxmox_sdn_subnet" "tiot" {
  vnet       = proxmox_sdn_vnet.tiot.id
  cidr       = "10.11.10.0/24"
  gateway    = "10.11.10.1"
  depends_on = [proxmox_sdn_vnet.tiot]
}

resource "proxmox_sdn_subnet" "tvoip" {
  vnet       = proxmox_sdn_vnet.tvoip.id
  cidr       = "10.11.11.0/24"
  gateway    = "10.11.11.1"
  depends_on = [proxmox_sdn_vnet.tvoip]
}

resource "proxmox_sdn_subnet" "tstor" {
  vnet       = proxmox_sdn_vnet.tstor.id
  cidr       = "10.11.20.0/24"
  gateway    = "10.11.20.1"
  depends_on = [proxmox_sdn_vnet.tstor]
}

resource "proxmox_sdn_subnet" "tmedia" {
  vnet       = proxmox_sdn_vnet.tmedia.id
  cidr       = "10.11.30.0/24"
  gateway    = "10.11.30.1"
  depends_on = [proxmox_sdn_vnet.tmedia]
}

resource "proxmox_sdn_subnet" "tcctv" {
  vnet       = proxmox_sdn_vnet.tcctv.id
  cidr       = "10.11.40.0/24"
  gateway    = "10.11.40.1"
  depends_on = [proxmox_sdn_vnet.tcctv]
}

resource "proxmox_sdn_applier" "test" {
  depends_on = [
    proxmox_sdn_zone_vlan.test,
    proxmox_sdn_vnet.tmgmt, proxmox_sdn_vnet.tdmz, proxmox_sdn_vnet.tsvc,
    proxmox_sdn_vnet.tvpn, proxmox_sdn_vnet.tiot, proxmox_sdn_vnet.tvoip,
    proxmox_sdn_vnet.tstor, proxmox_sdn_vnet.tmedia, proxmox_sdn_vnet.tcctv,
    proxmox_sdn_subnet.tmgmt, proxmox_sdn_subnet.tdmz, proxmox_sdn_subnet.tsvc,
    proxmox_sdn_subnet.tvpn, proxmox_sdn_subnet.tiot, proxmox_sdn_subnet.tvoip,
    proxmox_sdn_subnet.tstor, proxmox_sdn_subnet.tmedia, proxmox_sdn_subnet.tcctv,
  ]
}

################################################################################
# OPNsense test VM — vm-fw-test-01, VMID 1100 (ADR-0003, ADR-0027)
#
# 4 NICs: LAN first (vtnet0 = OPNsense default), then 3x WAN
# After terraform apply: bootstrap via Proxmox noVNC console (see README.md)
################################################################################

resource "proxmox_virtual_environment_vm" "fw_test_01" {
  name      = "vm-fw-test-01"
  vm_id     = 1100
  node_name = var.target_node

  tags = ["layer0", "opnsense", "env-test"]

  bios          = "ovmf"
  machine       = "q35"
  scsi_hardware = "virtio-scsi-single"
  tablet_device = false

  on_boot    = true
  started    = true
  protection = false

  agent { enabled = false }

  cpu {
    cores      = 2
    sockets    = 1
    type       = "host"
    hotplugged = 0
    flags      = ["+aes"]
  }

  memory {
    dedicated = 4096
    floating  = 0
  }

  disk {
    datastore_id = "poc-data"
    interface    = "scsi0"
    size         = 20
    file_format  = "raw"
    iothread     = true
    discard      = "on"
    cache        = "none"
    ssd          = true
  }

  efi_disk {
    datastore_id      = "poc-data"
    file_format       = "raw"
    type              = "4m"
    pre_enrolled_keys = false
  }

  cdrom {
    file_id   = "poc-iso:iso/${var.iso_file}"
    interface = "ide0"
  }

  boot_order = ["scsi0", "ide0"]

  # vtnet0 — LAN (VLAN trunk)
  network_device {
    bridge   = "vmbrAPPS"
    model    = "virtio"
    firewall = false
    queues   = 2
  }

  # vtnet1 — WAN1 (future Proximus)
  network_device {
    bridge   = "vmbrWAN1"
    model    = "virtio"
    firewall = false
    queues   = 2
  }

  # vtnet2 — WAN2 (future Telenet)
  network_device {
    bridge   = "vmbrWAN2"
    model    = "virtio"
    firewall = false
    queues   = 2
  }

  # vtnet3 — WAN3 (current internet)
  network_device {
    bridge   = "vmbrWAN3"
    model    = "virtio"
    firewall = false
    queues   = 2
  }

  vga {
    type   = "std"
    memory = 16
  }

  serial_device {}

  depends_on = [proxmox_sdn_applier.test]
}

################################################################################
# Test LXCs — uncomment after OPNsense is bootstrapped + VLANs configured
################################################################################

# resource "proxmox_virtual_environment_container" "webdmz" {
#   description = "DNAT target for firewall integration tests"
#   node_name   = var.target_node
#   vm_id       = 1500
#
#   initialization {
#     hostname = "lxc-webdmz-test-01"
#     ip_config {
#       ipv4 { address = "10.11.2.10/24", gateway = "10.11.2.1" }
#     }
#     user_account { keys = [var.ssh_pubkey] }
#   }
#
#   network_interface { name = "eth0", bridge = "tdmz" }
#   operating_system { template_file_id = "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst" }
#   disk { datastore_id = "poc-data", size = 4 }
#   cpu { cores = 1 }
#   memory { dedicated = 256 }
# }

# resource "proxmox_virtual_environment_container" "websrv" {
#   description = "Internal service for routing/shaper integration tests"
#   node_name   = var.target_node
#   vm_id       = 1501
#
#   initialization {
#     hostname = "lxc-websrv-test-01"
#     ip_config {
#       ipv4 { address = "10.11.3.10/24", gateway = "10.11.3.1" }
#     }
#     user_account { keys = [var.ssh_pubkey] }
#   }
#
#   network_interface { name = "eth0", bridge = "tsvc" }
#   operating_system { template_file_id = "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst" }
#   disk { datastore_id = "poc-data", size = 4 }
#   cpu { cores = 1 }
#   memory { dedicated = 256 }
# }

# resource "proxmox_virtual_environment_container" "dhcpclient" {
#   description = "DHCP lease validation (deploy after Kea configured)"
#   node_name   = var.target_node
#   vm_id       = 1502
#
#   initialization {
#     hostname = "lxc-dhcpclient-test-01"
#     ip_config {
#       ipv4 { address = "dhcp" }
#     }
#     user_account { keys = [var.ssh_pubkey] }
#   }
#
#   network_interface { name = "eth0", bridge = "tdmz" }
#   operating_system { template_file_id = "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst" }
#   disk { datastore_id = "poc-data", size = 4 }
#   cpu { cores = 1 }
#   memory { dedicated = 256 }
# }

################################################################################
# Outputs
################################################################################

output "fw_test_01_vm_id" {
  value = proxmox_virtual_environment_vm.fw_test_01.vm_id
}

output "sdn_zone_id" {
  value = proxmox_sdn_zone_vlan.test.id
}
