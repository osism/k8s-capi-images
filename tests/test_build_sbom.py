"""Tests for scripts/build-sbom.py.

Run with: python3 -m unittest discover -s tests
"""

import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "build-sbom.py"

# The file name has a hyphen, so the script cannot be imported by name.
spec = importlib.util.spec_from_file_location("build_sbom", SCRIPT)
build_sbom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_sbom)

PROXY_DIGEST = "b9ae667e" + "0" * 56
PAUSE_DIGEST = "27e3830e" + "1" * 56
IMAGE_SHA256 = "5f" * 32

PROXY_IMAGE = {
    "id": "sha256:11f9049f",
    "repoTags": ["registry.k8s.io/kube-proxy:v1.37.1"],
    "repoDigests": [f"registry.k8s.io/kube-proxy@sha256:{PROXY_DIGEST}"],
    "size": "26513890",
    "pinned": False,
}
PAUSE_IMAGE = {
    "id": "sha256:873ed751",
    "repoTags": ["registry.k8s.io/pause:3.10.1"],
    "repoDigests": [f"registry.k8s.io/pause@sha256:{PAUSE_DIGEST}"],
    "size": "320448",
    "pinned": True,
}

# Host and image BOM use the same bom-ref for their libc6 on purpose: only the
# prefix the merge adds keeps the two apart.
LIBC6_REF = "pkg:deb/libc6@2.41?package-id=1"
HOST_BOM = {
    "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "serialNumber": "urn:uuid:3e671687-395b-41f5-a30f-a58921a69b79",
    "version": 1,
    "metadata": {
        "timestamp": "2026-10-02T10:00:00Z",
        "tools": {"components": [{"type": "application", "author": "anchore", "name": "syft", "version": "1.54.0"}]},
        "component": {"bom-ref": "af63bd4c8601b7f1", "type": "file", "name": "/home/zuul/sbom/root"},
    },
    "components": [
        {"bom-ref": "pkg:deb/ubuntu/kubelet@1.37.1-1.1?package-id=2", "type": "library", "name": "kubelet", "version": "1.37.1-1.1"},
        {"bom-ref": LIBC6_REF, "type": "library", "name": "libc6", "version": "2.41-6ubuntu1"},
    ],
    "dependencies": [
        {"ref": "pkg:deb/ubuntu/kubelet@1.37.1-1.1?package-id=2", "dependsOn": [LIBC6_REF]},
    ],
}
PROXY_BOM = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "metadata": {"component": {"bom-ref": "5c0a4e9d", "type": "container", "name": "registry.k8s.io/kube-proxy"}},
    "components": [
        {"bom-ref": "pkg:deb/debian/iptables@1.8.9?package-id=3", "type": "library", "name": "iptables", "version": "1.8.9-2"},
        {"bom-ref": LIBC6_REF, "type": "library", "name": "libc6", "version": "2.36-9+deb12u13"},
    ],
    "dependencies": [
        {"ref": "pkg:deb/debian/iptables@1.8.9?package-id=3", "dependsOn": [LIBC6_REF]},
        {"ref": LIBC6_REF},
    ],
}
# syft writes neither components nor dependencies for the pause image.
PAUSE_BOM = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "metadata": {"component": {"bom-ref": "0d1f7a3b", "type": "container", "name": "registry.k8s.io/pause"}},
}


def all_bom_refs(components):
    """Return the bom-ref of every component, nested ones included."""
    refs = []
    for component in components:
        refs.append(component["bom-ref"])
        refs.extend(all_bom_refs(component.get("components", [])))
    return refs


class BuildSbomTestCase(unittest.TestCase):
    """Run the script's command line against files in a temporary directory."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)
        self.image_boms = self.tmp / "images"
        self.image_boms.mkdir()
        self.output = self.tmp / "image.qcow2.cdx.json"

    def write(self, name, data):
        """Write data as JSON to name in the temporary directory and return the path."""
        path = self.tmp / name
        path.write_text(json.dumps(data))
        return str(path)

    def run_script(self, *argv):
        """Run the command line and return (exit code, stdout, stderr), as a shell would see them."""
        stdout, stderr = io.StringIO(), io.StringIO()
        code = 0
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                build_sbom.main(list(argv))
            except SystemExit as exit_:
                code = exit_.code
        # The interpreter prints a string exit code to stderr and exits 1.
        if isinstance(code, str):
            stderr.write(code + "\n")
            code = 1
        return code or 0, stdout.getvalue(), stderr.getvalue()

    def run_merge(self, images=(PROXY_IMAGE,), host_bom=None, image_boms=None, sha256=IMAGE_SHA256):
        """Run merge on the given record and BOMs and return what run_script returns."""
        if image_boms is None:
            image_boms = {PROXY_DIGEST: PROXY_BOM}
        for digest, bom in image_boms.items():
            self.write(f"images/{digest}.cdx.json", bom)
        return self.run_script(
            "merge",
            "--host-bom", self.write("host.cdx.json", HOST_BOM if host_bom is None else host_bom),
            "--images", self.write("images.json", {"images": list(images)}),
            "--image-boms", str(self.image_boms),
            "--name", "ubuntu-2604-kube-v1.37.1.qcow2",
            "--version", "v1.37.1",
            "--sha256", sha256,
            "--output", str(self.output),
        )

    def merged(self, **kwargs):
        """Run merge, expect it to succeed and return the SBOM it wrote."""
        code, _, stderr = self.run_merge(**kwargs)
        self.assertEqual((code, stderr), (0, ""))
        return json.loads(self.output.read_text())

    def containers(self, bom):
        """Return the container components of a merged SBOM."""
        return [component for component in bom["components"] if component["type"] == "container"]


class RefsTest(BuildSbomTestCase):
    """The refs subcommand validates the record and prints the image references."""

    def test_refs_prints_one_sorted_reference_per_image(self):
        other_digest = f"registry.k8s.io/kube-proxy@sha256:{'f' * 64}"
        proxy = dict(PROXY_IMAGE, repoDigests=[other_digest] + PROXY_IMAGE["repoDigests"])
        record = self.write("images.json", {"images": [PAUSE_IMAGE, proxy]})

        code, stdout, stderr = self.run_script("refs", record)

        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(
            stdout,
            f"registry.k8s.io/kube-proxy@sha256:{PROXY_DIGEST}\nregistry.k8s.io/pause@sha256:{PAUSE_DIGEST}\n",
        )

    def test_refs_rejects_an_empty_images_list(self):
        record = self.write("images.json", {"images": []})

        code, stdout, stderr = self.run_script("refs", record)

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(
            stderr,
            f"ERROR: {record} lists no images; the build pre-pulls the Kubernetes images, so the record is incomplete\n",
        )

    def test_refs_rejects_a_record_without_images_list(self):
        for content in ({}, {"images": {}}, []):
            with self.subTest(content=content):
                record = self.write("images.json", content)

                code, stdout, stderr = self.run_script("refs", record)

                self.assertEqual((code, stdout), (1, ""))
                self.assertEqual(stderr, f"ERROR: {record} has no images list\n")

    def test_refs_rejects_an_image_without_repo_digests(self):
        without_key = {key: value for key, value in PROXY_IMAGE.items() if key != "repoDigests"}
        for image in (dict(PROXY_IMAGE, repoDigests=[]), without_key):
            with self.subTest(image=image):
                record = self.write("images.json", {"images": [PAUSE_IMAGE, image]})

                code, stdout, stderr = self.run_script("refs", record)

                self.assertEqual((code, stdout), (1, ""))
                self.assertEqual(stderr, f"ERROR: image sha256:11f9049f in {record} has no repoDigests\n")

    def test_refs_rejects_an_image_entry_without_an_id_or_that_is_not_an_object(self):
        for image in ("registry.k8s.io/pause", {"repoTags": []}):
            with self.subTest(image=image):
                record = self.write("images.json", {"images": [PAUSE_IMAGE, image]})

                code, stdout, stderr = self.run_script("refs", record)

                self.assertEqual((code, stdout), (1, ""))
                self.assertEqual(stderr, f"ERROR: image <unknown> in {record} has no repoDigests\n")

    def test_refs_rejects_a_reference_with_a_space(self):
        reference = f"registry.k8s.io/kube proxy@sha256:{PROXY_DIGEST}"
        record = self.write("images.json", {"images": [dict(PROXY_IMAGE, repoDigests=[reference])]})

        code, stdout, stderr = self.run_script("refs", record)

        self.assertEqual((code, stdout), (1, ""))
        self.assertEqual(stderr, f"ERROR: unexpected image reference '{reference}' in {record}\n")

    def test_refs_rejects_a_reference_without_a_sha256_digest(self):
        for reference in ("registry.k8s.io/kube-proxy:v1.37.1", f"registry.k8s.io/kube-proxy@sha256:{PROXY_DIGEST.upper()}", 7):
            with self.subTest(reference=reference):
                record = self.write("images.json", {"images": [dict(PROXY_IMAGE, repoDigests=[reference])]})

                code, _, stderr = self.run_script("refs", record)

                self.assertEqual(code, 1)
                self.assertEqual(stderr, f"ERROR: unexpected image reference '{reference}' in {record}\n")

    def test_refs_reports_an_unreadable_record(self):
        missing = str(self.tmp / "missing.json")
        invalid = self.tmp / "invalid.json"
        invalid.write_text('{"images": [')
        for record in (missing, str(invalid)):
            with self.subTest(record=record):
                code, stdout, stderr = self.run_script("refs", record)

                self.assertEqual((code, stdout), (1, ""))
                self.assertTrue(stderr.startswith(f"ERROR: could not read {record}: "), stderr)


class MergeTest(BuildSbomTestCase):
    """The merge subcommand writes the SBOM of the image file."""

    def test_merge_describes_the_image_file_in_metadata_component(self):
        bom = self.merged()

        self.assertEqual(
            bom["metadata"]["component"],
            {
                "bom-ref": "image",
                "type": "file",
                "name": "ubuntu-2604-kube-v1.37.1.qcow2",
                "version": "v1.37.1",
                "hashes": [{"alg": "SHA-256", "content": IMAGE_SHA256}],
            },
        )
        self.assertEqual(bom["components"][:2], HOST_BOM["components"])
        for key in ("$schema", "bomFormat", "specVersion", "serialNumber", "version"):
            self.assertEqual(bom[key], HOST_BOM[key])
        for key in ("timestamp", "tools"):
            self.assertEqual(bom["metadata"][key], HOST_BOM["metadata"][key])

    def test_merge_nests_image_packages_under_a_container_component(self):
        bom = self.merged()

        self.assertEqual(
            self.containers(bom),
            [
                {
                    "bom-ref": f"container-{PROXY_DIGEST}",
                    "type": "container",
                    "name": "registry.k8s.io/kube-proxy",
                    "version": "v1.37.1",
                    "purl": f"pkg:oci/kube-proxy@sha256%3A{PROXY_DIGEST}?arch=amd64&repository_url=registry.k8s.io/kube-proxy&tag=v1.37.1",
                    "hashes": [{"alg": "SHA-256", "content": PROXY_DIGEST}],
                    "components": [
                        {
                            "bom-ref": f"{PROXY_DIGEST}/pkg:deb/debian/iptables@1.8.9?package-id=3",
                            "type": "library",
                            "name": "iptables",
                            "version": "1.8.9-2",
                        },
                        {"bom-ref": f"{PROXY_DIGEST}/{LIBC6_REF}", "type": "library", "name": "libc6", "version": "2.36-9+deb12u13"},
                    ],
                }
            ],
        )
        self.assertEqual(len(bom["components"]), 3)

    def test_merge_prefixes_the_bom_ref_of_components_nested_in_image_packages(self):
        proxy_bom = dict(PROXY_BOM, components=[{"bom-ref": "outer", "type": "library", "name": "outer", "components": [{"bom-ref": "inner", "type": "library", "name": "inner"}]}])

        bom = self.merged(image_boms={PROXY_DIGEST: proxy_bom})

        self.assertEqual(
            all_bom_refs(self.containers(bom)),
            [f"container-{PROXY_DIGEST}", f"{PROXY_DIGEST}/outer", f"{PROXY_DIGEST}/inner"],
        )

    def test_merge_output_has_unique_bom_refs_and_no_dangling_dependency(self):
        bom = self.merged(images=(PROXY_IMAGE, PAUSE_IMAGE), image_boms={PROXY_DIGEST: PROXY_BOM, PAUSE_DIGEST: PAUSE_BOM})

        bom_refs = all_bom_refs([bom["metadata"]["component"]] + bom["components"])
        self.assertEqual(sorted(bom_refs), sorted(set(bom_refs)))
        self.assertEqual(len(bom["dependencies"]), 3)
        for dependency in bom["dependencies"]:
            self.assertIn(dependency["ref"], bom_refs)
            for target in dependency.get("dependsOn", []):
                self.assertIn(target, bom_refs)
        self.assertIn({"ref": f"{PROXY_DIGEST}/{LIBC6_REF}"}, bom["dependencies"])

    def test_merge_accepts_an_image_bom_without_components(self):
        for pause_bom in (PAUSE_BOM, dict(PAUSE_BOM, components=[])):
            with self.subTest(pause_bom=pause_bom):
                bom = self.merged(images=(PAUSE_IMAGE,), image_boms={PAUSE_DIGEST: pause_bom})

                (container,) = self.containers(bom)
                self.assertEqual(container["name"], "registry.k8s.io/pause")
                self.assertNotIn("components", container)
                self.assertEqual(bom["dependencies"], HOST_BOM["dependencies"])

    def test_merge_uses_the_digest_as_version_without_a_tag(self):
        for repo_tags in ([], ["registry.k8s.io/kube-proxy-arm64:v1.37.1"]):
            with self.subTest(repo_tags=repo_tags):
                bom = self.merged(images=(dict(PROXY_IMAGE, repoTags=repo_tags),))

                (container,) = self.containers(bom)
                self.assertEqual(container["version"], f"sha256:{PROXY_DIGEST}")
                self.assertEqual(
                    container["purl"],
                    f"pkg:oci/kube-proxy@sha256%3A{PROXY_DIGEST}?arch=amd64&repository_url=registry.k8s.io/kube-proxy",
                )

    def test_merge_takes_the_first_sorted_tag_of_an_image_with_several_tags(self):
        repo_tags = ["registry.k8s.io/kube-proxy:v1.37.1", "registry.k8s.io/kube-proxy:latest", "registry.k8s.io/other:a"]

        bom = self.merged(images=(dict(PROXY_IMAGE, repoTags=repo_tags),))

        (container,) = self.containers(bom)
        self.assertEqual(container["version"], "latest")
        self.assertTrue(container["purl"].endswith("&tag=latest"), container["purl"])

    def test_merge_takes_the_tag_of_a_registry_with_a_port_from_the_last_colon(self):
        image = {
            "id": "sha256:11f9049f",
            "repoTags": ["localhost:5000/k8s/kube-proxy:v1.37.1"],
            "repoDigests": [f"localhost:5000/k8s/kube-proxy@sha256:{PROXY_DIGEST}"],
        }

        bom = self.merged(images=(image,))

        (container,) = self.containers(bom)
        self.assertEqual(container["name"], "localhost:5000/k8s/kube-proxy")
        self.assertEqual(container["version"], "v1.37.1")
        self.assertEqual(
            container["purl"],
            f"pkg:oci/kube-proxy@sha256%3A{PROXY_DIGEST}?arch=amd64&repository_url=localhost:5000/k8s/kube-proxy&tag=v1.37.1",
        )

    def test_merge_orders_containers_like_refs(self):
        images = (PAUSE_IMAGE, PROXY_IMAGE)

        bom = self.merged(images=images, image_boms={PROXY_DIGEST: PROXY_BOM, PAUSE_DIGEST: PAUSE_BOM})
        _, refs, _ = self.run_script("refs", self.write("images.json", {"images": list(images)}))

        self.assertEqual(
            [f"{container['name']}@{container['hashes'][0]['content']}" for container in self.containers(bom)],
            [reference.replace("@sha256:", "@") for reference in refs.splitlines()],
        )

    def test_merge_rejects_a_host_bom_without_components(self):
        without_key = {key: value for key, value in HOST_BOM.items() if key != "components"}
        for host_bom in (dict(HOST_BOM, components=[]), without_key):
            with self.subTest(host_bom=host_bom):
                code, _, stderr = self.run_merge(host_bom=host_bom)

                self.assertEqual(code, 1)
                self.assertEqual(stderr, f"ERROR: {self.tmp}/host.cdx.json lists no components; the host scan found no packages\n")
                self.assertFalse(self.output.exists())

    def test_merge_rejects_a_host_bom_without_bom_format(self):
        host_bom = {key: value for key, value in HOST_BOM.items() if key != "bomFormat"}

        code, _, stderr = self.run_merge(host_bom=host_bom)

        self.assertEqual(code, 1)
        self.assertEqual(stderr, f"ERROR: {self.tmp}/host.cdx.json is not a CycloneDX BOM\n")
        self.assertFalse(self.output.exists())

    def test_merge_reports_a_missing_image_bom(self):
        code, _, stderr = self.run_merge(images=(PROXY_IMAGE, PAUSE_IMAGE))

        self.assertEqual(code, 1)
        self.assertTrue(stderr.startswith(f"ERROR: could not read {self.image_boms}/{PAUSE_DIGEST}.cdx.json: "), stderr)
        self.assertFalse(self.output.exists())

    def test_merge_rejects_an_image_bom_of_another_spec_version(self):
        code, _, stderr = self.run_merge(image_boms={PROXY_DIGEST: dict(PROXY_BOM, specVersion="1.7")})

        self.assertEqual(code, 1)
        self.assertEqual(stderr, f"ERROR: {self.image_boms}/{PROXY_DIGEST}.cdx.json has specVersion 1.7, expected 1.6\n")
        self.assertFalse(self.output.exists())

    def test_merge_rejects_a_malformed_sha256(self):
        for sha256 in ("xyz", IMAGE_SHA256.upper(), IMAGE_SHA256 + "0"):
            with self.subTest(sha256=sha256):
                code, _, stderr = self.run_merge(sha256=sha256)

                self.assertEqual(code, 2)
                self.assertIn("argument --sha256: must be 64 lowercase hex characters", stderr)
                self.assertFalse(self.output.exists())

    def test_merge_validates_the_record_before_reading_boms(self):
        code, _, stderr = self.run_merge(images=(), host_bom={})

        self.assertEqual(code, 1)
        self.assertEqual(
            stderr,
            f"ERROR: {self.tmp}/images.json lists no images; the build pre-pulls the Kubernetes images, so the record is incomplete\n",
        )

    def test_merge_reports_an_output_path_it_cannot_write(self):
        self.output = self.tmp / "missing" / "image.qcow2.cdx.json"

        code, _, stderr = self.run_merge()

        self.assertEqual(code, 1)
        self.assertTrue(stderr.startswith(f"ERROR: could not write {self.output}: "), stderr)

    def test_merge_writes_indented_json_with_a_trailing_newline(self):
        bom = self.merged()

        self.assertEqual(self.output.read_text(), json.dumps(bom, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
