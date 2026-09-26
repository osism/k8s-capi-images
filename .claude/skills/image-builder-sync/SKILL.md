---
name: image-builder-sync
description: Compare the k8s-capi diskimage-builder element (elements/k8s-capi) with the current state of upstream kubernetes-sigs/image-builder and report what changed upstream since the pinned commit and what the element has to adapt. Covers wrapper.yml vs node.yml, the staged packer/config files, the variables Packer passes to Ansible, ansible-core and collection pins, the kubeadm template workaround, the containerd.service hash allowlist, the chroot shims, the Ubuntu bases and upstream's per-series dependency pins. Use when checking for upstream image-builder changes, before bumping DIB_K8S_IMAGE_BUILDER_REF, or when asked whether the element is still in sync with image-builder.
argument-hint: "[upstream ref: tag, branch or SHA; default newest release, else main]"
---

# Compare elements/k8s-capi with upstream image-builder

The element does not vendor image-builder. `extra-data.d/10-fetch-image-builder`
clones it at the commit SHA in `environment.d/10-k8s-capi.bash`
(`DIB_K8S_IMAGE_BUILDER_REF`) and runs its roles unchanged in the DIB chroot.
Upstream changes therefore reach the images only when that pin moves. Some
parts of the element copy, mirror or work around upstream files, and those
have to be kept in step by hand:

| Upstream (`images/capi/...`) | Element counterpart |
|---|---|
| `ansible/node.yml` | `static/wrapper.yml` mirrors its play header and role order |
| `ansible/roles/{setup,node,providers,containerd,kubernetes,sysprep}` | run unchanged in the chroot, made to work by `static/shims/` and the notes in `install.d/60-run-image-builder` |
| `Makefile` `COMMON_NODE_VAR_FILES` | copy loop in `extra-data.d` and `-e @config/...` list in `install.d/60` |
| `packer/config/ansible-args.json`, `packer/openstack/packer.json` | extra vars `install.d/60` passes by hand (`packer_builder_type`, `containerd_service_url`, ...) |
| `hack/utils.sh`, `hack/ensure-ansible.sh` | ansible-core (detected automatically) and collection pins in `install.d/50-install-ansible` |
| `ansible/roles/kubernetes/templates/etc/kubeadm.yml` | `static/kubeadm.yml.j2` (v1beta4 workaround) |
| containerd version in `packer/config/containerd.json` | sha256 allowlist of `containerd.service` in `install.d/60` |
| `packer/config/kubernetes-version-matrix.yaml` | `overrides/*.json` plus config defaults |
| `packer/goss/` | cloned at the pin by `playbooks/validate.yml`; `goss-vars.yaml` `common_debs` and the `ubuntu.qemu` section are mirrored for Debian in `scripts/goss-vars-debian.json` |
| `ansible/roles/node/defaults/main.yml` `common_virt_debs`, `sysctl_conf_file` | Debian extra vars in `install.d/60` |
| `ansible/roles/providers/tasks/openstack.yml` package list | the Debian `include_role` `packages` param in `static/wrapper.yml`; no other providers task on the openstack path may read `packages` |
| `ansible/roles/node/tasks/main.yml` rp_filter task | the `static/wrapper.yml` rp_filter task (Ubuntu >= 26 and Debian) |

## 1. Run the comparison

From the repository root:

```bash
python3 .claude/skills/image-builder-sync/scripts/compare.py
```

If the skill was invoked with an argument, pass it as `--target "$ARGUMENTS"`.

- Without `--target`, the target is the newest release tag. If the pin already
  contains that tag, the script falls back to `main` and says so: that run
  previews what upstream has merged but not yet released.
- `--pin <sha>` compares from another commit than the one in `environment.d`,
  for example to evaluate a candidate before editing anything.
- `--offline` skips downloading `containerd.service` for the hash check.
- `--workdir` sets where the blobless upstream clone is kept (default
  `~/.cache/k8s-capi-images/image-builder`). The clone is reused and fetched on
  every run, and it is left checked out at the target.

The script only reads. It prints a Markdown report with a summary table first.
Findings have one of four levels:

- **ACTION**: the element has to change when the pin moves to the target.
- **REVIEW**: the script cannot decide; you have to read the change.
- **INFO**: arrives with the pin bump, or is only context.
- **OK**: checked, nothing to do.

## 2. Work through the findings

Do not relay the report as it is. The script finds the coupling points; you
decide what each change means for a build in a DIB chroot. Use the clone path
and the `git -C <clone> diff <pin> <target> -- <path>` command from the
report's header to read every change behind an ACTION or REVIEW finding. Use
`gh release view <tag> -R kubernetes-sigs/image-builder` for release notes.

### Changed role files

Read the diff of every file the report marks as **Ubuntu/OpenStack path**.
Before you set aside a file marked "other platform", check its `when:` or the
include that pulls it in. The filename heuristic is only a hint. The element
runs with `packer_builder_type=openstack` on Ubuntu and Debian (both Debian
`os_family`).

Judge each change against how the chroot differs from the booted VM that
image-builder expects. The element's `README.rst` and the comments in the
hook scripts explain each point:

- **No running systemd.** `static/shims/systemctl` performs
  `enable`/`disable`/`mask` offline, makes `show` fail so Ansible's systemd
  module falls back to `is-enabled`, keeps the real exit code of `is-enabled`,
  and turns lifecycle verbs into no-ops. Check new `systemctl` verbs, new
  `systemd`/`service` module parameters, and tasks that read a live service
  state (`is-active`, `status` output, `register` plus `failed_when`) against
  that behaviour.
- **Host kernel, image modules.** `/proc`, `/sys` and `uname -r` belong to the
  build host, while `/lib/modules` holds the image's kernel. `modprobe`,
  `sysctl`, `udevadm`, `journalctl` and `fstrim` are no-op shims, and
  `install.d/60` stubs `modules.builtin` for `community.general.modprobe`.
  Tasks that read live kernel state, or new commands of this kind without a
  shim, break or silently do the wrong thing.
- **The build-time containerd.** `static/wrapper.yml` starts containerd by hand
  between the `containerd` and `kubernetes` roles for the kubeadm image
  pre-pull. It uses `/run/containerd-build.toml`, which is the shipped
  `config.toml` with the btrfs snapshotter disabled. Upstream changes to the
  containerd config, the unit, the socket path or the pre-pull task affect
  that bracket.
- **`/tmp` holds DIB's read-only `in_target.d` mount.** `install.d/60` passes
  `temp_files` as an empty list so sysprep's temp reset deletes nothing. If
  upstream renames or restructures that task, or adds another wipe of `/tmp`,
  the build fails with EROFS.
- **DIB owns parts of the image.** Cloud-init datasources
  (`install.d/10-restore-cloud-init-datasources`), the apt index for grub
  (`finalise.d/40`), the bootloader and `/etc/machine-id`
  (`finalise.d/999-ensure-machine-id`) are handled by DIB and this element.
  Check sysprep changes in these areas for conflicts.
- **Python.** Ansible runs in a venv whose interpreter is pinned. The `apt`
  family respawns under `/usr/bin/python3` to reach `python3-apt`. Other
  modules need their Python libraries in the venv, as `deb822_repository`
  needs `python-debian`.
- **Packer-only variables.** The roles see only the staged config JSONs, the
  override and the `-e` vars in `install.d/60`. Anything upstream feeds in
  through Packer (builder variables, `{{env ...}}`, `ansible_common_vars`
  renames) does not arrive unless the element passes it.

### Other findings

- **node.yml changed:** carry the change into `static/wrapper.yml` and keep
  the containerd start/stop bracket around the `kubernetes` role.
- **Node var files or config keys changed:** update the copy loop in
  `extra-data.d` and the `-e @config/...` list in `install.d/60` together.
- **kubeadm template matches:** remove `static/kubeadm.yml.j2`, its `cp` in
  `extra-data.d`, the `kubeadm_template` `-e` in `install.d/60` and the notes
  in `README.rst`, all in the same change as the pin bump.
- **containerd hash not in the allowlist:** diff the new upstream unit against
  the previous one before you add the hash to the `case` in `install.d/60`.
- **Per-series pins differ:** upstream's matrix is its own choice, not a
  requirement. Say what differs (for example one crictl version for every
  series) and whether following upstream would mean new keys in
  `overrides/*.json`. `scripts/update-extra-vars.py` rewrites those files, so
  the sync workflow would have to keep any new key.
- **New upstream role not used by the chroot run:** only relevant if node.yml
  or a role dependency starts to include it.

## 3. Report back

Answer in the language the user writes in. Keep file paths and identifiers
as they are. Structure the answer as follows:

1. One line with the pin, the target and why that target was chosen, and the
   number of upstream commits between them.
2. **Needs an element change:** each item with the upstream commit or PR,
   what changes, and the element files to touch.
3. **Workarounds that can go:** what, and from which upstream ref on.
4. **Arrives with the pin bump, no change needed:** short list.
5. **Not relevant for Ubuntu/OpenStack DIB builds:** one line, with the reason.
6. **Decisions for the user:** for example, whether to switch
   `containerd.service` to upstream's template, or whether to follow
   upstream's per-series pins.
7. A recommendation: bump now (name the release tag and its commit SHA), wait
   for the next release, or nothing to do.

Do not edit any file unless the user asks for it.

## Bumping the pin (only when asked)

- Pin the tag's **commit SHA**
  (`git -C <clone> rev-list -n1 <tag>`), never a tag or branch name. The
  cloned roles run as root on the build host and ship in every image, so a
  movable ref would be a code-injection path. `environment.d` explains this.
- Update every reference to the old pin: the default and the tag comment in
  `environment.d/10-k8s-capi.bash`, the `DIB_K8S_IMAGE_BUILDER_REF` entry in
  `elements/k8s-capi/README.rst`, and the usage comment in `build-local.sh`.
  Find them with
  `grep -rn "<old tag>\|<old sha>" --exclude-dir=.git .`.
- Make every ACTION change in the same commit, so no build runs the new roles
  without the element changes they need.
- Rerun the script. Once the pin is at the target, it should report no
  ACTION findings; if the target was a release tag, the rerun compares against
  `main` instead.
- A real image build runs only in Zuul: every change under `elements/k8s-capi/`
  triggers the build job of every series on the check pipeline. Locally,
  `./build-local.sh vX.YY` needs a Linux host.
