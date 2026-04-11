variable "proxmox_endpoint" {
  description = "Proxmox API endpoint (e.g. https://10.6.224.105:8006)"
  type        = string
}

variable "proxmox_api_token" {
  description = "Proxmox API token in format 'user@realm!tokenname=uuid'"
  type        = string
  sensitive   = true
}

variable "target_node" {
  description = "Proxmox node name (e.g. srv-proxmox-poc-01)"
  type        = string
  default     = "srv-proxmox-poc-01"
}

variable "iso_file" {
  description = "OPNsense ISO filename on poc-iso storage"
  type        = string
  default     = "OPNsense-26.1.2-dvd-amd64.iso"
}

variable "ssh_pubkey" {
  description = "SSH public key for svc-rune (ED25519, passphrase mandatory)"
  type        = string
  default     = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHbkOZYUkqJ9pdmDWDm87MBI1Rf4x7fZV3IMuitG+qlu svc-rune@by-systems.be"
}
