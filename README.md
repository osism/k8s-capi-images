# kubernetes-capi-images

Images intended for use with Kubernetes CAPI providers. More details on
https://image-builder.sigs.k8s.io/capi/capi.html.

The images are built with the [Image Builder](https://github.com/kubernetes-sigs/image-builder/),
a collection of cross-provider Kubernetes virtual machine image building
utilities.

When a Kubernetes series changes to EOL status, the corresponding builds
are deactivated here and only the last version of this series will remain
available as an image in the future.

The following images contain the latest [stable releases](https://kubernetes.io/releases/),
which are updated as required. This means that the image for version `1.27`
contains, for example, version `1.27.3`.

## Kubernetes Versions

| Series | Current Version | Image URL                                                                                                                                                | End of Life |
|--------|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| v1.35  | v1.35.0         | [ubuntu-2404-kube-v1.35.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.qcow2)  | 2027-02-28  |
| v1.34  | v1.34.3         | [ubuntu-2404-kube-v1.34.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.qcow2)  | 2026-10-27  |
| v1.33  | v1.33.7         | [ubuntu-2404-kube-v1.33.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.33/ubuntu-2404-kube-v1.33.qcow2)  | 2026-06-28  |
| v1.32  | v1.32.11        | [ubuntu-2204-kube-v1.32.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.32/ubuntu-2204-kube-v1.32.qcow2)  | 2026-02-28  |

## Determining Current Versions

For each Kubernetes series, a `last-X` file is published to the object storage during the
CI build process. These files contain the build date and the path to the latest image
for that series.

The files are available at:

```
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.32
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.33
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.34
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.35
```

Each file contains a single line in the format:

```
YYYY-MM-DD ubuntu-XXXX-kube-vX.XX/ubuntu-XXXX-kube-vX.XX.X.qcow2
```

For example, `last-1.32` might contain:

```
2025-11-15 ubuntu-2204-kube-v1.32/ubuntu-2204-kube-v1.32.10.qcow2
```

This tells you that:
- The build was created on 2025-11-15
- The current version is v1.32.10
- The image uses Ubuntu 22.04
- The full download URL is: `https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2204-kube-v1.32/ubuntu-2204-kube-v1.32.10.qcow2`

To fetch the current version programmatically:

```bash
curl -s https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.32
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

The minimum supported version is `1.32`.

Example output:

```
Fetching https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-1.35 ...
Content: 2025-12-19 ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.0.qcow2

Latest version: v1.35.0

=========================================
 Download URLs (v1.35.0 - v1.35.0)
=========================================

https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.0.qcow2

Total: 1 images
```

## Archived

This section contains images for Kubernetes versions that have reached End of Life (EOL).
These images are no longer updated but remain available for download. Only the final
patch version of each EOL series is kept.

| Series | Version  | Image URL                                                                                                                                                 | CHECKSUM URL                                                                                                                                                              |
|--------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
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

