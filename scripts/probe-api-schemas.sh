#!/usr/bin/env bash
# =============================================================================
# probe-api-schemas.sh — OPNsense API schema probe (read-only)
# =============================================================================
# Copyright (c) BY-SYSTEMS SRL
# SPDX-License-Identifier: MIT
# https://github.com/by-openclaw/lib-opnsense
# =============================================================================
# Purpose:  GET every get_<entity> (no UUID) to capture empty schemas (fields,
#           enums, defaults).  POST every search_<entity> to capture row shape.
#           GET global /get endpoints for service-level settings.
#
# Output:   JSON files in docs/api/data/{version}/, one per endpoint.
#           Then calls build-api-schema-audit.sh to produce the .md audit.
#           Each probe run is stored under a versioned subdirectory so that
#           multiple OPNsense versions can be compared via git diff.
#
# Usage:    ./probe-api-schemas.sh
#           Requires: OPN_HOST, OPN_KEY, OPN_SECRET env vars
#
# Safety:   ALL calls are read-only (GET schema, GET/POST search).
#           No config is created, modified, or deleted.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_DIR="$(dirname "$SCRIPT_DIR")"
PROBE_BASE="${TOOL_DIR}/docs/api/data"
ENV_FILE="${TOOL_DIR}/.env"
SLEEP_SECONDS="${OPN_SLEEP_SECONDS:-0.3}"

SAFE_DENY_RE='/(add|set|del|delete|toggle|reconfigure|apply|start|stop|restart|rollback|revert|import|export|move|upload|flush)(/|$)'
SAFE_ALLOW_POST_RE='/(search[^/]*|is_enabled|status|show|meta|providers|running|info)(/|$)'

# Field names whose VALUES must never be written to disk. The probe captures live
# responses, so a settings endpoint will happily hand back an enrolment key, a
# relay password or a password hash — and these files are committed. Values are
# replaced with <REDACTED:{field}>; the field name, type and length stay visible,
# which is all the schema audit ever needed.
SECRET_FIELDS_RE='^(enroll_key|api_key|apikey|secret|api_secret|password|passwd|passphrase|token|private_key|privkey|prv|prv_payload|psk|pre_shared_key|apikeys|otp_seed)$'
# Public material is deliberately NOT redacted — 'crt'/'crt_payload' are
# certificates, 'pubkey'/'public-key' are public halves, 'uuid' is an id.
# Redacting those would gut the schema audit for no security gain.

# --- CLI overrides ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)        OPN_HOST="$2"; shift 2 ;;
    --key-file)    OPN_KEY="$(<"$2")"; shift 2 ;;
    --secret-file) OPN_SECRET="$(<"$2")"; shift 2 ;;
    --outdir)      OUTDIR="$2"; shift 2 ;;
    --sleep)       SLEEP_SECONDS="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

# --- Load credentials ---
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE"
fi

: "${OPN_HOST:?Set OPN_HOST (e.g. https://opnsense.example.com)}"
: "${OPN_KEY:?Set OPN_KEY (API key)}"
: "${OPN_SECRET:?Set OPN_SECRET (API secret)}"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ---------------------------------------------------------------------------
# Version detection — call /api/core/firmware/info to get OPNsense version
# ---------------------------------------------------------------------------
echo "Detecting OPNsense firmware version..."
FIRMWARE_JSON=$(curl -sk \
  -u "${OPN_KEY}:${OPN_SECRET}" \
  "${OPN_HOST}/api/core/firmware/info" 2>/dev/null || echo '{}')

OPN_VERSION=$(echo "$FIRMWARE_JSON" | jq -r '.product_version // "unknown"' 2>/dev/null || echo "unknown")
OPN_PRODUCT=$(echo "$FIRMWARE_JSON" | jq -r '.product_name // "OPNsense"' 2>/dev/null || echo "OPNsense")
OPN_ARCH=$(echo "$FIRMWARE_JSON" | jq -r '.product.CORE_ARCH // .product.product_arch // "unknown"' 2>/dev/null || echo "unknown")
OPN_NICKNAME=$(echo "$FIRMWARE_JSON" | jq -r '.product_nickname // ""' 2>/dev/null || echo "")
OPN_OS=$(echo "$FIRMWARE_JSON" | jq -r '.product.product_check.os_version // ""' 2>/dev/null || echo "")

if [[ "$OPN_VERSION" == "unknown" || "$OPN_VERSION" == "null" ]]; then
  echo "WARNING: Could not detect OPNsense version from /api/core/firmware/info" >&2
  echo "Falling back to 'unknown' — probe will continue but version tracking is degraded." >&2
  OPN_VERSION="unknown"
fi

echo "Detected: ${OPN_PRODUCT} ${OPN_VERSION} (${OPN_ARCH})"

# ---------------------------------------------------------------------------
# Versioned output directory — one subdir per OPNsense version
# ---------------------------------------------------------------------------
VERSION_SLUG="${OPN_VERSION//[^a-zA-Z0-9._-]/_}"
OUTDIR="${PROBE_BASE}/${VERSION_SLUG}"
MANIFEST_FILE="${OUTDIR}/manifest.jsonl"
VERSION_FILE="${OUTDIR}/version.json"

mkdir -p "$OUTDIR"
: > "$MANIFEST_FILE"

# Write version metadata
jq -nc \
  --arg version "$OPN_VERSION" \
  --arg product "$OPN_PRODUCT" \
  --arg arch "$OPN_ARCH" \
  --arg nickname "$OPN_NICKNAME" \
  --arg os "$OPN_OS" \
  --arg host "$OPN_HOST" \
  --arg timestamp "$TIMESTAMP" \
  --arg script "probe-api-schemas.sh" \
  '{opnsense_version:$version, product:$product, arch:$arch, nickname:$nickname, os:$os, host:$host, probe_timestamp:$timestamp, probe_script:$script}' \
  > "$VERSION_FILE"

# Symlink "latest" to current version for convenience
ln -sfn "$VERSION_SLUG" "${PROBE_BASE}/latest"

LOG="${OUTDIR}/probe-${TIMESTAMP}.log"

echo "=== OPNsense API Schema Probe — $TIMESTAMP ===" | tee "$LOG"
echo "Host: $OPN_HOST" | tee -a "$LOG"
echo "Version: ${OPN_PRODUCT} ${OPN_VERSION} (${OPN_ARCH})" | tee -a "$LOG"
echo "Output: $OUTDIR" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# ---------------------------------------------------------------------------
# Endpoint registry
# Each line: <type>|<endpoint>|<label>
#   schema = GET empty schema (field discovery)
#   search = POST search (row shape discovery)
#   global = GET global config / status
# ---------------------------------------------------------------------------
ENDPOINTS=(
  # --- Firewall ---
  "schema|firewall/alias/get_item|fw-alias"
  "search|firewall/alias/search_item|fw-alias"
  "schema|firewall/filter/get_rule|fw-filter-rule"
  "search|firewall/filter/search_rule|fw-filter-rule"
  "schema|firewall/source_nat/get_rule|fw-snat-rule"
  "search|firewall/source_nat/search_rule|fw-snat-rule"
  "schema|firewall/d_nat/get_rule|fw-dnat-rule"
  "search|firewall/d_nat/search_rule|fw-dnat-rule"
  "schema|firewall/one_to_one/get_rule|fw-1to1-rule"
  "search|firewall/one_to_one/search_rule|fw-1to1-rule"
  "schema|firewall/npt/get_rule|fw-npt-rule"
  "search|firewall/npt/search_rule|fw-npt-rule"
  "schema|firewall/group/get_item|fw-group"
  "search|firewall/group/search_item|fw-group"
  "schema|firewall/category/get_item|fw-category"
  "search|firewall/category/search_item|fw-category"
  # filter_base/get is the abstract parent controller — not callable directly.
  # Inherited by filter, d_nat, source_nat, one_to_one, npt controllers.

  # --- Interfaces ---
  "schema|interfaces/vlan_settings/get_item|if-vlan"
  "search|interfaces/vlan_settings/search_item|if-vlan"
  "schema|interfaces/bridge_settings/get_item|if-bridge"
  "search|interfaces/bridge_settings/search_item|if-bridge"
  "schema|interfaces/vip_settings/get_item|if-vip"
  "search|interfaces/vip_settings/search_item|if-vip"
  "schema|interfaces/loopback_settings/get_item|if-loopback"
  "search|interfaces/loopback_settings/search_item|if-loopback"
  "schema|interfaces/lagg_settings/get_item|if-lagg"
  "search|interfaces/lagg_settings/search_item|if-lagg"
  "schema|interfaces/gre_settings/get_item|if-gre"
  "search|interfaces/gre_settings/search_item|if-gre"
  "schema|interfaces/gif_settings/get_item|if-gif"
  "search|interfaces/gif_settings/search_item|if-gif"
  "schema|interfaces/vxlan_settings/get_item|if-vxlan"
  "search|interfaces/vxlan_settings/search_item|if-vxlan"
  "schema|interfaces/neighbor_settings/get_item|if-neighbor"
  "search|interfaces/neighbor_settings/search_item|if-neighbor"
  "global|interfaces/overview/interfaces_info|if-overview"
  "global|interfaces/settings/get|if-settings"

  # --- Routes / Routing ---
  "schema|routes/routes/getroute|route"
  "search|routes/routes/searchroute|route"
  "global|routes/gateway/status|gw-status"
  "schema|routing/settings/get_gateway|routing-gw"
  "search|routing/settings/search_gateway|routing-gw"
  "global|routing/settings/get|routing-settings"

  # --- Unbound DNS ---
  "schema|unbound/settings/get_forward|ub-forward"
  "search|unbound/settings/search_forward|ub-forward"
  "schema|unbound/settings/get_host_override|ub-host-override"
  "search|unbound/settings/search_host_override|ub-host-override"
  "schema|unbound/settings/get_host_alias|ub-host-alias"
  "search|unbound/settings/search_host_alias|ub-host-alias"
  "schema|unbound/settings/get_acl|ub-acl"
  "search|unbound/settings/search_acl|ub-acl"
  "schema|unbound/settings/get_dnsbl|ub-dnsbl"
  "search|unbound/settings/search_dnsbl|ub-dnsbl"
  "global|unbound/settings/get|ub-settings"
  "global|unbound/service/status|ub-service"
  "global|unbound/diagnostics/stats|ub-diag-stats"

  # --- Kea DHCP ---
  "schema|kea/dhcpv4/get_subnet|kea4-subnet"
  "search|kea/dhcpv4/search_subnet|kea4-subnet"
  "schema|kea/dhcpv4/get_reservation|kea4-reservation"
  "search|kea/dhcpv4/search_reservation|kea4-reservation"
  "schema|kea/dhcpv4/get_peer|kea4-peer"
  "search|kea/dhcpv4/search_peer|kea4-peer"
  "global|kea/dhcpv4/get|kea4-global"
  "schema|kea/dhcpv6/get_subnet|kea6-subnet"
  "search|kea/dhcpv6/search_subnet|kea6-subnet"
  "schema|kea/dhcpv6/get_reservation|kea6-reservation"
  "search|kea/dhcpv6/search_reservation|kea6-reservation"
  "global|kea/dhcpv6/get|kea6-global"
  "global|kea/ctrl_agent/get|kea-ctrl-agent"
  "global|kea/service/status|kea-service"

  # --- WireGuard ---
  "schema|wireguard/server/get_server|wg-server"
  "search|wireguard/server/search_server|wg-server"
  "schema|wireguard/client/get_client|wg-client"
  "search|wireguard/client/search_client|wg-client"
  "global|wireguard/general/get|wg-general"
  "global|wireguard/service/status|wg-service"
  "global|wireguard/service/show|wg-show"

  # --- OpenVPN ---
  "schema|openvpn/instances/get|ovpn-instance"
  "search|openvpn/instances/search|ovpn-instance"
  "schema|openvpn/client_overwrites/get|ovpn-cso"
  "search|openvpn/client_overwrites/search|ovpn-cso"
  "global|openvpn/service/search_sessions|ovpn-sessions"
  "global|openvpn/service/search_routes|ovpn-routes"

  # --- IPsec ---
  "schema|ipsec/connections/get_connection|ipsec-conn"
  "search|ipsec/connections/search_connection|ipsec-conn"
  "schema|ipsec/connections/get_child|ipsec-child"
  "search|ipsec/connections/search_child|ipsec-child"
  "schema|ipsec/connections/get_local|ipsec-local"
  "search|ipsec/connections/search_local|ipsec-local"
  "schema|ipsec/connections/get_remote|ipsec-remote"
  "search|ipsec/connections/search_remote|ipsec-remote"
  "schema|ipsec/key_pairs/get_item|ipsec-keypair"
  "search|ipsec/key_pairs/search_item|ipsec-keypair"
  "schema|ipsec/pre_shared_keys/get_item|ipsec-psk"
  "search|ipsec/pre_shared_keys/search_item|ipsec-psk"
  "schema|ipsec/pools/get|ipsec-pool"
  "search|ipsec/pools/search|ipsec-pool"
  "schema|ipsec/vti/get|ipsec-vti"
  "search|ipsec/vti/search|ipsec-vti"
  "global|ipsec/connections/is_enabled|ipsec-enabled"
  "global|ipsec/service/status|ipsec-service"
  "global|ipsec/settings/get|ipsec-settings"

  # --- IDS / Suricata ---
  "global|ids/settings/get|ids-settings"
  "schema|ids/settings/get_policy|ids-policy"
  "search|ids/settings/search_policy|ids-policy"
  "schema|ids/settings/get_user_rule|ids-user-rule"
  "search|ids/settings/search_user_rule|ids-user-rule"
  "schema|ids/settings/get_policy_rule|ids-policy-rule"
  "search|ids/settings/search_policy_rule|ids-policy-rule"
  "global|ids/service/status|ids-service"

  # --- Traffic Shaper ---
  "schema|trafficshaper/settings/get_pipe|ts-pipe"
  "search|trafficshaper/settings/search_pipes|ts-pipe"
  "schema|trafficshaper/settings/get_queue|ts-queue"
  "search|trafficshaper/settings/search_queues|ts-queue"
  "schema|trafficshaper/settings/get_rule|ts-rule"
  "search|trafficshaper/settings/search_rules|ts-rule"
  "global|trafficshaper/settings/get|ts-settings"
  "global|trafficshaper/service/statistics|ts-stats"

  # --- Syslog ---
  "schema|syslog/settings/get_destination|syslog-dest"
  "search|syslog/settings/search_destinations|syslog-dest"
  "global|syslog/settings/get|syslog-settings"
  "global|syslog/service/status|syslog-service"

  # --- Cron ---
  "schema|cron/settings/get_job|cron-job"
  "search|cron/settings/search_jobs|cron-job"
  "global|cron/settings/get|cron-settings"

  # --- Auth ---
  "schema|auth/user/get|auth-user"
  "search|auth/user/search|auth-user"
  "schema|auth/group/get|auth-group"
  "search|auth/group/search|auth-group"
  "global|auth/priv/get|auth-priv"

  # --- Trust ---
  "schema|trust/ca/get|trust-ca"
  "search|trust/ca/search|trust-ca"
  "schema|trust/cert/get|trust-cert"
  "search|trust/cert/search|trust-cert"
  "global|trust/crl/search|trust-crl"
  "global|trust/settings/get|trust-settings"

  # --- Captive Portal ---
  "schema|captiveportal/settings/get_zone|cp-zone"
  "search|captiveportal/settings/search_zones|cp-zone"
  "global|captiveportal/session/zones|cp-session-zones"
  "global|captiveportal/service/status|cp-service"

  # --- Dnsmasq ---
  "schema|dnsmasq/settings/get_host|dnsmasq-host"
  "search|dnsmasq/settings/search_host|dnsmasq-host"
  "schema|dnsmasq/settings/get_domain|dnsmasq-domain"
  "search|dnsmasq/settings/search_domain|dnsmasq-domain"
  "schema|dnsmasq/settings/get_range|dnsmasq-range"
  "search|dnsmasq/settings/search_range|dnsmasq-range"
  "schema|dnsmasq/settings/get_option|dnsmasq-option"
  "search|dnsmasq/settings/search_option|dnsmasq-option"
  "schema|dnsmasq/settings/get_boot|dnsmasq-boot"
  "search|dnsmasq/settings/search_boot|dnsmasq-boot"
  "schema|dnsmasq/settings/get_tag|dnsmasq-tag"
  "search|dnsmasq/settings/search_tag|dnsmasq-tag"
  "global|dnsmasq/settings/get|dnsmasq-settings"
  "global|dnsmasq/service/status|dnsmasq-service"

  # --- DHCP Relay ---
  "schema|dhcrelay/settings/get_dest|dhcrelay-dest"
  "search|dhcrelay/settings/search_dest|dhcrelay-dest"
  "schema|dhcrelay/settings/get_relay|dhcrelay-relay"
  "search|dhcrelay/settings/search_relay|dhcrelay-relay"
  "global|dhcrelay/settings/get|dhcrelay-settings"

  # --- Monit ---
  "schema|monit/settings/get_alert|monit-alert"
  "search|monit/settings/search_alert|monit-alert"
  "schema|monit/settings/get_service|monit-service"
  "search|monit/settings/search_service|monit-service"
  "schema|monit/settings/get_test|monit-test"
  "search|monit/settings/search_test|monit-test"
  "global|monit/settings/get|monit-settings"
  "global|monit/service/status|monit-svc-status"

  # --- Chrony (replaces NTPd, requires os-chrony plugin) ---
  "global|chrony/general/get|chrony-general"
  "global|chrony/service/status|chrony-service"

  # --- LLDP (requires os-lldpd plugin) ---
  "global|lldpd/general/get|lldpd-general"
  "global|lldpd/service/status|lldpd-service"

  # --- Removed in 26.x (kept as comments for reference) ---
  # radvd: removed from OPNsense 25.7+, router advertisements moved to core
  # ntpd: replaced by os-chrony plugin
  # hostdiscovery: removed, no replacement

  # --- Core ---
  "global|core/system/status|core-system"
  "global|core/firmware/info|core-firmware-info"
  "global|core/firmware/status|core-firmware-status"
  "global|core/firmware/running|core-firmware-running"
  "global|core/backup/providers|core-backup-providers"
  "schema|core/tunables/get_item|core-tunable"
  "search|core/tunables/search_item|core-tunable"
  "global|core/tunables/get|core-tunables"
  "global|core/hasync/get|core-hasync"
  "global|core/snapshots/is_supported|core-zfs-supported"
  "search|core/snapshots/search|core-snapshots"
  "global|core/service/search|core-services"

  # --- Diagnostics ---
  "global|diagnostics/system/system_information|diag-sysinfo"
  "global|diagnostics/system/system_resources|diag-resources"
  "global|diagnostics/system/system_time|diag-time"
  "global|diagnostics/system/system_temperature|diag-temp"
  "global|diagnostics/system/system_disk|diag-disk"
  "global|diagnostics/system/memory|diag-memory"
  "global|diagnostics/interface/get_arp|diag-arp"
  "global|diagnostics/interface/get_ndp|diag-ndp"
  "global|diagnostics/interface/get_interface_config|diag-ifconfig"
  "global|diagnostics/interface/get_interface_names|diag-ifnames"
  "global|diagnostics/interface/get_interface_statistics|diag-ifstats"
  "global|diagnostics/interface/get_routes|diag-routes"
  "global|diagnostics/interface/get_vip_status|diag-vip"
  "global|diagnostics/interface/get_protocol_statistics|diag-proto"
  "global|diagnostics/firewall/stats|diag-fw-stats"
  "global|diagnostics/firewall/list_rule_ids|diag-fw-ruleids"
  "global|diagnostics/netflow/is_enabled|diag-netflow-enabled"
  "global|diagnostics/netflow/status|diag-netflow-status"
  # --- CrowdSec (os-crowdsec) ---
  # General extends ApiMutableModelControllerBase -> get/set (settings are writable).
  # Service extends ApiMutableServiceControllerBase -> status/start/stop/restart.
  # Bouncers/Machines/Collections/Decisions extend ApiControllerBase -> search only.
  # Probed read-only: no set/del/start/stop is ever called from here.
  "global|crowdsec/general/get|crowdsec-general"
  "global|crowdsec/service/status|crowdsec-service"
  # NOT probed: crowdsec/version/get returns PLAIN TEXT (raw `cscli version`
  # output), not JSON, so it has no schema to capture and would write an
  # invalid .json artefact. VersionManager must parse it as text.
  "search|crowdsec/bouncers/search|crowdsec-bouncers"
  "search|crowdsec/machines/search|crowdsec-machines"
  "search|crowdsec/collections/search|crowdsec-collections"
  "search|crowdsec/decisions/search|crowdsec-decisions"
)

# ---------------------------------------------------------------------------
# Probe loop
# ---------------------------------------------------------------------------
TOTAL=${#ENDPOINTS[@]}
OK=0
FAIL=0

for entry in "${ENDPOINTS[@]}"; do
  IFS='|' read -r type endpoint label <<< "$entry"
  safe_name="${label}__${type}"
  outfile="${OUTDIR}/${safe_name}.json"
  endpoint_path="/api/${endpoint}"
  body_file="${OUTDIR}/${safe_name}.request.json"

  if [[ "$endpoint_path" =~ $SAFE_DENY_RE ]]; then
    echo "Refusing unsafe endpoint in registry: ${endpoint_path}" >&2
    exit 3
  fi

  if [[ "$type" == "search" ]]; then
    method="POST"
    if [[ ! "$endpoint_path" =~ $SAFE_ALLOW_POST_RE ]]; then
      echo "Refusing non-allowlisted POST endpoint in registry: ${endpoint_path}" >&2
      exit 4
    fi
    printf '%s\n' '{"current":1,"rowCount":5,"searchPhrase":""}' > "$body_file"
    http_code=$(curl -sk -o "$outfile" -w "%{http_code}" \
      -X POST \
      -H 'Content-Type: application/json' \
      --data @"$body_file" \
      -u "${OPN_KEY}:${OPN_SECRET}" \
      "${OPN_HOST}${endpoint_path}" 2>/dev/null || echo "000")
  else
    method="GET"
    # A GET carries no body, but the file is committed and check-json rejects an
    # empty file. Write an empty JSON object so the artefact is valid and the
    # hook can still catch a genuinely malformed request body.
    printf '%s\n' '{}' > "$body_file"
    http_code=$(curl -sk -o "$outfile" -w "%{http_code}" \
      -u "${OPN_KEY}:${OPN_SECRET}" \
      "${OPN_HOST}${endpoint_path}" 2>/dev/null || echo "000")
  fi

  # Redact secret values BEFORE the file is ever read, audited or committed.
  if [[ -s "$outfile" ]] && jq -e . "$outfile" >/dev/null 2>&1; then
    jq --arg re "$SECRET_FIELDS_RE" '
      def redact:
        if type == "object" then
          with_entries(
            if (.key | test($re; "i")) and (.value | type == "string") and (.value | length > 0)
            then .value = "<REDACTED:" + .key + ">"
            else .value |= redact
            end
          )
        elif type == "array" then map(redact)
        else .
        end;
      redact' "$outfile" > "${outfile}.redacted" 2>/dev/null \
      && mv "${outfile}.redacted" "$outfile" \
      || rm -f "${outfile}.redacted"
  fi

  # Store HTTP code alongside JSON
  echo "$http_code" > "${OUTDIR}/${safe_name}.http"

  jq -nc \
    --arg label "$label" \
    --arg type "$type" \
    --arg method "$method" \
    --arg path "$endpoint_path" \
    --arg requestBodyFile "$body_file" \
    --arg responseFile "$outfile" \
    --arg httpCode "$http_code" \
    '{label:$label,type:$type,method:$method,path:$path,requestBodyFile:$requestBodyFile,responseFile:$responseFile,httpCode:$httpCode}' >> "$MANIFEST_FILE"

  if [[ "$http_code" == "200" ]]; then
    status="OK"
    OK=$((OK + 1))
  else
    status="HTTP_${http_code}"
    FAIL=$((FAIL + 1))
  fi

  printf "%-4s %-12s %-55s %s\n" "$method" "$status" "$endpoint_path" "$label" | tee -a "$LOG"
  sleep "$SLEEP_SECONDS"
done

echo "" | tee -a "$LOG"
echo "=== Summary ===" | tee -a "$LOG"
echo "Total: $TOTAL | OK: $OK | Failed: $FAIL" | tee -a "$LOG"
echo "JSON output: $OUTDIR" | tee -a "$LOG"
echo "Log: $LOG" | tee -a "$LOG"

# ---------------------------------------------------------------------------
# Build the .md audit
# ---------------------------------------------------------------------------
echo ""
echo "Building .md audit from JSON schemas..."
"${SCRIPT_DIR}/build-api-schema-audit.sh" --indir "$OUTDIR"
