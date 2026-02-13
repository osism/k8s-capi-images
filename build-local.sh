#!/bin/bash

# Environment variables
export IMAGE_IDENTIFIER="1.33-gardener"
export DISTRO_VERSION="2404"
export PACKER_VAR_FILES="../../../extra_vars_133_gardener.json"

# Prepare script
# git clone https://github.com/kubernetes-sigs/image-builder
# cd image-builder/images/capi
# export PATH=$PWD/.bin:$HOME/.local/bin:$PATH
# make deps-qemu
# make build-qemu-ubuntu-$DISTRO_VERSION

# Prepare push script
pushd image-builder/images/capi/output/ubuntu-$DISTRO_VERSION-kube-v$IMAGE_IDENTIFIER
find . -type f -execdir bash -c 'x={}; cp $x ${x%.*}.qcow2; mv $x $x.qcow2' \;
find . -name '*.qcow2' -execdir bash -c 'x={}; sha256sum $(basename $x) > $x.CHECKSUM' \;
FIRST_QCOW2=$(find . -name '*.qcow2' -print -quit 2>/dev/null)
echo "$(date +%Y-%m-%d) ubuntu-$DISTRO_VERSION-kube-v$IMAGE_IDENTIFIER/$(basename "$FIRST_QCOW2")" > "last-$IMAGE_IDENTIFIER"
ls -lah
popd
mv image-builder/images/capi/output/ubuntu-$DISTRO_VERSION-kube-v$IMAGE_IDENTIFIER/last-$IMAGE_IDENTIFIER .
cat last-$IMAGE_IDENTIFIER
