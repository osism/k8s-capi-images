#!/usr/bin/env python3
"""Compare elements/k8s-capi with upstream kubernetes-sigs/image-builder.

The element does not vendor image-builder: extra-data.d clones it at the commit
pinned in environment.d and runs its Ansible roles unchanged in the DIB chroot,
so upstream changes only reach the images when that pin moves. Several parts of
the element mirror or work around upstream files, though, and those have to be
kept in step by hand. This script checks each of those coupling points between
the pinned commit and a target ref and prints a Markdown report.

It only reads upstream content (it never runs any of it) and never edits the
element. The upstream clone is kept in --workdir so the report's findings can
be followed up with plain git commands.
"""

import argparse
import difflib
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

try:
    import yaml
except ImportError:  # the matrix parser below covers the flat layout without it
    yaml = None

UPSTREAM_URL = "https://github.com/kubernetes-sigs/image-builder"
CAPI = "images/capi"
ROLES = f"{CAPI}/ansible/roles"

ELEMENT = "elements/k8s-capi"
ENV_FILE = f"{ELEMENT}/environment.d/10-k8s-capi.bash"
FETCH_FILE = f"{ELEMENT}/extra-data.d/10-fetch-image-builder"
ANSIBLE_FILE = f"{ELEMENT}/install.d/50-install-ansible"
RUN_FILE = f"{ELEMENT}/install.d/60-run-image-builder"
WRAPPER_FILE = f"{ELEMENT}/static/wrapper.yml"
KUBEADM_FILE = f"{ELEMENT}/static/kubeadm.yml.j2"

# Node var files the Makefile hands to Packer that only drive Packer itself;
# extra-data.d deliberately does not stage them.
PACKER_ONLY_VAR_FILES = {"ansible-args", "goss-args"}

# Name fragments of role files that belong to other distributions, providers
# or build targets. Only a hint for sorting the report: whether a file really
# never runs for Ubuntu on OpenStack is decided by its when/include condition.
OTHER_PLATFORM_TOKENS = (
    "alma", "amazon", "aws", "azure", "centos", "cloudstack", "fedora",
    "flatcar", "googlecompute", "gpu", "kubevirt", "maas", "mariner",
    "microsoft", "nutanix", "nvidia", "oci", "outscale", "photon", "ppc64le",
    "proxmox", "qemu", "raw", "redhat", "rhel", "rocky", "rpm", "suse",
    "vmware", "vsphere", "windows",
)

# Added role lines that touch what the chroot does not have: a running
# systemd, the image's own kernel, its own /proc and /sys, a reboot. Each hit
# needs a look at the shims in static/shims/ and the notes in 60-run-image-builder.
SHIM_SENSITIVE = re.compile(
    r"\bsystemctl\b|\b(?:ansible\.builtin\.)?(?:systemd|systemd_service|service):"
    r"|\bmodprobe\b|\bsysctl\b|\budevadm\b|\bjournalctl\b|\bfstrim\b"
    r"|\b(?:hostnamectl|timedatectl|localectl|loginctl|networkctl|resolvectl)\b"
    r"|\bswapoff\b|\bu?mount\b|\breboot\b|\bwait_for_connection\b|/proc/|/sys/"
)

# Packer template functions other than {{ user `x` }}; extra-data.d only
# rewrites user references, anything else would reach Ansible verbatim.
PACKER_FUNCTION = re.compile(
    r"\{\{\s*(?:env|isotime|timestamp|uuid|build_name|build_type|template_dir"
    r"|pwd|split|replace|lower|upper|clean_resource_name)\b"
)

ROLE_DEPENDENCY = (
    re.compile(r"^\s*-\s*role:\s*['\"]?([\w.-]+)", re.M),
    re.compile(r"(?:include_role|import_role):\s*\n\s*name:\s*['\"]?([\w.-]+)", re.M),
)

# Module calls such as "community.general.modprobe:" or "- ansible.posix.sysctl:".
MODULE_CALL = re.compile(r"^[\s-]*([a-z0-9_]+\.[a-z0-9_]+)\.[a-z0-9_]+:", re.M)

# Matrix keys the element takes from the overrides, which the sync workflow
# moves to the newest patch release on its own, and RPM-only keys.
SYNCED_KEYS = {"kubernetes_semver", "kubernetes_deb_version", "kubernetes_series"}
IGNORED_KEYS = {"kubernetes_rpm_version", "kubernetes_cni_rpm_version"}
# Only read by the kubernetes role's url.yml, i.e. when CNI is not installed
# from packages.
CNI_HTTP_KEYS = {"kubernetes_cni_semver", "kubernetes_cni_http_source"}


class Report:
    """Collects the Markdown body and a summary of the findings."""

    def __init__(self):
        self.body = []
        self.findings = []
        self.current = ""

    def section(self, title):
        self.current = title
        self.body += ["", f"## {title}", ""]

    def add(self, *lines):
        self.body.extend(lines)

    def finding(self, level, text):
        self.findings.append((level, self.current, text))
        self.body.append(f"- **{level}** {text}")

    def block(self, text, lang=""):
        self.body += ["", f"```{lang}", text.rstrip("\n"), "```", ""]


class Upstream:
    """Read-only access to a blobless clone of image-builder."""

    def __init__(self, path):
        self.path = path

    def git(self, *args, check=True):
        proc = subprocess.run(
            ["git", "-C", str(self.path), *args], capture_output=True, text=True, check=False
        )
        if check and proc.returncode != 0:
            sys.exit(f"ERROR: git {' '.join(args)}: {proc.stderr.strip()}")
        return proc

    def out(self, *args):
        return self.git(*args).stdout

    def show(self, ref, path):
        proc = self.git("show", f"{ref}:{path}", check=False)
        return proc.stdout if proc.returncode == 0 else None

    def commit(self, ref):
        # Remote branches first: the local "main" of the clone is never updated.
        for candidate in (f"refs/remotes/origin/{ref}", f"refs/tags/{ref}", ref):
            proc = self.git(
                "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}", check=False
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
        return None

    def date(self, sha):
        return self.out("show", "-s", "--format=%cs", sha).strip()

    def describe(self, sha):
        for args in (("--exact-match",), ()):
            proc = self.git("describe", "--tags", *args, sha, check=False)
            if proc.returncode == 0:
                return proc.stdout.strip()
        return "untagged"

    def is_ancestor(self, older, newer):
        proc = self.git("merge-base", "--is-ancestor", older, newer, check=False)
        return proc.returncode == 0

    def names(self, ref, path):
        listing = self.out("ls-tree", "--name-only", ref, f"{path}/")
        return [pathlib.PurePosixPath(p).name for p in listing.splitlines()]

    def files(self, ref, path):
        return self.out("ls-tree", "-r", "--name-only", ref, "--", path).splitlines()

    def log(self, old, new, *paths):
        return self.out(
            "log", "--no-merges", "--date=short", "--format=%h %ad %s",
            f"{old}..{new}", "--", *paths,
        ).splitlines()

    def diff(self, old, new, *paths, context=3):
        return self.out("diff", f"-U{context}", old, new, "--", *paths)

    def references(self, ref, word, path):
        proc = self.git("grep", "-c", "-w", word, ref, "--", path, check=False)
        return sum(int(line.rsplit(":", 1)[1]) for line in proc.stdout.splitlines())


def open_upstream(workdir):
    if workdir.exists() and any(workdir.iterdir()):
        upstream = Upstream(workdir)
        url = upstream.git("remote", "get-url", "origin", check=False).stdout.strip()
        if url.removesuffix(".git") != UPSTREAM_URL:
            sys.exit(f"ERROR: {workdir} is not a clone of {UPSTREAM_URL} (origin: {url or 'none'})")
        upstream.git("fetch", "--quiet", "--tags", "--force", "--prune", "origin")
        return upstream
    workdir.parent.mkdir(parents=True, exist_ok=True)
    # Blobless: history and trees now, file contents when they are first read.
    proc = subprocess.run(
        ["git", "clone", "--quiet", "--filter=blob:none", UPSTREAM_URL, str(workdir)],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        sys.exit(f"ERROR: cloning {UPSTREAM_URL} failed: {proc.stderr.strip()}")
    return Upstream(workdir)


def repo_root():
    here = pathlib.Path(__file__).resolve().parent
    proc = subprocess.run(
        ["git", "-C", str(here), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return pathlib.Path(proc.stdout.strip())


def latest_release_tag(upstream):
    tags = upstream.out("tag", "--list", "v*", "--sort=-v:refname").splitlines()
    return next((t for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+", t)), None)


def load_json(text):
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return None


def normalize(value):
    # Same normalization extra-data.d applies before the values reach Ansible.
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"\{\{\s*user\s*`([A-Za-z0-9_]+)`\s*\}\}", r"{{ \1 }}", value)
    return value


def short(value, limit=80):
    text = json.dumps(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def version_tuple(version):
    return tuple(int(p) for p in re.findall(r"\d+", version))


def satisfies(version, spec):
    """Evaluate a simple ansible-galaxy constraint; None when it cannot be parsed."""
    if spec in ("", "*"):
        return True
    for part in spec.split(","):
        match = re.fullmatch(r"\s*(<=|>=|==|!=|<|>)?\s*([\d.]+)\s*", part)
        if not match:
            return None
        op, bound = match.group(1) or "==", version_tuple(match.group(2))
        have = version_tuple(version)
        ok = {
            "<=": have <= bound, ">=": have >= bound, "==": have == bound,
            "!=": have != bound, "<": have < bound, ">": have > bound,
        }[op]
        if not ok:
            return False
    return True


def other_platform(path):
    inside_role = path.split("/roles/", 1)[-1].split("/", 1)[-1]
    tokens = [t for t in re.split(r"[-_./]", inside_role.lower()) if t]
    return any(t.startswith(OTHER_PLATFORM_TOKENS) for t in tokens)


def role_closure(upstream, ref, roots):
    seen, todo = [], list(roots)
    while todo:
        role = todo.pop(0)
        if role in seen:
            continue
        seen.append(role)
        for path in upstream.files(ref, f"{ROLES}/{role}"):
            if path.endswith((".yml", ".yaml")):
                text = upstream.show(ref, path) or ""
                for pattern in ROLE_DEPENDENCY:
                    todo += [r for r in pattern.findall(text) if r not in seen]
    return [r for r in seen if upstream.files(ref, f"{ROLES}/{r}")]


def added_lines(diff_text):
    path, lineno = None, 0
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            lineno = int(re.search(r"\+(\d+)", line).group(1))
        elif line.startswith("+") and path:
            yield path, lineno, line[1:]
            lineno += 1


def makefile_node_var_files(text):
    match = re.search(r"^COMMON_NODE_VAR_FILES\s*:?=((?:[^\n]*\\\n)*[^\n]*)", text or "", re.M)
    return re.findall(r"packer/config/([\w.-]+)\.json", match.group(1)) if match else None


def ansible_common_vars(text):
    data = load_json(text) or {}
    pairs = re.findall(r"(\w+)=\"?\{\{\s*user\s*`(\w+)`\s*\}\}", data.get("ansible_common_vars", ""))
    return dict(pairs)


def galaxy_collections(text):
    match = re.search(r"ansible-galaxy\"?\s+collection\s+install((?:[^\n]*\\\n)*[^\n]*)", text or "")
    result = {}
    for token in (match.group(1).replace("\\\n", " ").split() if match else []):
        name, _, spec = token.strip("'\"").partition(":")
        if re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", name):
            result[name] = spec or "*"
    return result


def parse_matrix(text):
    if not text:
        return {}
    if yaml is not None:
        return (yaml.safe_load(text) or {}).get("releasePins", {}) or {}
    pins, current = {}, None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        series = re.match(r'^  "?([\d.]+)"?:\s*$', line)
        value = re.match(r'^    (\w+):\s*"?([^"]*)"?\s*$', line)
        if series:
            current = pins.setdefault(series.group(1), {})
        elif value and current is not None:
            current[value.group(1)] = value.group(2)
        elif not line.startswith(" "):
            current = None
    return pins


class Comparison:
    def __init__(self, repo, upstream, pin, target, offline):
        self.repo = repo
        self.up = upstream
        self.pin = pin
        self.target = target
        self.offline = offline
        self.report = Report()
        self.element = {
            name: (repo / path).read_text()
            for name, path in {
                "env": ENV_FILE, "fetch": FETCH_FILE, "ansible": ANSIBLE_FILE,
                "run": RUN_FILE, "wrapper": WRAPPER_FILE, "kubeadm": KUBEADM_FILE,
            }.items()
        }
        self.overrides = {
            path.name: json.loads(path.read_text())
            for path in sorted((repo / "overrides").glob("*.json"))
        }
        self.wrapper_roles = re.findall(
            r"include_role:\s*\n\s*name:\s*([\w.-]+)", self.element["wrapper"]
        )
        self.roles = role_closure(upstream, target, self.wrapper_roles)
        self.staged_files = re.search(
            r"for f in (.*?); do", self.element["fetch"], re.S
        ).group(1).replace("\\\n", " ").split()
        self.staged = self.staged_values(target)
        self.extra_vars = [
            name for name in dict.fromkeys(
                re.findall(r"-e\s+'?([A-Za-z_]\w*)=", self.element["run"])
                + re.findall(r"-e\s+'\{\"(\w+)\"", self.element["run"])
            )
            if name != "ansible_python_interpreter"
        ]
        self.override_keys = {k for data in self.overrides.values() for k in data}

    def staged_values(self, ref):
        values = {}
        for name in self.staged_files:
            data = load_json(self.up.show(ref, f"{CAPI}/packer/config/{name}.json")) or {}
            values.update({k: normalize(v) for k, v in data.items()})
        return values

    def coverage_gaps(self, ref, common_vars, builder_vars):
        """Ansible vars Packer sets to a non-empty value that the element does not provide."""
        staged = self.staged_values(ref)
        provided = set(staged) | set(self.extra_vars) | self.override_keys
        gaps = {}
        for var, source in common_vars.items():
            value = staged.get(source, builder_vars.get(source))
            if var not in provided and value not in (None, ""):
                gaps[var] = (source, value)
        return gaps

    # -- individual checks -------------------------------------------------

    def check_node_play(self):
        r = self.report
        r.section("Play: images/capi/ansible/node.yml vs static/wrapper.yml")
        diff = self.up.diff(self.pin, self.target, f"{CAPI}/ansible/node.yml")
        if diff:
            r.finding("ACTION", "node.yml changed upstream; static/wrapper.yml mirrors its play "
                      "header and role order, so carry the change over:")
            r.block(diff, "diff")
        else:
            r.finding("OK", "node.yml is unchanged; static/wrapper.yml still mirrors it.")

    def check_roles(self):
        r = self.report
        r.section("Roles run in the chroot")
        r.add(f"wrapper.yml includes {', '.join(self.wrapper_roles)}; with their dependencies "
              f"at the target that is: {', '.join(self.roles)}.", "")
        old_roles = set(self.up.names(self.pin, ROLES))
        new_roles = set(self.up.names(self.target, ROLES))
        for role in sorted(new_roles - old_roles):
            used = "and the chroot run pulls it in" if role in self.roles else "not used by the chroot run"
            r.finding("REVIEW" if role in self.roles else "INFO", f"New upstream role `{role}` ({used}).")
        for role in sorted(old_roles - new_roles):
            r.finding("ACTION" if role in self.wrapper_roles else "INFO", f"Upstream removed role `{role}`.")
        roles_at_pin = role_closure(self.up, self.pin, self.wrapper_roles)
        for role in self.roles:
            if role not in roles_at_pin:
                r.finding("REVIEW", f"`{role}` became a dependency of the chroot run.")

        paths = [f"{ROLES}/{role}" for role in self.roles]
        status = self.up.out("diff", "--name-status", self.pin, self.target, "--", *paths).splitlines()
        relevant = []
        if status:
            r.add("", "| Status | File | Hint |", "|---|---|---|")
            for line in status:
                code, *names = line.split("\t")
                path = names[-1]
                if other_platform(path):
                    hint = "other platform (check its `when`)"
                else:
                    hint = "**Ubuntu/OpenStack path**"
                    relevant.append(path)
                r.add(f"| {code} | `{path.removeprefix(ROLES + '/')}` | {hint} |")
            r.add("")
            r.finding("REVIEW", f"{len(relevant)} of {len(status)} changed role files are on the "
                      "Ubuntu/OpenStack path; read their diffs against the chroot constraints.")
        else:
            r.finding("OK", "No role file of the chroot run changed.")

        hits = [
            (path, lineno, text.strip())
            for path, lineno, text in added_lines(self.up.diff(self.pin, self.target, *relevant, context=0))
            if SHIM_SENSITIVE.search(text)
        ] if relevant else []
        if hits:
            r.finding("REVIEW", "Added lines that touch systemd, kernel modules, sysctl, mounts, "
                      "/proc or /sys; check them against static/shims/ and the chroot notes:")
            for path, lineno, text in hits:
                r.add(f"  - `{path.removeprefix(ROLES + '/')}:{lineno}`: `{text[:140]}`")

        installed = galaxy_collections(self.element["ansible"])
        used = set()
        for role in self.roles:
            for path in self.up.files(self.target, f"{ROLES}/{role}"):
                if path.endswith((".yml", ".yaml")) and not other_platform(path):
                    used.update(MODULE_CALL.findall(self.up.show(self.target, path) or ""))
        missing = used - set(installed) - {"ansible.builtin", "ansible.legacy"}
        for collection in sorted(missing):
            r.finding("ACTION", f"The roles call modules from `{collection}`, which "
                      "install.d/50-install-ansible does not install.")

    def check_var_files(self):
        r = self.report
        r.section("Config files staged from packer/config/")
        makefile = self.up.show(self.target, f"{CAPI}/Makefile")
        upstream_files = makefile_node_var_files(makefile)
        if upstream_files is None:
            r.finding("REVIEW", "COMMON_NODE_VAR_FILES not found in the target Makefile; "
                      "check how upstream now assembles the node var files.")
        else:
            expected = [f for f in upstream_files if f not in PACKER_ONLY_VAR_FILES]
            added = sorted(set(expected) - set(self.staged_files))
            dropped = sorted(set(self.staged_files) - set(expected))
            for name in added:
                r.finding("ACTION", f"Upstream passes `packer/config/{name}.json` to node builds; "
                          "add it to the copy loop in extra-data.d and the -e list in 60-run-image-builder.")
            for name in dropped:
                r.finding("ACTION", f"Upstream no longer passes `packer/config/{name}.json`; "
                          "extra-data.d still copies it.")
            if not added and not dropped:
                r.finding("OK", f"extra-data.d stages the same node var files: {', '.join(self.staged_files)}.")

        for name in self.staged_files:
            path = f"{CAPI}/packer/config/{name}.json"
            old = load_json(self.up.show(self.pin, path)) or {}
            new_text = self.up.show(self.target, path)
            if new_text is None:
                r.finding("ACTION", f"`{path}` no longer exists; the copy in extra-data.d would fail.")
                continue
            new = load_json(new_text) or {}
            changes = []
            for key in sorted(set(old) | set(new)):
                if old.get(key, "<unset>") != new.get(key, "<unset>"):
                    note = " (set by overrides/, so not used)" if key in self.override_keys else ""
                    changes.append(f"  - `{key}`: {short(old.get(key, '<unset>'))} -> "
                                   f"{short(new.get(key, '<unset>'))}{note}")
                    if PACKER_FUNCTION.search(str(new.get(key, ""))) and not PACKER_FUNCTION.search(str(old.get(key, ""))):
                        r.finding("ACTION", f"`{name}.json` `{key}` now uses a Packer function that "
                                  f"extra-data.d does not translate: {short(new[key])}")
            if changes:
                r.finding("INFO", f"`{name}.json` values change (arrive with the pin bump):")
                r.add(*changes)

    def check_packer_vars(self):
        r = self.report
        r.section("Variables Packer passes to Ansible")
        path = f"{CAPI}/packer/config/ansible-args.json"
        old = ansible_common_vars(self.up.show(self.pin, path))
        new = ansible_common_vars(self.up.show(self.target, path))
        for var in sorted(set(new) - set(old)):
            r.finding("REVIEW", f"ansible_common_vars adds `{var}` (from Packer var `{new[var]}`).")
        for var in sorted(set(old) - set(new)):
            r.finding("REVIEW", f"ansible_common_vars drops `{var}`.")
        for var in sorted(set(old) & set(new)):
            if old[var] != new[var]:
                r.finding("REVIEW", f"`{var}` is now fed from Packer var `{new[var]}` (was `{old[var]}`).")

        builder = f"{CAPI}/packer/openstack/packer.json"
        old_builder = load_json(self.up.show(self.pin, builder)) or {}
        new_builder = load_json(self.up.show(self.target, builder)) or {}
        old_bvars, new_bvars = old_builder.get("variables", {}), new_builder.get("variables", {})
        sources = {u: a for a, u in new.items()}
        for key in sorted(set(old_bvars) | set(new_bvars)):
            if key in sources and old_bvars.get(key) != new_bvars.get(key):
                r.finding("REVIEW", f"The OpenStack builder changes `{key}` (Ansible `{sources[key]}`): "
                          f"{short(old_bvars.get(key, '<unset>'))} -> {short(new_bvars.get(key, '<unset>'))}. "
                          "60-run-image-builder passes the builder's values by hand.")

        known = self.coverage_gaps(self.pin, old, old_bvars)
        for var, (source, value) in sorted(self.coverage_gaps(self.target, new, new_bvars).items()):
            r.finding("INFO" if var in known else "REVIEW",
                      f"{'Known gap' if var in known else 'New gap'}: Packer sets `{var}` from `{source}` = "
                      f"{short(value)}, which the element neither stages under that name nor passes with -e.")

        def provisioner(builder_json):
            return next((p for p in builder_json.get("provisioners", []) if p.get("type") == "ansible"), {})

        old_prov, new_prov = provisioner(old_builder), provisioner(new_builder)
        for key in ("extra_arguments", "playbook_file", "ansible_env_vars"):
            if old_prov.get(key) != new_prov.get(key):
                r.finding("REVIEW", f"The OpenStack builder's ansible provisioner changes `{key}`: "
                          f"{short(old_prov.get(key), 200)} -> {short(new_prov.get(key), 200)}")

        r.add("", "Extra vars install.d/60-run-image-builder passes itself "
              "(references in images/capi/ansible, pin -> target):")
        for var in self.extra_vars:
            before = self.up.references(self.pin, var, f"{CAPI}/ansible")
            after = self.up.references(self.target, var, f"{CAPI}/ansible")
            if after == 0:
                r.finding("REVIEW", f"`{var}` is no longer referenced by the roles; its `-e` is "
                          f"probably obsolete (was referenced {before}x).")
            else:
                r.add(f"  - `{var}`: {before} -> {after}")

    def check_ansible(self):
        r = self.report
        r.section("ansible-core, collections and ansible.cfg")
        utils = f"{CAPI}/hack/utils.sh"
        versions = {}
        for label, ref in (("pin", self.pin), ("target", self.target)):
            text = self.up.show(ref, utils) or ""
            match = re.search(r'_version_ansible_core="([0-9.]+)"', text)
            note = re.search(r"#\s*Note: ansible-core[^\n]*", text)
            versions[label] = (match.group(1) if match else None, note.group(0).lstrip("# ") if note else "")
        if versions["target"][0] is None:
            r.finding("ACTION", "extra-data.d can no longer detect the ansible-core version in "
                      "hack/utils.sh; the build would fail at the staging step.")
        elif versions["pin"][0] != versions["target"][0]:
            r.finding("REVIEW", f"ansible-core {versions['pin'][0]} -> {versions['target'][0]} "
                      f"(extra-data.d picks it up). {versions['target'][1]} Check the collection pins "
                      "and the interpreter notes in install.d/50 and 60 against it.")
        else:
            r.finding("OK", f"ansible-core stays at {versions['target'][0]}.")

        ensure = f"{CAPI}/hack/ensure-ansible.sh"
        old = galaxy_collections(self.up.show(self.pin, ensure))
        new = galaxy_collections(self.up.show(self.target, ensure))
        ours = dict(re.findall(r"'([a-z0-9_]+\.[a-z0-9_]+):==([\d.]+)'", self.element["ansible"]))
        r.add("", "| Collection | Upstream at pin | Upstream at target | Element |", "|---|---|---|---|")
        for name in sorted(set(old) | set(new) | set(ours)):
            r.add(f"| {name} | {old.get(name, '-')} | {new.get(name, '-')} | {ours.get(name, '-')} |")
        r.add("")
        for name, version in ours.items():
            verdict = satisfies(version, new.get(name, "*"))
            if verdict is False:
                r.finding("ACTION", f"`{name}=={version}` does not satisfy upstream's `{new[name]}`.")
            elif verdict is None:
                r.finding("REVIEW", f"Cannot evaluate upstream's constraint `{new.get(name)}` for `{name}`.")
            if old.get(name) != new.get(name):
                r.finding("REVIEW", f"Upstream changed its `{name}` constraint: "
                          f"{old.get(name, '-')} -> {new.get(name, '-')}.")

        cfg = self.up.diff(self.pin, self.target, f"{CAPI}/ansible.cfg")
        if cfg:
            r.finding("REVIEW", "ansible.cfg changed (it is staged as is):")
            r.block(cfg, "diff")
        else:
            r.finding("OK", "ansible.cfg is unchanged.")

    def check_kubeadm_template(self):
        r = self.report
        r.section("kubeadm pre-pull template (static/kubeadm.yml.j2)")

        def body(text):
            lines = [line for line in (text or "").splitlines() if not line.startswith("#")]
            return "\n".join(lines).strip() + "\n"

        path = f"{ROLES}/kubernetes/templates/etc/kubeadm.yml"
        ours = body(self.element["kubeadm"])
        at_pin, at_target = body(self.up.show(self.pin, path)), body(self.up.show(self.target, path))
        if at_pin == ours:
            r.finding("ACTION", "The template at the pinned commit already matches static/kubeadm.yml.j2; "
                      "drop the copy and the kubeadm_template extra var now.")
        elif at_target == ours:
            r.finding("ACTION", "Upstream's template at the target matches static/kubeadm.yml.j2: with the "
                      "pin bump drop the file, its staging in extra-data.d and the kubeadm_template -e "
                      "in 60-run-image-builder, and the notes in README.rst.")
        else:
            r.finding("OK" if at_pin == at_target else "REVIEW",
                      "The workaround is still needed; upstream's template at the target differs:")
            r.block("".join(difflib.unified_diff(
                at_target.splitlines(True), ours.splitlines(True),
                "upstream (target)", "static/kubeadm.yml.j2")), "diff")

    def check_containerd(self):
        r = self.report
        r.section("containerd.service allowlist (install.d/60-run-image-builder)")
        path = f"{CAPI}/packer/config/containerd.json"
        old = load_json(self.up.show(self.pin, path)) or {}
        new = load_json(self.up.show(self.target, path)) or {}
        for key in ("containerd_version", "runc_version"):
            if old.get(key) != new.get(key):
                r.finding("INFO", f"`{key}`: {old.get(key)} -> {new.get(key)}")
        versions = {new.get("containerd_version")} | {
            data["containerd_version"] for data in self.overrides.values() if "containerd_version" in data
        }
        url = re.search(r"containerd_service_url=([^']+)'", self.element["run"])
        allowlist = set(re.findall(r"^\s*([0-9a-f]{64})\)", self.element["run"], re.M))
        for version in sorted(v for v in versions if v):
            if self.offline or not url:
                r.finding("REVIEW", f"containerd {version}: unit hash not checked (offline or no URL).")
                continue
            unit_url = re.sub(r"\{\{\s*containerd_version\s*\}\}", version, url.group(1))
            try:
                with urllib.request.urlopen(unit_url, timeout=30) as response:
                    digest = hashlib.sha256(response.read()).hexdigest()
            except (urllib.error.URLError, TimeoutError) as err:
                r.finding("REVIEW", f"containerd {version}: could not fetch {unit_url}: {err}")
                continue
            if digest in allowlist:
                r.finding("OK", f"containerd {version}: containerd.service ({digest[:12]}) is in the allowlist.")
            else:
                r.finding("ACTION", f"containerd {version}: containerd.service sha256 {digest} is not in the "
                          "allowlist; review the upstream unit, then extend the case in 60-run-image-builder.")

        defaults = self.up.show(self.target, f"{ROLES}/containerd/defaults/main.yml") or ""
        match = re.search(r"^containerd_service_template_versions:\s*\n((?:\s+-.*\n)+)", defaults, re.M)
        if match:
            bundled = re.findall(r"-\s*\"?([\d.]+)", match.group(1))
            r.finding("REVIEW", "Upstream can render containerd.service from a bundled template "
                      f"(for containerd {', '.join(bundled)}) when containerd_service_url is empty. "
                      "The element still passes the URL, so the download and the sha256 gate stay in "
                      "effect; decide whether to switch to the template.")

    def check_ubuntu(self):
        r = self.report
        r.section("Ubuntu bases")

        def builds(ref):
            openstack = {m.group(1) for n in self.up.names(ref, f"{CAPI}/packer/openstack")
                         if (m := re.fullmatch(r"ubuntu-(\d{4})\.json", n))}
            qemu = {m.group(1) for n in self.up.names(ref, f"{CAPI}/packer/qemu")
                    if (m := re.fullmatch(r"qemu-ubuntu-(\d{4})(?:-[\w.-]+)?\.json", n))}
            return openstack, qemu

        (old_os, old_qemu), (new_os, new_qemu) = builds(self.pin), builds(self.target)
        ours = {}
        for name, data in self.overrides.items():
            ours.setdefault(data.get("ubuntu_version"), []).append(data.get("kubernetes_series", name))
        r.add(f"Upstream OpenStack builds at the target: {', '.join(sorted(new_os)) or '-'}; "
              f"QEMU builds: {', '.join(sorted(new_qemu)) or '-'}.", "")
        for version in sorted((new_os | new_qemu) - (old_os | old_qemu)):
            r.finding("INFO", f"Upstream adds Ubuntu {version} builds.")
        if set(ours) <= new_os:
            r.finding("OK", f"Upstream builds every Ubuntu base in use ({', '.join(sorted(ours))}) for OpenStack.")
        for version, series in sorted(ours.items()):
            where = ", ".join(series)
            if version not in new_os:
                r.finding("REVIEW", f"Ubuntu {version} ({where}) has no upstream OpenStack build at the target.")
            diff = self.up.diff(self.pin, self.target, f"{CAPI}/packer/openstack/ubuntu-{version}.json")
            if diff:
                r.finding("INFO", f"packer/openstack/ubuntu-{version}.json changed ({where}):")
                r.block(diff, "diff")

    def check_series(self):
        r = self.report
        r.section("Kubernetes series and per-series dependency pins")
        path = f"{CAPI}/packer/config/kubernetes-version-matrix.yaml"
        pins = {str(k): v for k, v in parse_matrix(self.up.show(self.target, path)).items()}
        if not pins:
            r.finding("INFO", "Upstream has no kubernetes-version-matrix.yaml at the target.")
            return
        if self.up.show(self.pin, path) is None:
            r.finding("INFO", "kubernetes-version-matrix.yaml is new since the pin: upstream now pins "
                      "crictl, CNI, containerd and runc per Kubernetes minor.")
        ours = {data["kubernetes_series"].lstrip("v"): data for data in self.overrides.values()
                if "kubernetes_series" in data}
        for minor in sorted(pins, key=version_tuple):
            if minor not in ours and version_tuple(minor) > max(map(version_tuple, ours)):
                r.finding("INFO", f"Upstream pins a newer series v{minor} than overrides/ has.")
        r.add("", "| Series | Key | Upstream pin | Element |", "|---|---|---|---|")
        cni_from_packages = self.staged.get("kubernetes_cni_source_type") == "pkg"
        drift = []
        for minor, data in sorted(ours.items(), key=lambda item: version_tuple(item[0])):
            entry = pins.get(minor)
            if entry is None:
                r.add(f"| v{minor} | - | no upstream pin | - |")
                continue
            for key, value in sorted(entry.items()):
                if key in IGNORED_KEYS or (key in CNI_HTTP_KEYS and cni_from_packages):
                    continue
                have = data.get(key, self.staged.get(key)) or "<unpinned>"
                if str(have) != str(value):
                    source = "override" if key in data else "config default"
                    r.add(f"| v{minor} | {key} | {value} | {have} ({source}) |")
                    if key not in SYNCED_KEYS:
                        drift.append(f"v{minor} {key}")
        r.add("")
        if drift:
            r.finding("REVIEW", "The element builds with other dependency versions than upstream pins "
                      f"for these series: {', '.join(drift)}.")
        else:
            r.finding("OK", "Apart from Kubernetes patch versions (kept current by the sync workflow), "
                      "the element uses upstream's per-series pins.")

    def check_goss(self):
        r = self.report
        r.section("goss specs (osism/k8s-capi-images#338)")
        commits = self.up.log(self.pin, self.target, f"{CAPI}/packer/goss")
        if commits:
            r.finding("INFO", f"{len(commits)} commits change the goss specs; relevant once goss "
                      "validation is adopted:")
            r.add(*(f"  - {c}" for c in commits))
        else:
            r.finding("OK", "goss specs are unchanged.")

    def check_commits(self):
        r = self.report
        r.section("Upstream commits on paths the element depends on")
        paths = [f"{CAPI}/ansible/node.yml", f"{CAPI}/ansible.cfg", f"{CAPI}/packer/config",
                 f"{CAPI}/hack/utils.sh", f"{CAPI}/hack/ensure-ansible.sh", f"{CAPI}/packer/openstack",
                 *(f"{ROLES}/{role}" for role in self.roles)]
        commits = self.up.log(self.pin, self.target, *paths)
        r.add(*[f"- {c}" for c in commits[:100]] or ["- none"])
        if len(commits) > 100:
            r.add(f"- ... and {len(commits) - 100} more")
        return len(commits)

    def run(self, header):
        for check in (self.check_node_play, self.check_roles, self.check_var_files,
                      self.check_packer_vars, self.check_ansible, self.check_kubeadm_template,
                      self.check_containerd, self.check_ubuntu, self.check_series, self.check_goss):
            check()
        watched = self.check_commits()
        lines = header + [f"Commits touching the paths above: {watched}.", "", "## Summary", ""]
        important = [f for f in self.report.findings if f[0] in ("ACTION", "REVIEW")]
        if important:
            lines += ["| Level | Area | Finding |", "|---|---|---|"]
            lines += [f"| {level} | {area} | {text.splitlines()[0].rstrip(':')} |"
                      for level, area, text in sorted(important, key=lambda f: f[0])]
        else:
            lines.append("No ACTION or REVIEW findings: moving the pin to the target needs no other "
                         "change to the element.")
        return "\n".join(lines + self.report.body) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", help="upstream ref to compare against (tag, branch or SHA); "
                        "default: the newest release tag, or main when the pin already contains it")
    parser.add_argument("--pin", help="image-builder commit to compare from; default: the one in environment.d")
    parser.add_argument("--workdir", type=pathlib.Path,
                        default=pathlib.Path.home() / ".cache" / "k8s-capi-images" / "image-builder",
                        help="where the blobless upstream clone is kept (default: %(default)s)")
    parser.add_argument("--offline", action="store_true",
                        help="skip downloading containerd.service for the allowlist check")
    args = parser.parse_args()

    repo = repo_root()
    pin_ref = args.pin or re.search(
        r"DIB_K8S_IMAGE_BUILDER_REF:-([0-9a-f]{40})", (repo / ENV_FILE).read_text()
    ).group(1)
    upstream = open_upstream(args.workdir.expanduser())

    pin = upstream.commit(pin_ref) or sys.exit(f"ERROR: {pin_ref} is not a commit in {UPSTREAM_URL}")
    tag = latest_release_tag(upstream)
    tag_sha = upstream.commit(tag) if tag else None
    main_sha = upstream.commit("main")
    if args.target:
        target_name, why = args.target, "requested"
    elif tag_sha and not upstream.is_ancestor(tag_sha, pin):
        target_name, why = tag, "newest release tag"
    else:
        target_name = "main"
        why = f"the pin already contains {tag}, so this previews what main has that no release has yet"
    target = upstream.commit(target_name) or sys.exit(f"ERROR: unknown upstream ref {target_name}")

    # A detached checkout makes git fetch the target's blobs in one batch, and
    # leaves the target in the working tree for reading; the diff does the same
    # for what the pin has on top.
    upstream.git("checkout", "--quiet", "--detach", target, check=False)
    upstream.git("diff", "--stat", pin, target, "--", CAPI)

    rows = [("Pinned (environment.d)", upstream.describe(pin), pin)]
    rows += [("Newest release tag", tag, tag_sha)] if tag_sha else []
    rows += [("main", "origin/main", main_sha), ("**Target**", target_name, target)]
    header = ["# image-builder upstream comparison", "",
              "| | Ref | Commit | Date |", "|---|---|---|---|"]
    header += [f"| {label} | {ref} | `{sha[:12]}` | {upstream.date(sha)} |" for label, ref, sha in rows]
    total = len(upstream.log(pin, target))
    header += ["", f"Target: `{target_name}` ({why}).",
               f"Upstream clone: `{upstream.path}`; drill down with "
               f"`git -C {upstream.path} diff {pin[:12]} {target[:12]} -- <path>`.",
               f"Commits pin..target (without merges): {total}."]
    if not upstream.is_ancestor(pin, target):
        header.append("**Warning:** the target does not contain the pinned commit; the diffs "
                      "include changes that go backwards.")

    print(Comparison(repo, upstream, pin, target, args.offline).run(header), end="")


if __name__ == "__main__":
    main()
