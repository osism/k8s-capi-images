#!/bin/bash
# Build a CAPI image locally with diskimage-builder via the k8s-capi element,
# named <os>-<os_version>-kube-vX.YY.Z like image-builder's
# ubuntu-XXXX-kube-vX.YY qcow2. The base (<os>_release/<os>_version) comes from
# the override file of the series.
#
# Usage:
#   ./build-local.sh [VERSION [OS]]
#
# VERSION is the basename of an overrides/<VERSION>.json file and OS is ubuntu
# (default) or debian, e.g.:
#   ./build-local.sh v1.33
#   ./build-local.sh v1.36
#   ./build-local.sh v1.37 debian
#
# Environment:
#   DIB_K8S_IMAGE_BUILDER_REF  image-builder commit SHA to run (default: the
#                              commit for tag v0.1.55)
#
# Requires Linux with root/sudo and qemu/libguestfs; it does not run on macOS.
# A debian build also needs debootstrap and debian-archive-keyring on the host:
# debootstrap verifies the Debian archive signature with that keyring and, as
# --force-check-gpg is set, aborts when it is missing.

set -euo pipefail

cd "$(dirname "$0")"

VERSION="${1:-v1.33}"
case "${VERSION}" in
    */*|*..*)
        echo "ERROR: invalid VERSION '${VERSION}'; it must be an overrides/ basename" >&2
        exit 1
        ;;
esac
IMAGE_OS="${2:-ubuntu}"
case "${IMAGE_OS}" in
    ubuntu|debian) ;;
    *)
        echo "ERROR: invalid OS '${IMAGE_OS}'; it must be ubuntu or debian" >&2
        exit 1
        ;;
esac
OVERRIDE="overrides/${VERSION}.json"
if [ ! -f "${OVERRIDE}" ]; then
    echo "ERROR: no override file ${OVERRIDE}" >&2
    exit 1
fi

export DIB_K8S_CAPI_OVERRIDE
DIB_K8S_CAPI_OVERRIDE="$(readlink -f "${OVERRIDE}")"
export ELEMENTS_PATH=./elements

# kubernetes_semver names the image, <os>_release (codename, e.g. resolute or
# trixie) selects the DIB base and <os>_version (e.g. 2604 or 13) the image
# prefix. A series without both keys has no image of that OS.
OVERRIDE_FIELDS="$(python3 - "${OVERRIDE}" "${IMAGE_OS}" "${VERSION}" <<'PYEOF'
import json
import sys

path, image_os, version = sys.argv[1:]
data = json.load(open(path))
release = data.get(f"{image_os}_release")
os_version = data.get(f"{image_os}_version")
if not release or not os_version:
    sys.exit(
        f"ERROR: {path} has no {image_os}_release/{image_os}_version; "
        f"the {version} series has no {image_os} image"
    )
print(data["kubernetes_semver"], release, os_version)
PYEOF
)"
read -r SEMVER OS_RELEASE OS_VERSION <<< "${OVERRIDE_FIELDS}"
export DIB_RELEASE="${OS_RELEASE}"
# debootstrap builds the Debian root filesystem on this host. Without
# debian-archive-keyring it only warns and continues unverified;
# --force-check-gpg makes it abort instead.
if [ "${IMAGE_OS}" = debian ]; then
    export DIB_DEBOOTSTRAP_EXTRA_ARGS=--force-check-gpg
fi
NAME="${IMAGE_OS}-${OS_VERSION}-kube-${SEMVER}"

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

mkdir -p output
.venv/bin/disk-image-create -a amd64 -t qcow2 \
    -o "output/${NAME}" \
    "${IMAGE_OS}" vm growroot openssh-server k8s-capi
