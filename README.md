# kubernetes-capi-images

Images intended for use with Kubernetes CAPI providers. More details on
https://image-builder.sigs.k8s.io/capi/capi.html.

The images are built with [diskimage-builder](https://docs.openstack.org/diskimage-builder/latest/),
driven by the custom `k8s-capi` element under `elements/`. The element
reuses the upstream [Image Builder](https://github.com/kubernetes-sigs/image-builder/)
Ansible roles, pinned to an immutable commit, so the resulting
`ubuntu-2404-kube-vX.YY` qcow2 images match what Image Builder produces.

When a Kubernetes series changes to EOL status, the corresponding builds
are deactivated here and only the last version of this series will remain
available as an image in the future.

The following images contain the latest [stable releases](https://kubernetes.io/releases/),
which are updated as required. This means that the image for version `1.27`
contains, for example, version `1.27.3`.

## Building images

Each Kubernetes series and its gardener variant is described by an override
file under `overrides/`, for example `overrides/v1.33.json` or
`overrides/v1.33-gardener.json`.

To build an image locally on a Linux host with qemu/libguestfs:

```bash
# Build the latest v1.33 image (the qcow2 lands in output/)
./build-local.sh v1.33

# Build the gardener variant
./build-local.sh v1.33-gardener
```

In CI, Zuul builds every series and variant on the `check` pipeline and, on
the `post` pipeline after a merge to `main`, publishes the qcow2 image, its
`.CHECKSUM`, and the `last-X` pointer to the object storage. Gardener
variants are published under the parallel `…-gardener` names. The published
layout and naming are unchanged, so the URLs below and
`scripts/generate-k8s-image-urls.sh` keep resolving.

## Validating images

After building, CI asserts that each image actually contains the expected
Kubernetes binaries, containerd, CNI, packages, services, kernel parameters,
and files by running the upstream [Image Builder](https://github.com/kubernetes-sigs/image-builder/)
[goss](https://github.com/goss-org/goss) spec — the same spec upstream uses —
inside the booted image. This is `playbooks/validate.yml`, run after
`playbooks/build.yml` on every `check` job.

Service-running and live sysctl checks need a booted system, so the image is
booted under QEMU and `goss validate` runs inside the VM. To keep the published
qcow2 bit-identical, the VM boots a disposable copy-on-write overlay whose
backing file is the built image; all guest writes land in the overlay, which is
deleted afterwards. The build's `.CHECKSUM` is re-verified at the end to prove
the artifact was untouched.

```bash
# How the overlay is created (the published image is the read-only backing file)
qemu-img create -f qcow2 -b output/<image>.qcow2 -F qcow2 validate-overlay.qcow2
```

The image boots under QEMU with KVM acceleration. The goss spec is re-cloned from
image-builder at the same `DIB_K8S_IMAGE_BUILDER_REF` the build uses (it is not
vendored), and the `goss` binary is pinned to `0.3.23` and verified by checksum,
matching how the build already pins and hashes its inputs.

A failed assertion fails the build, so an image that diverges from what upstream
Image Builder produces is never published. The goss JSON report and the VM
console log are saved under `zuul-output/logs/`.

## Kubernetes Versions

| Series | Current Version | Image URL                                                                                                                                                | End of Life |
|--------|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| v1.36  | v1.36.2         | [ubuntu-2404-kube-v1.36.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.qcow2)  | 2027-06-28  |
| v1.35  | v1.35.6         | [ubuntu-2404-kube-v1.35.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.qcow2)  | 2027-02-28  |
| v1.34  | v1.34.9         | [ubuntu-2404-kube-v1.34.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.qcow2)  | 2026-10-27  |
| v1.33  | v1.33.13        | [ubuntu-2404-kube-v1.33.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.33/ubuntu-2404-kube-v1.33.qcow2)  | 2026-06-28  |

## Determining Current Versions

For each Kubernetes series, a `last-X` file is published to the object storage during the
CI build process. These files contain the build date and the path to the latest image
for that series.

The files are available at:

```
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.33
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.34
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.35
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.36
```

Each file contains a single line in the format:

```
YYYY-MM-DD ubuntu-XXXX-kube-vX.XX/ubuntu-XXXX-kube-vX.XX.X.qcow2
```

For example, `last-1.33` might contain:

```
2025-11-15 ubuntu-2404-kube-v1.33/ubuntu-2404-kube-v1.33.9.qcow2
```

This tells you that:
- The build was created on 2025-11-15
- The current version is v1.33.9
- The image uses Ubuntu 24.04
- The full download URL is: `https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.33/ubuntu-2404-kube-v1.33.9.qcow2`

To fetch the current version programmatically:

```bash
curl -s https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.33
```

## Generating Download URLs for All Patch Versions

The script `scripts/generate-k8s-image-urls.sh` generates download URLs for all
patch versions of a given Kubernetes minor version. It fetches the latest patch
version from the `last-X` file and outputs URLs for every patch from `.0` up to
the latest.

```bash
# Generate URLs for v1.35 (default)
bash scripts/generate-k8s-image-urls.sh

# Generate URLs for a specific minor version
bash scripts/generate-k8s-image-urls.sh 1.33
```

The minimum supported version is `1.33`.

Example output:

```
Fetching latest patch version for 1.35 ...
Latest version: v1.35.0

=========================================
 Download URLs (v1.35.0 - v1.35.0)
=========================================

https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.0.qcow2

Total: 1 images
```

## Verifying Image Checksums

The script also supports a `--verify` mode that downloads the `.CHECKSUM` file from the
server and verifies a local image against it. If the image is not present locally, it will
be downloaded automatically.

```bash
# Verify the latest patch version of 1.35 (downloads the image if not present)
bash scripts/generate-k8s-image-urls.sh --verify 1.35

# Verify an exact version
bash scripts/generate-k8s-image-urls.sh --verify 1.35.1

# Verify and delete the downloaded image afterwards
bash scripts/generate-k8s-image-urls.sh --verify 1.35 --cleanup
```

The `--cleanup` flag only removes the image if it was downloaded during the verification.
Files that already existed locally are never deleted.

The script exits with code `0` on success and `1` on checksum mismatch.

## Archived

This section contains images for Kubernetes versions that have reached End of Life (EOL).
These images are no longer updated but remain available for download. Only the final
patch version of each EOL series is kept.

| Series | Version  | Image URL                                                                                                                                                 | CHECKSUM URL                                                                                                                                                              |
|--------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| v1.32  |          |                                                                                                                                                           |                                                                                                                                                                           |
|        | v1.32.13 | [ubuntu-2204-kube-v1.32.13.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.32/ubuntu-2204-kube-v1.32.13.qcow2) | [ubuntu-2204-kube-v1.32.13.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.32/ubuntu-2204-kube-v1.32.13.qcow2.CHECKSUM) |
| v1.31  |          |                                                                                                                                                                                                               |                                                                                                                                                                                                                               |
|        | v1.31.14 | [ubuntu-2204-kube-v1.31.14.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.31/ubuntu-2204-kube-v1.31.14.qcow2)   | [ubuntu-2204-kube-v1.31.14.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.31/ubuntu-2204-kube-v1.31.14.qcow2.CHECKSUM) |
| v1.30  |          |                                                                                                                                                           |                                                                                                                                                                           |
|        | v1.30.14 | [ubuntu-2204-kube-v1.30.14.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.30/ubuntu-2204-kube-v1.30.14.qcow2) | [ubuntu-2204-kube-v1.30.14.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.30/ubuntu-2204-kube-v1.30.14.qcow2.CHECKSUM) |
| v1.29  |          |                                                                                                                                                           |                                                                                                                                                                           |
|        | v1.29.15 | [ubuntu-2204-kube-v1.29.15.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.29/ubuntu-2204-kube-v1.29.15.qcow2) | [ubuntu-2204-kube-v1.29.15.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.29/ubuntu-2204-kube-v1.29.15.qcow2.CHECKSUM) |
| v1.28  |          |                                                                                                                                                           |                                                                                                                                                                           |
|        | v1.28.15 | [ubuntu-2204-kube-v1.28.15.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.28/ubuntu-2204-kube-v1.28.15.qcow2) | [ubuntu-2204-kube-v1.28.15.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.28/ubuntu-2204-kube-v1.28.15.qcow2.CHECKSUM) |
| v1.27  |          |                                                                                                                                                           |                                                                                                                                                                           |
|        | v1.27.15 | [ubuntu-2204-kube-v1.27.15.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.27/ubuntu-2204-kube-v1.27.15.qcow2) | [ubuntu-2204-kube-v1.27.15.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.27/ubuntu-2204-kube-v1.27.15.qcow2.CHECKSUM) |

