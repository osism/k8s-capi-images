# kubernetes-capi-images

Images intended for use with Kubernetes CAPI providers. More details on
https://image-builder.sigs.k8s.io/capi/capi.html.

When a Kubernetes series changes to EOL status, the corresponding builds
are deactivated here and only the last version of this series will remain
available as an image in the future.

The following images contain the latest [stable releases](https://kubernetes.io/releases/),
which are updated as required. This means that the image for version `1.27`
contains, for example, version `1.27.3`.

> [!IMPORTANT]
> **Migration in progress — Packer → diskimage-builder.**
>
> This repository is being migrated from the old Packer +
> [`kubernetes-sigs/image-builder`](https://github.com/kubernetes-sigs/image-builder/)
> pipeline (the **old world**) to a new
> [diskimage-builder](https://docs.openstack.org/diskimage-builder/latest/) based
> pipeline (the **new world**).
>
> **The new DIB pipeline is still being tested and is not finished yet.**
> Publishing from the DIB pipeline is **not armed** — the `post`/publish jobs and
> the upload secret in `.zuul.yaml` are intentionally commented out, and goss image
> validation is still being wired up
> ([#338](https://github.com/osism/k8s-capi-images/issues/338)).
>
> Until the cutover, **all images available at the URLs in this document are still
> built with the old Packer pipeline.** Once the DIB pipeline is armed, the same
> URLs and naming will serve DIB-built images, so no consumer-side change will be
> required.

## New world: diskimage-builder (DIB)

The images are built with [diskimage-builder](https://docs.openstack.org/diskimage-builder/latest/),
driven by the custom `k8s-capi` element under `elements/`. The element
reuses the upstream [Image Builder](https://github.com/kubernetes-sigs/image-builder/)
Ansible roles, pinned to an immutable commit, so the resulting
`ubuntu-2404-kube-vX.YY` qcow2 images match what Image Builder produces.

### Building images

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

In CI, Zuul builds every series and variant on the `check` pipeline in
build-only mode (`upload_image: false`) — nothing is published yet. The
`post`/publish pipeline that uploads the qcow2 image, its `.CHECKSUM`, and the
`last-X` pointer to the object storage is prepared but still commented out in
`.zuul.yaml`; it will be armed once a maintainer regenerates the upload secret
(see the note at the top of `.zuul.yaml`). The published layout and naming stay
unchanged, so the URLs below and `scripts/generate-k8s-image-urls.sh` keep
resolving after the cutover. Gardener variants are published under the parallel
`…-gardener` names.

### Kubernetes versions (new world / DIB)

> [!NOTE]
> These series are built by the DIB pipeline today, but **no DIB image has been
> published yet** because publishing is not armed. The table below reflects the
> build targets currently under test. After the cutover the images will be served
> at the same URLs as the old-world table further down.

| Series | Target Version | Variants          | End of Life | Status                         |
|--------|----------------|-------------------|-------------|--------------------------------|
| v1.36  | v1.36.2        | default, gardener | 2027-06-28  | under test — not yet published |
| v1.35  | v1.35.6        | default, gardener | 2027-02-28  | under test — not yet published |
| v1.34  | v1.34.9        | default, gardener | 2026-10-27  | under test — not yet published |
| v1.33  | v1.33.13       | default, gardener | 2026-06-28  | under test — not yet published |

## Old world: Packer / image-builder

The previous pipeline built the images with Packer and the upstream
`kubernetes-sigs/image-builder` project. **All images currently published at the
URLs below were built with this old-world pipeline** and remain the authoritative
artifacts until the DIB cutover is complete.

### Kubernetes versions (old world / Packer) — currently published

| Series | Current Version | Image URL                                                                                                                                                | End of Life |
|--------|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| v1.36  | v1.36.1         | [ubuntu-2404-kube-v1.36.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.qcow2)  | 2027-06-28  |
| v1.35  | v1.35.5         | [ubuntu-2404-kube-v1.35.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.qcow2)  | 2027-02-28  |
| v1.34  | v1.34.8         | [ubuntu-2404-kube-v1.34.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.qcow2)  | 2026-10-27  |
| v1.33  | v1.33.12        | [ubuntu-2404-kube-v1.33.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.33/ubuntu-2404-kube-v1.33.qcow2)  | 2026-06-28  |

### Archived

This section contains images for Kubernetes versions that have reached End of Life (EOL).
These images are no longer updated but remain available for download. Only the final
patch version of each EOL series is kept. All archived images were built with the
old-world Packer pipeline.

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
