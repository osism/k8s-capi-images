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
> **The `v1.36` images were the first images published from the DIB pipeline.**
> Publishing is now armed for every series that is still built here — `v1.34`,
> `v1.35`, `v1.36` and `v1.37`, each with its gardener variant. `v1.37` is the
> first series that never had an old-world Packer build. goss image validation is
> still being wired up
> ([#338](https://github.com/osism/k8s-capi-images/issues/338)).
>
> DIB images are always published under their full patch version
> (`ubuntu-2404-kube-v1.36.2.qcow2`). The old pipeline additionally maintained an
> unversioned `ubuntu-2404-kube-v1.36.qcow2` pointing at the latest build of the
> series; the DIB pipeline does **not** write that file. Consumers of a series
> should resolve the current image through the `last-X` file (see
> [Determining Current Versions](#determining-current-versions)) rather than
> through the unversioned name.

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
build-only mode (`upload_image: false`). On the `post` pipeline, the publish jobs
upload the qcow2 image, its `.CHECKSUM`, and the `last-X` pointer to the object
storage. These jobs are armed for every series and variant in `overrides/` that
has build jobs, currently `v1.34` through `v1.37` in both the default and the
gardener variant.

Publishing is create-once per image version: a publish job checks whether the
`.CHECKSUM` of the image it would upload already exists in the object storage and
then skips build and upload. This keeps the `.zuul.yaml` file matchers idempotent
— touching the pipeline config re-triggers the jobs without rebuilding or
overwriting images that are already published. Gardener variants are published
under the parallel `…-gardener` names.

### Kubernetes versions (new world / DIB)

> [!NOTE]
> All series below are built by the DIB pipeline. `v1.34`, `v1.35` and `v1.36`
> are published from it; `v1.37` is armed but has not had a `post` run yet. The
> unversioned Packer images listed further down are frozen and no longer updated.

#### Published from the DIB pipeline

| Series         | Version  | Image URL                                                                                                                                                                                | CHECKSUM URL                                                                                                                                                                                               | End of Life |
|----------------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| v1.36          | v1.36.4  | [ubuntu-2404-kube-v1.36.4.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.4.qcow2)                              | [ubuntu-2404-kube-v1.36.4.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.4.qcow2.CHECKSUM)                              | 2027-06-28  |
| v1.36-gardener | v1.36.4  | [ubuntu-2404-kube-v1.36.4-gardener.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36-gardener/ubuntu-2404-kube-v1.36.4-gardener.qcow2)   | [ubuntu-2404-kube-v1.36.4-gardener.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36-gardener/ubuntu-2404-kube-v1.36.4-gardener.qcow2.CHECKSUM)   | 2027-06-28  |
| v1.35          | v1.35.8  | [ubuntu-2404-kube-v1.35.8.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.8.qcow2)                              | [ubuntu-2404-kube-v1.35.8.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.8.qcow2.CHECKSUM)                              | 2027-02-28  |
| v1.35-gardener | v1.35.8  | [ubuntu-2404-kube-v1.35.8-gardener.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35-gardener/ubuntu-2404-kube-v1.35.8-gardener.qcow2)   | [ubuntu-2404-kube-v1.35.8-gardener.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35-gardener/ubuntu-2404-kube-v1.35.8-gardener.qcow2.CHECKSUM)   | 2027-02-28  |
| v1.34          | v1.34.11 | [ubuntu-2404-kube-v1.34.11.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.11.qcow2)                            | [ubuntu-2404-kube-v1.34.11.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.11.qcow2.CHECKSUM)                            | 2026-10-27  |
| v1.34-gardener | v1.34.11 | [ubuntu-2404-kube-v1.34.11-gardener.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34-gardener/ubuntu-2404-kube-v1.34.11-gardener.qcow2) | [ubuntu-2404-kube-v1.34.11-gardener.qcow2.CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34-gardener/ubuntu-2404-kube-v1.34.11-gardener.qcow2.CHECKSUM) | 2026-10-27  |

The current image of each series is also resolvable through its pointer file:
[last-1.34](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.34),
[last-1.34-gardener](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.34-gardener),
[last-1.35](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.35),
[last-1.35-gardener](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.35-gardener),
[last-1.36](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.36)
and
[last-1.36-gardener](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.36-gardener).

#### Built, not yet published

| Series | Target Version | Variants          | End of Life | Status                                  |
|--------|----------------|-------------------|-------------|-----------------------------------------|
| v1.37  | v1.37.0        | default, gardener | 2027-10-28  | publish armed — awaiting first post run |

## Old world: Packer / image-builder

The previous pipeline built the images with Packer and the upstream
`kubernetes-sigs/image-builder` project. Every image published at the URLs below
was built with it. All of those series are published from the DIB pipeline now,
so the unversioned files stay available but are frozen at their last Packer
build.

### Kubernetes versions (old world / Packer) — currently published

> [!WARNING]
> The images below are frozen Packer artifacts containing **v1.34.8**,
> **v1.35.5** and **v1.36.1** and are no longer updated. The unversioned
> `ubuntu-2404-kube-v1.34.qcow2`, `ubuntu-2404-kube-v1.35.qcow2` and
> `ubuntu-2404-kube-v1.36.qcow2` files are not written by the DIB pipeline, so
> they keep serving those old builds. For these series, use the
> [DIB images above](#published-from-the-dib-pipeline).

| Series | Current Version | Image URL                                                                                                                                                | End of Life |
|--------|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| v1.36  | v1.36.1         | [ubuntu-2404-kube-v1.36.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.qcow2)  | 2027-06-28  |
| v1.35  | v1.35.5         | [ubuntu-2404-kube-v1.35.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.qcow2)  | 2027-02-28  |
| v1.34  | v1.34.8         | [ubuntu-2404-kube-v1.34.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.qcow2)  | 2026-10-27  |

### Archived

This section contains images for Kubernetes versions that have reached End of Life (EOL).
These images are no longer updated but remain available for download. Only the final
patch version of each EOL series is kept. All archived images were built with the
old-world Packer pipeline.

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

## Determining Current Versions

For each Kubernetes series, a `last-X` file is published to the object storage during the
CI build process. These files contain the build date and the path to the latest image
for that series.

The files are available at:

```
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.34
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.35
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.36
```

Gardener variants use a parallel `last-X-gardener` file. It exists for every
series published from the DIB pipeline, so currently for `v1.34`, `v1.35` and
`v1.36`:

```
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.34-gardener
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.35-gardener
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.36-gardener
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
- The image uses Ubuntu 24.04
- The full download URL is: `https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.4.qcow2`

To fetch the current version programmatically:

```bash
curl -s https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.36
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
