#!/bin/bash
# Build a CAPI image locally with diskimage-builder, reproducing image-builder's
# ubuntu-2404-kube-vX.YY qcow2 via the k8s-capi element.
#
# Usage:
#   ./build-local.sh [VERSION]
#
# VERSION is the basename of an overrides/<VERSION>.json file, e.g.:
#   ./build-local.sh v1.33
#   ./build-local.sh v1.36-gardener
#
# Environment:
#   DIB_K8S_IMAGE_BUILDER_REF  image-builder commit SHA to run (default: the
#                              commit for tag v0.1.52)
#
# Requires Linux with root/sudo and qemu/libguestfs; it does not run on macOS.

set -euo pipefail

cd "$(dirname "$0")"

VERSION="${1:-v1.33}"
case "${VERSION}" in
    */*|*..*)
        echo "ERROR: invalid VERSION '${VERSION}'; it must be an overrides/ basename" >&2
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
export DIB_RELEASE=noble
export ELEMENTS_PATH=./elements

SEMVER="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['kubernetes_semver'])" "${OVERRIDE}")"
NAME="ubuntu-2404-kube-${SEMVER}"
case "${VERSION}" in
    *-gardener) NAME="${NAME}-gardener" ;;
esac

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

mkdir -p output
.venv/bin/disk-image-create -a amd64 -t qcow2 \
    -o "output/${NAME}" \
    ubuntu vm growroot openssh-server k8s-capi
