# kubernetes-capi-images

Images intended for use with Kubernetes CAPI providers. More details on
https://image-builder.sigs.k8s.io/capi/capi.html.

The images are built with [diskimage-builder](https://docs.openstack.org/diskimage-builder/latest/)
(DIB). The custom `k8s-capi` element under `elements/` reuses the Ansible roles
of the upstream [Image Builder](https://github.com/kubernetes-sigs/image-builder/)
project, pinned to an immutable commit, so the resulting `ubuntu-XXXX-kube-vX.YY`
qcow2 images match what Image Builder produces. The element is documented in
[`elements/k8s-capi/README.rst`](elements/k8s-capi/README.rst).

Starting with Kubernetes v1.37, every series is also published as a
`debian-13-kube-vX.YY` image built on Debian 13, from the same element, roles
and validation. Image Builder has no Debian build target, so the element closes
the gaps with its own workarounds (see the "Debian" section of the element
README).

The base image is fixed per Kubernetes series and OS and is part of the image
name (`ubuntu-2604-kube-v1.37`, `debian-13-kube-v1.37`). It is set in the
override file of the series (`<os>_release` is the codename, `<os>_version`
the prefix in the image name), see [Building images](#building-images).

| Kubernetes series | Ubuntu base      | Debian base |
|-------------------|------------------|-------------|
| v1.37 and newer   | 26.04 (resolute) | 13 (trixie) |
| v1.33.4 to v1.36  | 24.04 (noble)    | none        |
| up to v1.33.3     | 22.04 (jammy)    | none        |

When a Kubernetes series changes to EOL status, the corresponding builds
are deactivated here and only the last version of this series will remain
available as an image in the future.

The following images contain the latest [stable releases](https://kubernetes.io/releases/),
which are updated as required. This means that the image for version `1.36`
contains, for example, version `1.36.4`.

## Kubernetes versions

Every series is published under two names per OS (see [Building images](#building-images)):

- `<os>-<version>-kube-vX.YY.Z.qcow2` (versioned) is written once and never
  overwritten. Consumers that want a fixed version resolve it through the
  `last-ubuntu-X` or `last-debian-X` pointer file (see [Determining Current Versions](#determining-current-versions)).
- `<os>-<version>-kube-vX.YY.qcow2` (series) is overwritten on every publish run
  and always contains the latest build of the series, including fixes to the
  image itself that do not bump the Kubernetes version.

The `Version` column lists the Kubernetes version the series is currently built
with. It is kept in sync with the `overrides/` files by the upstream sync
workflow; the published versioned image follows with the next publish run.

| Series         | Version  | Series Image (latest build)                                                                                                                                                       | Pointer (fixed version)                                                                              | End of Life |
|----------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|-------------|
| v1.37          | v1.37.1  | [ubuntu-2604-kube-v1.37.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2604-kube-v1.37/ubuntu-2604-kube-v1.37.qcow2) ([CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2604-kube-v1.37/ubuntu-2604-kube-v1.37.qcow2.CHECKSUM))                                     | [last-ubuntu-1.37](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-ubuntu-1.37)     | 2027-10-28  |
| v1.37          | v1.37.1  | [debian-13-kube-v1.37.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/debian-13-kube-v1.37/debian-13-kube-v1.37.qcow2) ([CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/debian-13-kube-v1.37/debian-13-kube-v1.37.qcow2.CHECKSUM))                                     | [last-debian-1.37](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-debian-1.37)     | 2027-10-28  |
| v1.36          | v1.36.5  | [ubuntu-2404-kube-v1.36.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.qcow2) ([CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.qcow2.CHECKSUM))                                     | [last-ubuntu-1.36](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-ubuntu-1.36)     | 2027-06-28  |
| v1.35          | v1.35.9  | [ubuntu-2404-kube-v1.35.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.qcow2) ([CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.35/ubuntu-2404-kube-v1.35.qcow2.CHECKSUM))                                     | [last-ubuntu-1.35](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-ubuntu-1.35)     | 2027-02-28  |
| v1.34          | v1.34.12 | [ubuntu-2404-kube-v1.34.qcow2](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.qcow2) ([CHECKSUM](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.34/ubuntu-2404-kube-v1.34.qcow2.CHECKSUM))                                     | [last-ubuntu-1.34](https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-ubuntu-1.34)     | 2026-10-27  |

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
the base of every OS the series is built on: `ubuntu_release` and
`debian_release` are the codenames diskimage-builder builds on (`DIB_RELEASE`,
e.g. `resolute`, `trixie`), and `ubuntu_version` and `debian_version` the
prefix in the image name (e.g. `2604`, `13`). A series whose override file has
no `debian_release` and `debian_version` has no Debian image, and every build
tool refuses a Debian build of it with a message naming the missing key. The
Kubernetes version fields are kept in sync with the Kubernetes package
repository by the [Sync with upstream](.github/workflows/sync-with-upstream.yml)
workflow, which runs `scripts/update-extra-vars.py` and opens a pull request;
the Ubuntu and Debian fields are only ever changed by hand.

To build an image locally on a Linux host with qemu/libguestfs:

```bash
# Build the latest v1.36 image (the qcow2 lands in output/)
./build-local.sh v1.36

# Build the Debian image of v1.37 (debian-13-kube-v1.37.Z.qcow2)
./build-local.sh v1.37 debian
```

The optional second argument is the OS, `ubuntu` (the default) or `debian`. A
Debian build also needs `debootstrap` and `debian-archive-keyring` on the build
host: debootstrap builds the Debian root filesystem there and verifies the
archive signature with that keyring, and the build aborts when it is missing.

In CI, Zuul builds every series on the `check` pipeline in
build-only mode (`upload_image: false`). On the `post` pipeline, the publish
jobs upload the image, its `.CHECKSUM`, and the pointer files to the object
storage. A job is triggered by changes to its override file, the element, the
playbooks, `scripts/render-goss-vars.py`, `requirements.txt` or `.zuul.yaml`,
and the Debian jobs also by `scripts/goss-vars-debian.json`.

The Debian image of a series has its own job pair,
`k8s-capi-images-build-v1.37-debian` and `k8s-capi-images-publish-v1.37-debian`,
which set the job var `image_os: debian` (unset means `ubuntu`). To give a new
series a Debian image, add `debian_release` and `debian_version` to its
override file and add a build and publish job pair with its own
`files_vX_YY_debian` matcher.

Every publish run builds the image and uploads it under two names:

- `<os>-<version>-kube-vX.YY.Z.qcow2` (versioned) is create-once: the job checks
  whether its `.CHECKSUM` already exists in the object storage and, if so,
  neither overwrites the image nor rewrites its pointer files. A pointer file
  that is missing next to an already published versioned image, such as the
  `last-ubuntu-X` of a version published before that pointer existed, is
  copied from `last-X`, which keeps its build date. The `.CHECKSUM` is
  uploaded after the pointer files, so a run that fails before it publishes
  the image and every pointer file again, and the job fails when the pointer
  files of the series are missing or differ afterwards.
- `<os>-<version>-kube-vX.YY.qcow2` (series) is always overwritten together with
  its `.CHECKSUM`, so every merged change that touches the element, the
  playbooks or the override file ships as a fresh "latest" image of the series,
  even when the Kubernetes version stays the same.

## Validating images

After building, CI asserts that each image actually contains the expected
Kubernetes binaries, containerd, CNI, packages, services, kernel parameters,
and files by running the upstream [Image Builder](https://github.com/kubernetes-sigs/image-builder/)
[goss](https://github.com/goss-org/goss) spec — the same spec upstream uses —
inside the booted image. This is `playbooks/validate.yml`, run after
`playbooks/build.yml` in every build and publish job.

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

Upstream's `goss-image-hygiene.yaml` is checked separately, before the boot. It
asserts that the artifact is sealed: no SSH host keys, no machine-id, and no
cloud-init instance state. Upstream runs it in the Packer build VM right after
sysprep. The validation boot here recreates all three through cloud-init and
systemd before goss can run, so that file runs offline instead: a raw copy of
the unbooted image is loop-mounted read-only and goss runs in a chroot of it.
The VM runs every other gossfile of upstream's `goss.yaml`.

The image boots under QEMU with KVM acceleration where the node exposes
`/dev/kvm` (the build host widens its permissions in `playbooks/pre.yml`),
falling back to TCG software emulation otherwise. The goss spec is re-cloned from
image-builder at the same `DIB_K8S_IMAGE_BUILDER_REF` the build uses (it is not
vendored), and the `goss` binary is pinned to `0.3.23` and verified by checksum,
matching how the build already pins and hashes its inputs.

A failed assertion fails the job, so a change whose image diverges from what
upstream Image Builder produces fails its `check` jobs. In publish runs the
upload tasks at the tail of `playbooks/build.yml` still run before validation,
so validation does not yet gate the upload itself. The goss JSON reports (the
offline hygiene check and the in-VM run) and the VM console log are saved under
`zuul-output/logs/`.

Upstream's goss spec has a section per OS but none for Debian. For the Debian
images, `scripts/render-goss-vars.py --os debian` adds this repository's
`scripts/goss-vars-debian.json` as the `debian` section. It mirrors upstream's
`ubuntu` section with Debian package names. The validation logs in to the VM as
the image's cloud-init default user, `ubuntu` or `debian`.

## Determining Current Versions

For each Kubernetes series and OS, a pointer file is published to the object
storage during the CI build process. It contains the build date and the path to
the latest versioned image of that series:

- `last-ubuntu-X` points at the Ubuntu image.
- `last-debian-X` points at the Debian image, from 1.37 on.
- `last-X` is an alias of `last-ubuntu-X` with identical content. It is kept so
  existing consumers keep working.

The files are available at:

```
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-ubuntu-1.34
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-ubuntu-1.35
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-ubuntu-1.36
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-ubuntu-1.37
https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-debian-1.37
```

and the aliases `last-1.34` to `last-1.37` next to them.

Each file contains a single line in the format:

```
YYYY-MM-DD <os>-<version>-kube-vX.XX/<os>-<version>-kube-vX.XX.X.qcow2
```

For example, `last-ubuntu-1.36` (and `last-1.36`) might contain:

```
2026-09-16 ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.4.qcow2
```

This tells you that:
- The build was created on 2026-09-16
- The current version is v1.36.4
- The image uses Ubuntu 24.04 (`ubuntu-2404`); `last-ubuntu-1.37` names an
  `ubuntu-2604-kube-v1.37/...` image built on Ubuntu 26.04
- The full download URL is: `https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/ubuntu-2404-kube-v1.36/ubuntu-2404-kube-v1.36.4.qcow2`

`last-debian-1.37` might contain:

```
2026-09-26 debian-13-kube-v1.37/debian-13-kube-v1.37.1.qcow2
```

The Debian images log in with Debian's cloud-init default user `debian`, the
Ubuntu images with `ubuntu`.

To fetch the current version programmatically:

```bash
curl -s https://nbg1.your-objectstorage.com/osism/openstack-k8s-capi-images/last-ubuntu-1.36
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

The script covers the Ubuntu images only. The Debian images start at the patch
that was current at the first Debian publish, so not every patch from `.0`
exists; use the Debian series image or `last-debian-X` instead.

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
