"""Tests for scripts/render-goss-vars.py.

Run with: python3 -m unittest discover -s tests
"""

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
SCRIPT = os.path.join(SCRIPTS, "render-goss-vars.py")
DEBIAN_SECTION = os.path.join(SCRIPTS, "goss-vars-debian.json")

_spec = importlib.util.spec_from_file_location("render_goss_vars", SCRIPT)
render_goss_vars = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_goss_vars)


def write_json(path, data):
    with open(path, "w") as handle:
        json.dump(data, handle)


class OsVersionTest(unittest.TestCase):
    def test_ubuntu_version_is_rendered_as_yy_mm(self):
        override = {"ubuntu_version": "2604"}
        self.assertEqual(render_goss_vars.os_version(override, "ubuntu", "v1.37.json"), "26.04")

    def test_debian_version_is_used_as_is(self):
        override = {"debian_version": "13"}
        self.assertEqual(render_goss_vars.os_version(override, "debian", "v1.37.json"), "13")

    def test_series_without_the_os_version_is_refused(self):
        with self.assertRaises(SystemExit) as raised:
            render_goss_vars.os_version({"ubuntu_version": "2404"}, "debian", "v1.36.json")
        self.assertIn("debian_version", str(raised.exception.code))


class DebianSectionTest(unittest.TestCase):
    # The keys upstream's gossfiles range over for .Vars.OS and for
    # .Vars.OS.PROVIDER; a missing one would make goss skip its checks.
    OS_KEYS = ("common-kernel-param", "common-package", "common-service")
    PROVIDER_KEYS = ("package", "service")

    def setUp(self):
        with open(DEBIAN_SECTION) as handle:
            self.section = json.load(handle)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def load(self, section):
        path = os.path.join(self.tmp.name, "goss-vars-debian.json")
        write_json(path, section)
        return render_goss_vars.load_debian_section(path)

    def test_shipped_section_is_accepted(self):
        self.assertEqual(self.load(self.section), self.section)

    def test_section_without_an_os_key_is_refused(self):
        for key in self.OS_KEYS:
            with self.subTest(key=key):
                section = copy.deepcopy(self.section)
                del section[key]
                with self.assertRaises(SystemExit) as raised:
                    self.load(section)
                self.assertIn(key, str(raised.exception.code))

    def test_section_without_a_provider_key_is_refused(self):
        for key in self.PROVIDER_KEYS:
            with self.subTest(key=key):
                section = copy.deepcopy(self.section)
                del section["qemu"][key]
                with self.assertRaises(SystemExit) as raised:
                    self.load(section)
                self.assertIn(f"qemu.{key}", str(raised.exception.code))


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name in render_goss_vars.CONFIG_FILES:
            write_json(os.path.join(self.tmp.name, f"{name}.json"), {})
        self.override = os.path.join(self.tmp.name, "v1.37.json")
        write_json(self.override, {
            "containerd_version": "2.1.4",
            "debian_version": "13",
            "kubernetes_cni_semver": "v1.7.1",
            "kubernetes_deb_version": "1.37.1-1.1",
            "kubernetes_semver": "v1.37.1",
            "ubuntu_version": "2604",
        })

    def render(self, image_os):
        result = subprocess.run(
            [sys.executable, SCRIPT, "--os", image_os, self.tmp.name, self.override],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def test_ubuntu_render_has_no_debian_section(self):
        rendered = self.render("ubuntu")
        self.assertEqual((rendered["OS"], rendered["OS_VERSION"]), ("ubuntu", "26.04"))
        self.assertNotIn("debian", rendered)

    def test_debian_render_carries_the_debian_section(self):
        rendered = self.render("debian")
        self.assertEqual((rendered["OS"], rendered["OS_VERSION"]), ("debian", "13"))
        with open(DEBIAN_SECTION) as handle:
            self.assertEqual(rendered["debian"], json.load(handle))


if __name__ == "__main__":
    unittest.main()
