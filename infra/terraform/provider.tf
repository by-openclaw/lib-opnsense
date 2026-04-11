provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = var.proxmox_api_token
  insecure  = true

  ssh {
    agent    = true
    username = "root"

    node {
      name    = var.target_node
      address = "10.6.224.105"
      port    = 22222
    }
  }
}
