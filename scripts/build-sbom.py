#!/usr/bin/python3
#
# Assemble the CycloneDX SBOM of a built CAPI image.
#
# playbooks/sbom.yml scans the unbooted image and every pre-pulled container
# image with syft, which writes one CycloneDX BOM per scan. This script turns
# those into the one SBOM published next to the image: the packages of the
# root filesystem at the top level, and one "container" component per
# pre-pulled image with that image's packages nested beneath it.
#
# Usage:
#   build-sbom.py refs <images_record>
#   build-sbom.py merge --host-bom <path> --images <images_record>
#                       --image-boms <dir> --name <name> --version <version>
#                       --sha256 <hex> --output <path>
#
#   <images_record>  the `crictl images -o json` output the k8s-capi element
#                    records during the build
#                    (<image name>.d/dib-manifests/k8s-capi-container-images.json)
#
# refs validates the record and prints one image reference
# (<repository>@sha256:<digest>) per line, sorted. merge validates it the same
# way and reads the BOM of each of those images from
# <dir>/<digest hex>.cdx.json. --name, --version and --sha256 describe the
# image file in metadata.component, so a consumer can compare the hash with
# the image's .CHECKSUM file.
#
###############################################################################

"""Assemble the CycloneDX SBOM of a built CAPI image."""

import argparse
import json
import os
import re
import sys
from typing import Any, NamedTuple

# Both are used with fullmatch. A reference becomes a syft argument and a file
# name in playbooks/sbom.yml, so nothing outside this character set passes.
REFERENCE_RE = re.compile(r"[A-Za-z0-9._/:-]+@sha256:[0-9a-f]{64}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")

# The architecture playbooks/sbom.yml scans the pre-pulled images for
# (--platform linux/amd64). Change both together.
IMAGE_ARCH = "amd64"


class Image(NamedTuple):
    """A pre-pulled container image from the record."""

    reference: str  # <name>@sha256:<digest>
    name: str  # the repository, e.g. registry.k8s.io/kube-proxy
    digest: str  # the 64 hex characters of the reference
    tag: str | None  # None when no repo tag names the same repository


def load_json(path: str) -> Any:
    """Load a JSON document from path, failing loudly with context on error."""
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError) as err:
        sys.exit(f"ERROR: could not read {path}: {err}")


def image_tag(repo_tags: list[Any], name: str) -> str | None:
    """Return the tag of the first sorted repo tag of repository name, or None."""
    for repo_tag in sorted(map(str, repo_tags)):
        # Split at the last colon: a registry with a port has one of its own.
        repository, _, tag = repo_tag.rpartition(":")
        if repository == name and tag:
            return tag
    return None


def load_images(path: str) -> list[Image]:
    """Validate the record of the pre-pulled images and return its images.

    The list is sorted by reference. Exits with an error when the record is
    unreadable, lists no images, or holds an image without a usable reference.
    """
    record = load_json(path)
    entries = record.get("images") if isinstance(record, dict) else None
    if not isinstance(entries, list):
        sys.exit(f"ERROR: {path} has no images list")
    if not entries:
        sys.exit(f"ERROR: {path} lists no images; the build pre-pulls the Kubernetes images, so the record is incomplete")

    images = []
    for entry in entries:
        if not isinstance(entry, dict):
            entry = {}
        digests = entry.get("repoDigests")
        if not isinstance(digests, list) or not digests:
            sys.exit(f"ERROR: image {entry.get('id', '<unknown>')} in {path} has no repoDigests")
        reference = min(map(str, digests))
        if not REFERENCE_RE.fullmatch(reference):
            sys.exit(f"ERROR: unexpected image reference '{reference}' in {path}")
        name, _, digest = reference.partition("@sha256:")
        images.append(Image(reference, name, digest, image_tag(entry.get("repoTags") or [], name)))
    return sorted(images, key=lambda image: image.reference)


def load_bom(path: str) -> dict[str, Any]:
    """Load the CycloneDX BOM at path, exiting with an error when it is not one."""
    bom = load_json(path)
    if not isinstance(bom, dict) or bom.get("bomFormat") != "CycloneDX":
        sys.exit(f"ERROR: {path} is not a CycloneDX BOM")
    return bom


def sha256_hex(value: str) -> str:
    """Return value when it is a sha256 in lowercase hex (argparse type)."""
    if not SHA256_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("must be 64 lowercase hex characters")
    return value


def prefix_components(components: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    """Return copies of components with prefix on every bom-ref, nested ones included."""
    prefixed = []
    for component in components:
        component = dict(component)
        if "bom-ref" in component:
            component["bom-ref"] = prefix + component["bom-ref"]
        if "components" in component:
            component["components"] = prefix_components(component["components"], prefix)
        prefixed.append(component)
    return prefixed


def prefix_dependencies(dependencies: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    """Return copies of dependencies with prefix on every ref and dependsOn entry."""
    prefixed = []
    for dependency in dependencies:
        dependency = dict(dependency, ref=prefix + dependency["ref"])
        if "dependsOn" in dependency:
            dependency["dependsOn"] = [prefix + target for target in dependency["dependsOn"]]
        prefixed.append(dependency)
    return prefixed


def container_component(image: Image, image_bom: dict[str, Any]) -> dict[str, Any]:
    """Return the container component of image, with the packages of image_bom nested in it.

    The bom-ref of every nested component gets the image digest as prefix,
    because syft numbers the packages of each scan on its own and two images
    can hold the same package.
    """
    _, name, digest, tag = image
    purl = f"pkg:oci/{name.rsplit('/', 1)[-1]}@sha256%3A{digest}?arch={IMAGE_ARCH}&repository_url={name}"
    if tag:
        purl += f"&tag={tag}"
    component = {
        "bom-ref": f"container-{digest}",
        "type": "container",
        "name": name,
        "version": tag or f"sha256:{digest}",
        "purl": purl,
        "hashes": [{"alg": "SHA-256", "content": digest}],
    }
    # An image without packages is valid: syft finds none in the pause image.
    if image_bom.get("components"):
        component["components"] = prefix_components(image_bom["components"], f"{digest}/")
    return component


def refs(args: argparse.Namespace) -> None:
    """Print the reference of every recorded image, one per line."""
    for image in load_images(args.images):
        print(image.reference)


def merge(args: argparse.Namespace) -> None:
    """Write the SBOM of the image file to args.output.

    The host BOM is kept as it is, apart from metadata.component, which
    describes the image file. One container component per recorded image is
    appended to it. Exits with an error when a BOM is missing, is not a
    CycloneDX BOM of the host BOM's specVersion, or the host BOM lists no
    components.
    """
    images = load_images(args.images)
    bom = load_bom(args.host_bom)
    if not isinstance(bom.get("components"), list) or not bom["components"]:
        sys.exit(f"ERROR: {args.host_bom} lists no components; the host scan found no packages")

    bom.setdefault("metadata", {})["component"] = {
        "bom-ref": "image",
        "type": "file",
        "name": args.name,
        "version": args.version,
        "hashes": [{"alg": "SHA-256", "content": args.sha256}],
    }

    for image in images:
        path = os.path.join(args.image_boms, f"{image.digest}.cdx.json")
        image_bom = load_bom(path)
        if image_bom.get("specVersion") != bom.get("specVersion"):
            sys.exit(f"ERROR: {path} has specVersion {image_bom.get('specVersion')}, expected {bom.get('specVersion')}")
        bom["components"].append(container_component(image, image_bom))
        if image_bom.get("dependencies"):
            bom.setdefault("dependencies", []).extend(prefix_dependencies(image_bom["dependencies"], f"{image.digest}/"))

    try:
        with open(args.output, "w") as handle:
            json.dump(bom, handle, indent=2)
            handle.write("\n")
    except OSError as err:
        sys.exit(f"ERROR: could not write {args.output}: {err}")


def main(argv: list[str] | None = None) -> None:
    """Parse argv (default: the command line) and run the chosen subcommand."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    refs_parser = subparsers.add_parser("refs", help="validate the record and print one image reference per line")
    refs_parser.add_argument("images", metavar="images_record", help="the recorded `crictl images -o json` output")
    refs_parser.set_defaults(run=refs)

    merge_parser = subparsers.add_parser("merge", help="merge the host BOM and the image BOMs into the SBOM of the image")
    merge_parser.add_argument("--host-bom", required=True, help="CycloneDX BOM of the image's root filesystem")
    merge_parser.add_argument("--images", required=True, help="the recorded `crictl images -o json` output")
    merge_parser.add_argument("--image-boms", required=True, help="directory with one <digest hex>.cdx.json per recorded image")
    merge_parser.add_argument("--name", required=True, help="file name of the image the SBOM describes")
    merge_parser.add_argument("--version", required=True, help="Kubernetes version of the image")
    merge_parser.add_argument("--sha256", required=True, type=sha256_hex, help="sha256 of the image file, 64 lowercase hex characters")
    merge_parser.add_argument("--output", required=True, help="path the SBOM is written to")
    merge_parser.set_defaults(run=merge)

    args = parser.parse_args(argv)
    args.run(args)


if __name__ == "__main__":
    main()
