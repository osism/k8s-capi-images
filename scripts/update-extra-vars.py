#!/usr/bin/python3
#
# Script to fetch the latest version of kubernetes by the given file.
# Also updates the README.md Kubernetes Versions table.
#
###############################################################################

import json
import os
import re
import sys
import urllib.error
import urllib.request


###############################################################################
# Variables
###############################################################################

# The apt repository the image build itself installs from, so it is the only
# source that can tell us which versions are actually installable. Deriving the
# version from the Kubernetes git tags instead would guess the Debian revision
# suffix (it is not always "-1.1", e.g. 1.36.2 ships as 1.36.2-2.1) and would
# pick up a tag before its packages have been built.
package_index_url = "https://pkgs.k8s.io/core:/stable:/{series}/deb/Packages"

# The image build pins these to a single version, so only a version that all of
# them share is usable.
required_packages = ("kubeadm", "kubectl", "kubelet")

file = sys.argv[1]
script_dir = os.path.dirname(os.path.abspath(__file__))
readme_path = os.path.join(script_dir, "..", "README.md")


###############################################################################
# Functions
###############################################################################


def load_file(file):
    with open(file) as json_load_file:
        data = json.load(json_load_file)
    return data


def parse_package_index(index):
    """Map each package name in a Debian "Packages" index to its versions.

    Stanzas are separated by a blank line and repeat per architecture, hence
    the set of versions per package rather than a single value.
    """
    versions = {}

    for stanza in index.split("\n\n"):
        name = None
        version = None
        for line in stanza.splitlines():
            # Continuation lines (e.g. inside Description) are indented, so a
            # field only counts when its name starts the line.
            if line.startswith("Package:"):
                name = line.partition(":")[2].strip()
            elif line.startswith("Version:"):
                version = line.partition(":")[2].strip()
        if name and version:
            versions.setdefault(name, set()).add(version)

    return versions


def deb_version_key(version):
    """Sort key comparing each numeric run of a version as a number.

    A plain string compare would sort 1.33.9-1.1 above 1.33.13-1.1.
    """
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in re.findall(r"\d+|\D+", version)
    )


def latest_deb_version(series):
    """Return the newest version of the series that all required packages share."""
    url = package_index_url.format(series=series)
    with urllib.request.urlopen(url, timeout=30) as response:
        versions = parse_package_index(response.read().decode())

    shared = set.intersection(
        *(versions.get(package, set()) for package in required_packages)
    )

    # The repository of a series carries packages of other series too (cri-tools
    # for instance), so restrict the candidates to the series being updated.
    prefix = series.lstrip("v") + "."
    candidates = [version for version in shared if version.startswith(prefix)]

    if not candidates:
        raise LookupError(
            f"{url} lists no {prefix}x version shared by {', '.join(required_packages)}"
        )

    return max(candidates, key=deb_version_key)


def update_version(data):
    # e.g. 1.36.2-2.1
    deb_version = latest_deb_version(data["kubernetes_series"])
    data["kubernetes_deb_version"] = deb_version
    # e.g. v1.36.2
    data["kubernetes_semver"] = "v" + deb_version.split("-")[0]

    return data


def dump_file(file, data):
    with open(file, "w") as fp:
        json.dump(data, fp, indent=4, sort_keys=True)
        fp.write("\n")


def update_readme(series, new_version):
    """Update the Kubernetes Versions table in README.md with the new version."""
    if not os.path.exists(readme_path):
        print(f"Warning: README.md not found at {readme_path}")
        return

    with open(readme_path, "r") as f:
        content = f.read()

    # This script maintains the versions that get built, so it may only rewrite
    # the "Target Version" table. The README carries a second table listing the
    # versions the old Packer pipeline actually published; rewriting that one
    # would advertise images that do not exist.
    table = re.search(
        r"\| Series \| Target Version \|.*?(?=\n\n|\Z)", content, re.DOTALL
    )
    if not table:
        print("Warning: no 'Target Version' table found in README.md")
        return

    # Pattern to match the table row for this series
    # Matches: | v1.32  | v1.32.8         | [ubuntu-...
    # Captures the version and trailing spaces together to calculate total width
    pattern = rf"(\| {re.escape(series)}\s+\| )(v[\d.]+\s+)(\|)"

    def replace_version(match):
        prefix = match.group(1)
        old_version_with_spaces = match.group(2)
        suffix = match.group(3)
        # Keep the same total width for the column
        total_width = len(old_version_with_spaces)
        new_version_padded = new_version.ljust(total_width)
        return prefix + new_version_padded + suffix

    updated_table = re.sub(pattern, replace_version, table.group(0))

    if updated_table != table.group(0):
        start, end = table.span()
        with open(readme_path, "w") as f:
            f.write(content[:start] + updated_table + content[end:])
        print(f"Updated README.md: {series} -> {new_version}")
    else:
        print(f"README.md already up to date for {series}")


###############################################################################
# Main
###############################################################################

original_data = load_file(file)
try:
    updated_data = update_version(original_data)
except (urllib.error.URLError, TimeoutError, LookupError) as err:
    # An unknown series answers with a 403 rather than a 404, and the endpoint
    # can stall or be unreachable. Fail this file loudly instead of crashing
    # with a traceback so the surrounding loop can move on.
    print(f"Error: could not fetch Kubernetes versions for {file}: {err}")
    sys.exit(1)

dump_file(file, updated_data)

# Always update README.md to ensure it's in sync with extra_vars
update_readme(
    updated_data.get("kubernetes_series"), updated_data.get("kubernetes_semver")
)
