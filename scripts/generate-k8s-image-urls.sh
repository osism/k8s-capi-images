#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images"
MIN_MINOR=32
MINOR_VERSION="${1:-1.35}"

# Validate: minimum supported version is 1.32
MINOR_NUM="${MINOR_VERSION#1.}"
if [[ "${MINOR_NUM}" -lt "${MIN_MINOR}" ]]; then
    echo "ERROR: Minimum supported version is 1.${MIN_MINOR}, got ${MINOR_VERSION}" >&2
    exit 1
fi

LAST_FILE="last-${MINOR_VERSION}"

echo "Fetching ${BASE_URL}/${LAST_FILE} ..."
CONTENT=$(curl -sf "${BASE_URL}/${LAST_FILE}") || {
    echo "ERROR: Could not fetch ${BASE_URL}/${LAST_FILE}" >&2
    exit 1
}

echo "Content: ${CONTENT}"
echo ""

# Extract the image filename (second field after date)
IMAGE_PATH=$(echo "${CONTENT}" | awk '{print $2}')

if [[ -z "${IMAGE_PATH}" ]]; then
    echo "ERROR: Could not parse image path from content" >&2
    exit 1
fi

# Extract the patch version from the filename
# e.g. ubuntu-2404-kube-v1.33.7.qcow2 -> 7
PATCH_VERSION=$(echo "${IMAGE_PATH}" | sed -n "s/.*v${MINOR_VERSION}\.\([0-9][0-9]*\).*/\1/p")

if [[ -z "${PATCH_VERSION}" ]]; then
    echo "ERROR: Could not extract patch version from '${IMAGE_PATH}'" >&2
    exit 1
fi

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
