#!/usr/bin/python3
#
# Render the goss --vars-inline mapping for a built CAPI image.
#
# playbooks/validate.yml boots a freshly built qcow2 and runs upstream
# image-builder's own goss spec inside it. Upstream's Packer "goss" provisioner
# passes a vars_inline object derived from the merged packer/config/*.json plus
# the per-build override; this script reproduces that object for our
# qemu/Ubuntu or Debian build so the same spec asserts the same things.
#
# Usage:
#   render-goss-vars.py [--os {ubuntu,debian}] <config_dir> <override_path>
#
#   --os             the image OS (default: ubuntu); OS_VERSION is read from
#                    the override's <os>_version
#   <config_dir>     a checked-out images/capi/packer/config/ at the pinned
#                    DIB_K8S_IMAGE_BUILDER_REF
#   <override_path>  one of the overrides/*.json files
#
# Every upstream gossfile indexes .Vars.<OS> and .Vars.<OS>.<PROVIDER>, and
# upstream's goss-vars.yaml has no debian section. For --os debian the script
# therefore emits goss-vars-debian.json, next to this script, as the "debian"
# key of the mapping.
#
# The merge order mirrors elements/k8s-capi/install.d/60-run-image-builder: the
# config files are layered in a fixed order and the override is applied last so
# its Kubernetes/containerd versions win. The emitted JSON is written to stdout.
#
###############################################################################

import argparse
import json
import os
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

# The Debian goss section, a mirror of upstream's ubuntu section with Debian
# package names. It lives next to this script.
DEBIAN_SECTION = "goss-vars-debian.json"

# The keys of upstream's ubuntu section that its gossfiles range over, for
# .Vars.OS and for .Vars.OS.PROVIDER. A missing key renders as nil and range
# over nil runs zero times, so goss would skip those checks without failing.
DEBIAN_KEYS = ("common-kernel-param", "common-package", "common-service")
PROVIDER_KEYS = ("package", "service")


def load_json(path):
    """Load a JSON object from path, failing loudly with context on error."""
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError) as err:
        sys.exit(f"ERROR: could not read {path}: {err}")


def merge_config(config_dir, override):
    """Merge the config files in order, then apply the override on top."""
    merged = {}
    for name in CONFIG_FILES:
        merged.update(load_json(f"{config_dir}/{name}.json"))
    merged.update(override)
    return merged


def os_version(override, image_os, override_path):
    """Return the goss OS_VERSION of image_os from the override.

    Ubuntu's YYMM (2604) becomes YY.MM (26.04), the form upstream uses;
    Debian's major version (13) is used as is. A series without the key has
    no image of that OS, which is a hard error.
    """
    value = override.get(f"{image_os}_version")
    if not value:
        sys.exit(
            f"ERROR: {override_path} has no {image_os}_version; "
            f"the series has no {image_os} image"
        )
    value = str(value)
    if image_os == "ubuntu":
        return f"{value[:2]}.{value[2:]}"
    return value


def load_debian_section(path):
    """Load the Debian goss section; every key goss ranges over must be set."""
    section = load_json(path)
    if not isinstance(section, dict) or not isinstance(section.get("qemu"), dict):
        sys.exit(f"ERROR: {path} has no qemu section; goss indexes .Vars.debian.qemu")
    missing = [key for key in DEBIAN_KEYS if not section.get(key)]
    missing += [f"qemu.{key}" for key in PROVIDER_KEYS if not section["qemu"].get(key)]
    if missing:
        sys.exit(
            f"ERROR: {path} lacks {', '.join(missing)}; goss would skip those "
            "checks without failing"
        )
    return section


def strip_v(value):
    """Drop a single leading 'v', mirroring upstream's replace "v" "" 1."""
    return value[1:] if value.startswith("v") else value


def blank_if_none(value):
    """Map JSON null (and missing keys) to "", as the Packer templates do."""
    return "" if value is None else value


def render(merged, image_os, image_os_version):
    """Build the vars_inline mapping upstream's qemu goss provisioner passes."""
    missing = [key for key in REQUIRED_KEYS if merged.get(key) is None]
    if missing:
        sys.exit(
            "ERROR: required keys missing from the merged config/override: "
            + ", ".join(missing)
        )

    # PROVIDER and ARCH are fixed: this repository only builds amd64 qemu
    # images. OS and OS_VERSION follow --os and the override.
    # kubernetes_rpm_version and kubernetes_cni_rpm_version are emitted empty:
    # the rpm-version assertions are gated to non-deb images and never run here.
    return {
        "ARCH": "amd64",
        "OS": image_os,
        "OS_VERSION": image_os_version,
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
        "--os",
        choices=["ubuntu", "debian"],
        default="ubuntu",
        help="the image OS (default: ubuntu)",
    )
    parser.add_argument(
        "config_dir",
        help="checked-out images/capi/packer/config/ at the pinned ref",
    )
    parser.add_argument(
        "override_path",
        help="path to one of the overrides/*.json files",
    )
    args = parser.parse_args()

    override = load_json(args.override_path)
    merged = merge_config(args.config_dir, override)
    rendered = render(
        merged, args.os, os_version(override, args.os, args.override_path)
    )
    if args.os == "debian":
        rendered["debian"] = load_debian_section(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), DEBIAN_SECTION)
        )
    print(json.dumps(rendered, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
