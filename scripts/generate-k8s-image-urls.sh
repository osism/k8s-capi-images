#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images"
MIN_MINOR=32

# Portable SHA256: use sha256sum (Linux) or shasum (macOS)
sha256_hash() {
    if command -v sha256sum &>/dev/null; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum &>/dev/null; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        echo "ERROR: Neither sha256sum nor shasum found" >&2
        return 1
    fi
}

# Determine the Ubuntu version for a given minor.patch combination
# - 1.32.x:       always 2204
# - 1.33.0-1.33.3: 2204, starting with 1.33.4: 2404
# - 1.34+:        always 2404
get_ubuntu_version() {
    local minor="$1"
    local patch="$2"

    case "${minor}" in
        32)
            echo "2204"
            ;;
        33)
            if [[ "${patch}" -lt 4 ]]; then
                echo "2204"
            else
                echo "2404"
            fi
            ;;
        *)
            echo "2404"
            ;;
    esac
}

# Resolve a minor-only version (e.g. 1.35) to the latest patch version
# by fetching the last-file from the server
resolve_latest_patch() {
    local minor_version="$1"
    local last_file="last-${minor_version}"

    local content
    content=$(curl -sf "${BASE_URL}/${last_file}") || {
        echo "ERROR: Could not fetch ${BASE_URL}/${last_file}" >&2
        return 1
    }

    local image_path
    image_path=$(echo "${content}" | awk '{print $2}')

    if [[ -z "${image_path}" ]]; then
        echo "ERROR: Could not parse image path from content" >&2
        return 1
    fi

    local patch
    patch=$(echo "${image_path}" | sed -n "s/.*v${minor_version}\.\([0-9][0-9]*\).*/\1/p")

    if [[ -z "${patch}" ]]; then
        echo "ERROR: Could not extract patch version from '${image_path}'" >&2
        return 1
    fi

    echo "${patch}"
}

# --verify mode: download checksum from server and verify a local image
if [[ "${1:-}" == "--verify" ]]; then
    if [[ -z "${2:-}" ]]; then
        echo "Usage: $0 --verify <version> [--cleanup]" >&2
        echo "  version: 1.35 (latest patch) or 1.35.1 (exact)" >&2
        exit 1
    fi

    VERSION_ARG="$2"
    CLEANUP=false
    if [[ "${3:-}" == "--cleanup" ]]; then
        CLEANUP=true
    fi

    # Parse version: minor-only (1.35) vs full (1.35.1)
    if [[ "${VERSION_ARG}" =~ ^1\.([0-9]+)$ ]]; then
        MINOR_NUM="${BASH_REMATCH[1]}"
        MINOR_VERSION="1.${MINOR_NUM}"

        if [[ "${MINOR_NUM}" -lt "${MIN_MINOR}" ]]; then
            echo "ERROR: Minimum supported version is 1.${MIN_MINOR}, got ${MINOR_VERSION}" >&2
            exit 1
        fi

        echo "Resolving latest patch version for ${MINOR_VERSION} ..."
        PATCH_VERSION=$(resolve_latest_patch "${MINOR_VERSION}")
        FULL_VERSION="${MINOR_VERSION}.${PATCH_VERSION}"
        echo "Resolved to v${FULL_VERSION}"
    elif [[ "${VERSION_ARG}" =~ ^1\.([0-9]+)\.([0-9]+)$ ]]; then
        MINOR_NUM="${BASH_REMATCH[1]}"
        PATCH_VERSION="${BASH_REMATCH[2]}"
        MINOR_VERSION="1.${MINOR_NUM}"
        FULL_VERSION="${MINOR_VERSION}.${PATCH_VERSION}"

        if [[ "${MINOR_NUM}" -lt "${MIN_MINOR}" ]]; then
            echo "ERROR: Minimum supported version is 1.${MIN_MINOR}, got ${MINOR_VERSION}" >&2
            exit 1
        fi
    else
        echo "ERROR: Invalid version format '${VERSION_ARG}'. Expected 1.X or 1.X.Y" >&2
        exit 1
    fi

    UBUNTU=$(get_ubuntu_version "${MINOR_NUM}" "${PATCH_VERSION}")
    DIR="ubuntu-${UBUNTU}-kube-v${MINOR_VERSION}"
    FILE="ubuntu-${UBUNTU}-kube-v${FULL_VERSION}.qcow2"
    IMAGE_URL="${BASE_URL}/${DIR}/${FILE}"
    CHECKSUM_URL="${IMAGE_URL}.CHECKSUM"

    echo "Image:    ${IMAGE_URL}"
    echo "Checksum: ${CHECKSUM_URL}"
    echo ""

    # Fetch checksum from server
    echo "Fetching checksum from server ..."
    SERVER_CHECKSUM_LINE=$(curl -sf "${CHECKSUM_URL}") || {
        echo "ERROR: Could not fetch checksum from ${CHECKSUM_URL}" >&2
        exit 1
    }
    SERVER_CHECKSUM=$(echo "${SERVER_CHECKSUM_LINE}" | awk '{print $1}')

    if [[ -z "${SERVER_CHECKSUM}" ]]; then
        echo "ERROR: Could not parse checksum from server response" >&2
        exit 1
    fi
    echo "Server checksum: ${SERVER_CHECKSUM}"

    # Show Last-Modified timestamps from the server
    CHECKSUM_LAST_MODIFIED=$(curl -sfI "${CHECKSUM_URL}" | grep -i '^Last-Modified:' | sed 's/^[^:]*: //')
    IMAGE_LAST_MODIFIED=$(curl -sfI "${IMAGE_URL}" | grep -i '^Last-Modified:' | sed 's/^[^:]*: //')
    if [[ -n "${CHECKSUM_LAST_MODIFIED}" ]]; then
        echo "Checksum last modified: ${CHECKSUM_LAST_MODIFIED}"
    fi
    if [[ -n "${IMAGE_LAST_MODIFIED}" ]]; then
        echo "Image last modified:    ${IMAGE_LAST_MODIFIED}"
    fi

    # Ensure local file exists
    DOWNLOADED=false
    if [[ -f "${FILE}" ]]; then
        echo "Local file found: ${FILE}"
    else
        echo "Local file not found, downloading ${FILE} ..."
        curl -f --progress-bar -o "${FILE}" "${IMAGE_URL}" || {
            echo "ERROR: Could not download ${IMAGE_URL}" >&2
            exit 1
        }
        DOWNLOADED=true
    fi

    # Verify checksum
    echo ""
    echo "Calculating local checksum ..."
    LOCAL_CHECKSUM=$(sha256_hash "${FILE}")
    echo "Local checksum:  ${LOCAL_CHECKSUM}"

    if [[ "${LOCAL_CHECKSUM}" == "${SERVER_CHECKSUM}" ]]; then
        echo ""
        echo "OK: Checksum verified successfully for ${FILE}"
        RESULT=0
    else
        echo ""
        echo "FAILED: Checksum mismatch for ${FILE}" >&2
        echo "  expected: ${SERVER_CHECKSUM}" >&2
        echo "  got:      ${LOCAL_CHECKSUM}" >&2
        RESULT=1
    fi

    # Cleanup if requested (only delete files we downloaded)
    if [[ "${CLEANUP}" == true && "${DOWNLOADED}" == true ]]; then
        echo "Cleaning up downloaded file: ${FILE}"
        rm -f "${FILE}"
    fi

    exit "${RESULT}"
fi

# Default mode: generate download URLs
MINOR_VERSION="${1:-1.35}"

# Validate: minimum supported version is 1.32
MINOR_NUM="${MINOR_VERSION#1.}"
if [[ "${MINOR_NUM}" -lt "${MIN_MINOR}" ]]; then
    echo "ERROR: Minimum supported version is 1.${MIN_MINOR}, got ${MINOR_VERSION}" >&2
    exit 1
fi

echo "Fetching latest patch version for ${MINOR_VERSION} ..."
PATCH_VERSION=$(resolve_latest_patch "${MINOR_VERSION}")

echo "Latest version: v${MINOR_VERSION}.${PATCH_VERSION}"
echo ""
echo "========================================="
echo " Download URLs (v${MINOR_VERSION}.0 - v${MINOR_VERSION}.${PATCH_VERSION})"
echo "========================================="
echo ""

for patch in $(seq 0 "${PATCH_VERSION}"); do
    UBUNTU=$(get_ubuntu_version "${MINOR_NUM}" "${patch}")
    DIR="ubuntu-${UBUNTU}-kube-v${MINOR_VERSION}"
    FILE="ubuntu-${UBUNTU}-kube-v${MINOR_VERSION}.${patch}.qcow2"
    echo "${BASE_URL}/${DIR}/${FILE}"
done

echo ""
echo "Total: $((PATCH_VERSION + 1)) images"
