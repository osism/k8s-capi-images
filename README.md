# kubernetes-capi-images

Images intended for use with Kubernetes CAPI providers. More details on
https://image-builder.sigs.k8s.io/capi/capi.html.

The images are built with [diskimage-builder](https://docs.openstack.org/diskimage-builder/latest/)
(DIB). The custom `k8s-capi` element under `elements/` reuses the Ansible roles
of the upstream [Image Builder](https://github.com/kubernetes-sigs/image-builder/)
project, pinned to an immutable commit, so the resulting `ubuntu-XXXX-kube-vX.YY`
qcow2 images match what Image Builder produces. The element is documented in
[`elements/k8s-capi/README.rst`](elements/k8s-capi/README.rst).

The Ubuntu base image is fixed per Kubernetes series and is part of the
image name (`ubuntu-2604-kube-v1.37`). It is set in the override file of the
series (`ubuntu_release` is the Ubuntu codename, `ubuntu_version` the prefix
in the image name), see [Building images](#building-images).

| Kubernetes series | Ubuntu base      |
|-------------------|------------------|
| v1.37 and newer   | 26.04 (resolute) |
| v1.33.4 to v1.36  | 24.04 (noble)    |
| up to v1.33.3     | 22.04 (jammy)    |

When a Kubernetes series changes to EOL status, the corresponding builds
are deactivated here and only the last version of this series will remain
available as an image in the future.

The following images contain the latest [stable releases](https://kubernetes.io/releases/),
which are updated as required. This means that the image for version `1.36`
contains, for example, version `1.36.4`.

## Kubernetes versions

Every series is published under two names (see [Building images](#building-images)):

- `ubuntu-XXXX-kube-vX.YY.Z.qcow2` (versioned) is written once and never
  overwritten. Consumers that want a fixed version resolve it through the
  `last-X` pointer file (see [Determining Current Versions](#determining-current-versions)).
- `ubuntu-XXXX-kube-vX.YY.qcow2` (series) is overwritten on every publish run
  and always contains the latest build of the series, including fixes to the
  image itself that do not bump the Kubernetes version.

The `Version` column lists the Kubernetes version the series is currently built
with. It is kept in sync with the `overrides/` files by the upstream sync
workflow; the published versioned image follows with the next publish run.

| Series         | Version  | Series Image (latest build)                                                                                                                                                       | Pointer (fixed version)                                                                              | End of Life |
|----------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|-------------|
| v1.37          | v1.37.0  | [ubuntu-2604-kube-v1.37.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2604-kube-v1.37/ubuntu-2604-kube-v1.37.qcow2) ([CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2604-kube-v1.37/ubuntu-2604-kube-v1.37.qcow2.CHECKSUM))                                     | [last-1.37](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.37)                   | 2027-10-28  |
| v1.36          | v1.36.4  | [ubuntu-2404-kube-v1.36.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.qcow2) ([CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.qcow2.CHECKSUM))                                     | [last-1.36](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.36)                   | 2027-06-28  |
| v1.35          | v1.35.8  | [ubuntu-2404-kube-v1.35.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.qcow2) ([CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.qcow2.CHECKSUM))                                     | [last-1.35](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.35)                   | 2027-02-28  |
| v1.34          | v1.34.11 | [ubuntu-2404-kube-v1.34.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.qcow2) ([CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.qcow2.CHECKSUM))                                     | [last-1.34](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.34)                   | 2026-10-27  |

The versioned images live next to the series image, for example
`ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.4.qcow2` with its
`.CHECKSUM` file.

The first v1.37.0 build was still published on Ubuntu 24.04 as
`ubuntu-2404-kube-v1.37/ubuntu-2404-kube-v1.37.0.qcow2`. It stays available,
but it is no longer updated; `last-1.37` and all v1.37 builds from now on
point at the `ubuntu-2604-kube-v1.37` images.

### Archived

This section contains images for Kubernetes versions that have reached End of Life (EOL).
These images are no longer updated but remain available for download. Only the final
patch version of each EOL series is kept. All archived images were built with the
previous Packer based pipeline, before the migration to diskimage-builder.

| Series | Version  | Image URL                                                                                                                                                     | CHECKSUM URL                                                                                                                                                                    |
|--------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| v1.33  |          |                                                                                                                                                               |                                                                                                                                                                                 |
|        | v1.33.11 | [ubuntu-2404-kube-v1.33.11.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.33/ubuntu-2404-kube-v1.33.11.qcow2) | [ubuntu-2404-kube-v1.33.11.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.33/ubuntu-2404-kube-v1.33.11.qcow2.CHECKSUM) |
| v1.32  |          |                                                                                                                                                               |                                                                                                                                                                                 |
|        | v1.32.13 | [ubuntu-2204-kube-v1.32.13.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.32/ubuntu-2204-kube-v1.32.13.qcow2) | [ubuntu-2204-kube-v1.32.13.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.32/ubuntu-2204-kube-v1.32.13.qcow2.CHECKSUM) |
| v1.31  |          |                                                                                                                                                               |                                                                                                                                                                                 |
|        | v1.31.14 | [ubuntu-2204-kube-v1.31.14.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.31/ubuntu-2204-kube-v1.31.14.qcow2) | [ubuntu-2204-kube-v1.31.14.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.31/ubuntu-2204-kube-v1.31.14.qcow2.CHECKSUM) |
| v1.30  |          |                                                                                                                                                               |                                                                                                                                                                                 |
|        | v1.30.14 | [ubuntu-2204-kube-v1.30.14.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.30/ubuntu-2204-kube-v1.30.14.qcow2) | [ubuntu-2204-kube-v1.30.14.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.30/ubuntu-2204-kube-v1.30.14.qcow2.CHECKSUM) |
| v1.29  |          |                                                                                                                                                               |                                                                                                                                                                                 |
|        | v1.29.15 | [ubuntu-2204-kube-v1.29.15.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.29/ubuntu-2204-kube-v1.29.15.qcow2) | [ubuntu-2204-kube-v1.29.15.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.29/ubuntu-2204-kube-v1.29.15.qcow2.CHECKSUM) |
| v1.28  |          |                                                                                                                                                               |                                                                                                                                                                                 |
|        | v1.28.15 | [ubuntu-2204-kube-v1.28.15.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.28/ubuntu-2204-kube-v1.28.15.qcow2) | [ubuntu-2204-kube-v1.28.15.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.28/ubuntu-2204-kube-v1.28.15.qcow2.CHECKSUM) |
| v1.27  |          |                                                                                                                                                               |                                                                                                                                                                                 |
|        | v1.27.15 | [ubuntu-2204-kube-v1.27.15.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.27/ubuntu-2204-kube-v1.27.15.qcow2) | [ubuntu-2204-kube-v1.27.15.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.27/ubuntu-2204-kube-v1.27.15.qcow2.CHECKSUM) |

## Building images

Each Kubernetes series is described by an override file under `overrides/`,
for example `overrides/v1.36.json`. Besides the Kubernetes version it names
the Ubuntu base of the series: `ubuntu_release` is the codename diskimage-builder
downloads the cloud image for (`DIB_RELEASE`, e.g. `resolute`) and
`ubuntu_version` the prefix in the image name (e.g. `2604`). The Kubernetes
version fields are kept in sync with the Kubernetes package repository by the
[Sync with upstream](.github/workflows/sync-with-upstream.yml) workflow, which
runs `scripts/update-extra-vars.py` and opens a pull request; the Ubuntu
fields are only ever changed by hand.

To build an image locally on a Linux host with qemu/libguestfs:

```bash
# Build the latest v1.36 image (the qcow2 lands in output/)
./build-local.sh v1.36
```

In CI, Zuul builds every series on the `check` pipeline in
build-only mode (`upload_image: false`). On the `post` pipeline, the publish
jobs upload the image, its `.CHECKSUM`, and the `last-X` pointer to the object
storage. A job is triggered by changes to its override file, the element, the
playbooks, `requirements.txt` or `.zuul.yaml`.

Every publish run builds the image and uploads it under two names:

- `ubuntu-XXXX-kube-vX.YY.Z.qcow2` (versioned) is create-once: the job checks
  whether its `.CHECKSUM` already exists in the object storage and, if so,
  neither overwrites the image nor rewrites the `last-X` pointer.
- `ubuntu-XXXX-kube-vX.YY.qcow2` (series) is always overwritten together with
  its `.CHECKSUM`, so every merged change that touches the element, the
  playbooks or the override file ships as a fresh "latest" image of the series,
  even when the Kubernetes version stays the same.

## Determining Current Versions

For each Kubernetes series, a `last-X` file is published to the object storage during the
CI build process. These files contain the build date and the path to the latest image
for that series.

The files are available at:

```
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.34
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.35
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.36
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.37
```

Each file contains a single line in the format:

```
YYYY-MM-DD ubuntu-XXXX-kube-vX.XX/ubuntu-XXXX-kube-vX.XX.X.qcow2
```

For example, `last-1.36` might contain:

```
2026-09-16 ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.4.qcow2
```

This tells you that:
- The build was created on 2026-09-16
- The current version is v1.36.4
- The image uses Ubuntu 24.04 (`ubuntu-2404`); `last-1.37` names an
  `ubuntu-2604-kube-v1.37/...` image built on Ubuntu 26.04
- The full download URL is: `https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.4.qcow2`

To fetch the current version programmatically:

```bash
curl -s https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.36
```

If you do not need a fixed patch version, the unversioned series image always
contains the latest published build of that series (see
[Building images](#building-images)):

```
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.qcow2
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.qcow2.CHECKSUM
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
