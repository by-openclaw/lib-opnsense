#!/usr/bin/env bash
# =============================================================================
# firmware-upgrade-check.sh — full validation after OPNsense firmware upgrade
# =============================================================================
# Copyright (c) BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# https://github.com/by-openclaw/lib-opnsense
# =============================================================================
#
# Run after upgrading OPNsense firmware to detect:
#   1. New/removed/changed API endpoints
#   2. Enum values that changed (new options, removed options)
#   3. Field types that changed (UpdateOnlyTextField, etc.)
#   4. Pylib validators that need updating
#
# Usage:
#   ./scripts/firmware-upgrade-check.sh
#
# Prerequisites:
#   - OPN_HOST, OPN_KEY, OPN_SECRET env vars (or .env file)
#   - Python venv with lib-opnsense installed: source .venv/bin/activate
#
# Output:
#   1. Fresh probe data in docs/api/data/{new_version}/
#   2. Diff between old and new probe data
#   3. Validator verification report
#   4. Summary of what needs updating
#
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PROBE_BASE="${REPO_ROOT}/docs/api/data"

cd "$REPO_ROOT"

# Load .env if present
if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

echo "============================================"
echo " OPNsense Firmware Upgrade Check"
echo "============================================"
echo ""

# --- Step 1: Get current version (before probe) ---
OLD_VERSION=$(ls -1 "$PROBE_BASE" | grep -v latest | grep -v README | sort -V | tail -1 || echo "none")
echo "Previous probe version: ${OLD_VERSION}"

# --- Step 2: Run probe to capture new schemas ---
echo ""
echo "Step 1/3: Probing API schemas..."
"${SCRIPT_DIR}/probe-api-schemas.sh"

# --- Step 3: Get new version ---
NEW_VERSION=$(ls -1 "$PROBE_BASE" | grep -v latest | grep -v README | sort -V | tail -1)
echo ""
echo "New probe version: ${NEW_VERSION}"

# --- Step 4: Diff between old and new ---
if [[ "$OLD_VERSION" != "none" && "$OLD_VERSION" != "$NEW_VERSION" ]]; then
    echo ""
    echo "Step 2/3: Comparing schemas ${OLD_VERSION} → ${NEW_VERSION}..."
    echo ""

    # Compare schema files
    OLD_DIR="${PROBE_BASE}/${OLD_VERSION}"
    NEW_DIR="${PROBE_BASE}/${NEW_VERSION}"

    # New endpoints
    NEW_ENDPOINTS=$(comm -13 \
        <(ls "$OLD_DIR"/*__schema.json 2>/dev/null | xargs -I{} basename {} | sort) \
        <(ls "$NEW_DIR"/*__schema.json 2>/dev/null | xargs -I{} basename {} | sort) \
    )
    if [[ -n "$NEW_ENDPOINTS" ]]; then
        echo "NEW ENDPOINTS (added in ${NEW_VERSION}):"
        echo "$NEW_ENDPOINTS" | sed 's/__schema.json//' | sed 's/^/  + /'
        echo ""
    fi

    # Removed endpoints
    REMOVED_ENDPOINTS=$(comm -23 \
        <(ls "$OLD_DIR"/*__schema.json 2>/dev/null | xargs -I{} basename {} | sort) \
        <(ls "$NEW_DIR"/*__schema.json 2>/dev/null | xargs -I{} basename {} | sort) \
    )
    if [[ -n "$REMOVED_ENDPOINTS" ]]; then
        echo "REMOVED ENDPOINTS (gone in ${NEW_VERSION}):"
        echo "$REMOVED_ENDPOINTS" | sed 's/__schema.json//' | sed 's/^/  - /'
        echo ""
    fi

    # Changed schemas (diff JSON structure)
    CHANGED=0
    for new_file in "$NEW_DIR"/*__schema.json; do
        base=$(basename "$new_file")
        old_file="${OLD_DIR}/${base}"
        if [[ -f "$old_file" ]]; then
            if ! diff -q "$old_file" "$new_file" > /dev/null 2>&1; then
                if [[ $CHANGED -eq 0 ]]; then
                    echo "CHANGED SCHEMAS:"
                fi
                echo "  ~ ${base%.json}"
                CHANGED=$((CHANGED + 1))
            fi
        fi
    done
    if [[ $CHANGED -gt 0 ]]; then
        echo "  ($CHANGED schemas changed — review with: diff docs/api/data/${OLD_VERSION}/<file> docs/api/data/${NEW_VERSION}/<file>)"
        echo ""
    fi
else
    echo ""
    echo "Step 2/3: No previous version to compare (first probe or same version)."
fi

# --- Step 5: Verify pylib validators ---
echo ""
echo "Step 3/3: Verifying pylib validators against ${NEW_VERSION} schemas..."
echo ""

PYTHONPATH="${REPO_ROOT}/src" python3 "${SCRIPT_DIR}/verify-validators.py" \
    --schema-dir "${PROBE_BASE}/${NEW_VERSION}" 2>&1

VERIFY_EXIT=$?

echo ""
echo "============================================"
if [[ $VERIFY_EXIT -eq 0 ]]; then
    echo " RESULT: ALL VALIDATORS MATCH"
else
    echo " RESULT: ENUM MISMATCHES FOUND — fix pylib validators"
fi
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Fix any enum mismatches in src/opnsense/managers/"
echo "  2. Run unit tests:        .venv/bin/python -m pytest tests/unit/ -q"
echo "  3. Run integration tests: .venv/bin/python -m pytest tests/integration/ -q"
echo "  4. Update docs/api-coverage.md if new endpoints appeared"
echo "  5. Commit: feat(api): update validators for OPNsense ${NEW_VERSION}"
