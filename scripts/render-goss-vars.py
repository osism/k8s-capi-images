#!/usr/bin/python3
#
# Render the goss --vars-inline mapping for a built CAPI image.
#
# playbooks/validate.yml boots a freshly built qcow2 and runs upstream
# image-builder's own goss spec inside it. Upstream's Packer "goss" provisioner
# passes a vars_inline object derived from the merged packer/config/*.json plus
# the per-build override; this script reproduces that object for our qemu/Ubuntu
# build so the same spec asserts the same things.
#
# Usage:
#   render-goss-vars.py <config_dir> <override_path>
#
#   <config_dir>     a checked-out images/capi/packer/config/ at the pinned
#                    DIB_K8S_IMAGE_BUILDER_REF
#   <override_path>  one of the overrides/*.json files
#
# The merge order mirrors elements/k8s-capi/install.d/60-run-image-builder: the
# config files are layered in a fixed order and the override is applied last so
# its Kubernetes/containerd versions win. The emitted JSON is written to stdout.
#
###############################################################################

import argparse
import json
import sys

# The config files image-builder loads for a node build, in the same order the
# in-chroot run merges them (override applied last by the caller's merge).
CONFIG_FILES = [
    "common",
    "containerd",
    "cni",
    "kubernetes",
    "wasm-shims",
    "additional_components",
    "ecr_credential_provider",
]

# Keys that must be present after merging config + override. They drive the
# assertions the spec actually runs for an Ubuntu/pkg image, so a missing key is
# a hard error rather than a silently degraded validation.
REQUIRED_KEYS = [
    "containerd_version",
    "kubernetes_cni_semver",
    "kubernetes_deb_version",
    "kubernetes_semver",
]


def load_json(path):
    """Load a JSON object from path, failing loudly with context on error."""
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError) as err:
        sys.exit(f"ERROR: could not read {path}: {err}")


def merge_config(config_dir, override_path):
    """Merge the config files in order, then apply the override on top."""
    merged = {}
    for name in CONFIG_FILES:
        merged.update(load_json(f"{config_dir}/{name}.json"))
    merged.update(load_json(override_path))
    return merged


def strip_v(value):
    """Drop a single leading 'v', mirroring upstream's replace "v" "" 1."""
    return value[1:] if value.startswith("v") else value


def blank_if_none(value):
    """Map JSON null (and missing keys) to "", as the Packer templates do."""
    return "" if value is None else value


def render(merged):
    """Build the vars_inline mapping upstream's qemu goss provisioner passes."""
    missing = [key for key in REQUIRED_KEYS if merged.get(key) is None]
    if missing:
        sys.exit(
            "ERROR: required keys missing from the merged config/override: "
            + ", ".join(missing)
        )

    # OS/OS_VERSION/PROVIDER/ARCH are fixed: this repository only builds the
    # amd64 Ubuntu 24.04 qemu image, so the per-OS selectors are constant.
    # kubernetes_rpm_version and kubernetes_cni_rpm_version are emitted empty:
    # the rpm-version assertions are gated to non-deb images and never run here.
    return {
        "ARCH": "amd64",
        "OS": "ubuntu",
        "OS_VERSION": "24.04",
        "PROVIDER": "qemu",
        "containerd_image_pull_progress_timeout": blank_if_none(
            merged.get("containerd_image_pull_progress_timeout")
        ),
        "containerd_version": merged["containerd_version"],
        "kubernetes_cni_deb_version": blank_if_none(
            merged.get("kubernetes_cni_deb_version")
        ),
        "kubernetes_cni_rpm_version": "",
        "kubernetes_cni_source_type": merged.get("kubernetes_cni_source_type"),
        "kubernetes_cni_version": strip_v(merged["kubernetes_cni_semver"]),
        "kubernetes_deb_version": merged["kubernetes_deb_version"],
        "kubernetes_rpm_version": "",
        "kubernetes_source_type": merged.get("kubernetes_source_type"),
        "kubernetes_version": strip_v(merged["kubernetes_semver"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config_dir",
        help="checked-out images/capi/packer/config/ at the pinned ref",
    )
    parser.add_argument(
        "override_path",
        help="path to one of the overrides/*.json files",
    )
    args = parser.parse_args()

    merged = merge_config(args.config_dir, args.override_path)
    print(json.dumps(render(merged), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
