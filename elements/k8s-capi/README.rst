========
k8s-capi
========

A diskimage-builder element that reproduces the Cluster API (CAPI)
``ubuntu-XXXX-kube-vX.YY`` images locally without Packer. The Ubuntu base is
chosen per Kubernetes series through ``DIB_RELEASE``; 24.04 (``noble``) and
26.04 (``resolute``) are in use. From v1.37 on, the element also builds
``debian-13-kube-vX.YY`` images on Debian 13 (``trixie``), see `Debian`_.
Instead of reimplementing the provisioning in
Bash, it fetches
`kubernetes-sigs/image-builder <https://github.com/kubernetes-sigs/image-builder>`_
at a pinned git ref and runs image-builder's *original* Ansible roles
(``node`` → ``setup``, ``providers``, ``containerd``, ``kubernetes``,
``sysprep``) unchanged inside the build chroot.

The central problem this element solves is that image-builder's roles assume a
booted VM with a running ``systemd``, while the diskimage-builder chroot has no
init system. The element supplies build-time shims and a ``policy-rc.d`` so the
daemon-touching tasks succeed while still writing their configuration files, and
starts ``containerd`` manually for the Kubernetes image pre-pull.

This element deliberately drops image-builder's Packer-only goss plumbing.
Validation of the built image with the upstream goss spec is done separately,
after the build, by ``playbooks/validate.yml`` -- see the "Validating images"
section of the repository ``README.md``.

Inputs
======

Both inputs are environment variables (see ``environment.d/10-k8s-capi.bash``):

``DIB_K8S_IMAGE_BUILDER_REF``
  Immutable **commit SHA** of ``kubernetes-sigs/image-builder`` to clone and
  run -- not a tag or branch, since the cloned roles run as root on the build
  host and ship in every node image. Defaults to the commit for tag ``v0.1.55``
  (``7ffb9b7f1f26cd66891874463cc9411e3633325f``).

``DIB_K8S_CAPI_OVERRIDE``
  Absolute path to one of the ``overrides/*.json`` files in this repository.
  It selects the Kubernetes series. There is no default; the build fails
  loudly if it is unset or points at a missing file.

``DIB_RELEASE``
  DIB's own variable for the Ubuntu or Debian codename to build on. The
  element cannot set it (DIB's ``ubuntu`` and ``debian`` elements read it
  before any hook of this element runs), but ``extra-data.d`` fails the build
  unless it matches the ``<distro>_release`` (``ubuntu_release`` or
  ``debian_release``) of the selected override, where ``<distro>`` is DIB's
  ``DISTRO_NAME``. Without that check a build started without ``DIB_RELEASE``
  would silently fall back to DIB's default (``noble``, ``stable``) and install
  the series' Kubernetes packages on the wrong base.

Usage
=====

The element is normally driven through ``build-local.sh`` at the repository
root, which sets the inputs and invokes::

    disk-image-create -a amd64 -t qcow2 \
        -o output/ubuntu-2604-kube-v1.37.0 \
        ubuntu vm growroot openssh-server k8s-capi

with ``DIB_RELEASE`` set to the Ubuntu codename of the series (``noble`` or
``resolute``). ``build-local.sh`` reads it from the override file.

``build-local.sh v1.37 debian`` builds the Debian image of the series::

    disk-image-create -a amd64 -t qcow2 \
        -o output/debian-13-kube-v1.37.0 \
        debian vm growroot openssh-server k8s-capi

with ``DIB_RELEASE=trixie`` and ``DIB_DEBOOTSTRAP_EXTRA_ARGS=--force-check-gpg``
(see `Archive signature check`_).

How it works
============

``extra-data.d/10-fetch-image-builder`` (outside the chroot)
  Checks ``DIB_RELEASE`` against the override's ``<distro>_release`` for DIB's
  ``DISTRO_NAME`` (``ubuntu`` or ``debian``; any other value, and a missing key,
  fails the build), then clones
  image-builder at ``DIB_K8S_IMAGE_BUILDER_REF`` and stages, under
  ``$TMP_HOOKS_PATH/image-builder`` (visible as ``/tmp/in_target.d/image-builder``
  in the chroot): the ``ansible/`` tree and ``ansible.cfg``, the
  ``packer/config/*.json`` role inputs, the six build shims, ``wrapper.yml``,
  and the selected override, plus ``static/kubeadm.yml.j2`` (see `Offline image
  pre-pull`_). It normalizes the config JSONs by rewriting
  Packer ``{{ user `x` }}`` references to Ansible ``{{ x }}`` and replacing
  JSON ``null`` with the empty string, so a direct ``ansible-playbook`` run
  behaves like Packer's variable handling.

``install.d/10-restore-cloud-init-datasources`` (in the chroot)
  Removes the cloud-init datasource restriction that DIB's
  ``cloud-init-datasources`` element writes just before. The ``ubuntu`` element
  hard-depends on that element and defaults ``DIB_CLOUD_INIT_DATASOURCES`` to
  ``Ec2``, which leaves ``datasource_list: [ Ec2, None ]`` in the image: the
  ConfigDrive and OpenStack datasources are never probed, the CAPI user-data on
  a config drive is ignored, and the node only ever tries plain DHCP. Dropping
  the DIB files restores the stock Ubuntu list (``90_dpkg.cfg``) that the
  Packer-built images ship, so ``ds-identify`` selects the datasource from DMI
  and the attached drive again. The hook fails the build if any other file
  still restricts the list. On Debian there is nothing to remove: DIB's
  ``debian`` element does not depend on ``cloud-init-datasources``.

``install.d/50-install-ansible`` (in the chroot)
  Builds a throwaway virtualenv with the ``ansible-core`` version image-builder
  pins at the chosen ref and installs the ``community.general`` and
  ``ansible.posix`` collections the roles import, plus ``python-debian`` for
  ``ansible.builtin.deb822_repository`` (the ``apt`` family respawns itself
  under a system interpreter to reach ``python3-apt``; that module does not).

``install.d/60-run-image-builder`` (in the chroot)
  Writes ``/usr/sbin/policy-rc.d`` (so apt does not start services; DIB removes
  it again in its own cleanup phase), prepends the shims and the venv to
  ``PATH``, and runs ``wrapper.yml`` with the staged config JSONs and the
  override. ``ansible_python_interpreter`` is pinned to the venv interpreter:
  ansible-core 2.18's discovery only probes up to ``python3.13``, so on
  Resolute (Python 3.14) it would fall back to ``/usr/bin/python3``, where
  ``python-debian`` is missing and ``deb822_repository`` fails. On Debian it
  also passes the extra vars described in `Debian`_.

``finalise.d/40-update-apt-for-bootloader`` (in the chroot)
  Runs ``apt-get update`` before DIB's ``bootloader`` element installs grub.
  image-builder sysprep cleared the apt index, so without this the grub install
  fails with "no installation candidate".

``finalise.d/99-k8s-capi-cleanup`` (in the chroot)
  Removes the build scaffolding so it does not ship in the image: the Ansible
  venv and the Ansible/pip caches, and the apt index re-fetched for the
  bootloader. ``policy-rc.d`` is left for DIB to remove (its
  ``cleanup.d/40-unblock-daemons`` deletes it with a bare ``rm`` that errors if
  it is already gone). This runs in ``finalise.d`` rather than ``cleanup.d`` because
  ``cleanup.d`` runs on the build host as an unprivileged user, where these
  absolute paths would point at the host instead of the image. ``/tmp`` is left
  alone -- during DIB's chroot phases it holds DIB's own machinery (the
  ``in_target.d`` mount, dib-run-parts' profile dir), so wiping it breaks the
  build; ``wrapper.yml`` therefore only neutralizes image-builder sysprep's own
  temp reset (which cannot delete the read-only ``in_target.d`` mount) rather
  than reproducing it.

Build shims
===========

``static/shims/`` contains drop-in replacements prepended to ``PATH`` only
during the Ansible run:

``systemctl``
  No-ops daemon lifecycle verbs (``start``/``stop``/``restart``/
  ``daemon-reload`` …) and answers status queries benignly, but performs
  ``enable``/``disable`` offline (``SYSTEMD_OFFLINE=1``) so ``containerd`` and
  ``kubelet`` end up enabled-but-stopped in the image.

``modprobe``, ``sysctl``, ``journalctl``, ``fstrim``, ``udevadm``
  No-op (exit ``0``). The Ansible modules still write their configuration files
  (``/etc/modules-load.d``, ``/etc/sysctl.conf`` …); only the live kernel/daemon
  action is skipped.

Offline image pre-pull
======================

``kubeadm config images pull`` needs a running ``containerd`` so the images bake
into the offline content store. ``wrapper.yml`` therefore starts
``/usr/local/bin/containerd`` manually between the ``containerd`` and
``kubernetes`` roles, waits for its socket, lets the ``kubernetes`` role pull the
images into the ``k8s.io`` namespace, then stops it.

The role renders the kubeadm config for that pull from the template named by
``kubeadm_template``. The template shipped at the pinned ref still declares
``kubeadm.k8s.io/v1beta3``, which kubeadm 1.37 removed -- the pre-pull aborts
with *your configuration file uses an old API spec*. The element therefore
stages its own ``static/kubeadm.yml.j2`` (the same template with the API version
raised to ``v1beta4``, understood by kubeadm 1.31 and newer) and points
``kubeadm_template`` at it by absolute path. Upstream made the same change on
main in commit ``db2e0f41014c``; both the template and the extra var can go once
``DIB_K8S_IMAGE_BUILDER_REF`` moves past it.

If the in-chroot ``containerd`` pre-pull proves unstable in a given build
environment (overlayfs/cgroup constraints), the documented fallback is to pull
the images on first boot via a ``systemd`` oneshot instead. That fallback is not
implemented here; the in-chroot pre-pull is the default.

Reverse path filtering on Resolute
==================================

The ``node`` role sets ``net.ipv4.conf.all.rp_filter`` to ``1`` without passing
its own ``sysctl_conf_file``, so the value lands in ``/etc/sysctl.conf``.
systemd 259 on Ubuntu 26.04 no longer reads that file, and the image boots with
the ``2`` that procps ships in ``/usr/lib/sysctl.d/55-network-security.conf``.
Upstream's goss spec expects ``1`` and catches this once the image is booted
(see "Validating images" in the repository ``README.md``). ``wrapper.yml``
therefore writes the same value to ``/etc/sysctl.d/99-sysctl.conf`` on Ubuntu
26.04 and newer, the file ``sysctl_conf_file`` names there, and on Debian (see
`Debian`_). The task can go once the role's ``rp_filter`` task passes
``sysctl_file: "{{ sysctl_conf_file }}"`` and ``DIB_K8S_IMAGE_BUILDER_REF``
moves past that change.

Debian
======

image-builder has no Debian build target
(`kubernetes-sigs/image-builder#2019 <https://github.com/kubernetes-sigs/image-builder/issues/2019>`_),
and the roles run here contain Ubuntu-only steps. The element closes each gap
with a scoped workaround and never edits the cloned roles. Each workaround can
go once the named upstream change is in the pinned
``DIB_K8S_IMAGE_BUILDER_REF``.

a. Virtualization packages. On amd64 the setup role installs
   ``common_virt_debs``, which names Ubuntu's ``linux-cloud-tools-virtual`` and
   ``linux-tools-virtual`` metapackages. Debian 13 has neither, so
   ``install.d/60-run-image-builder`` passes ``common_virt_debs`` as
   ``hyperv-daemons``, ``linux-perf`` and ``open-vm-tools``, Debian's packages
   for the same Hyper-V daemons and perf tools. ``hyperv-daemons`` is required:
   the providers role disables ``hv-kvp-daemon``, and on Debian only that
   package ships the unit. Retired once the node role's defaults name Debian
   packages for ``common_virt_debs``.

b. Kernel parameter file. The node role writes its kernel parameters to
   ``sysctl_conf_file``, which upstream resolves to ``/etc/sysctl.conf`` on
   Debian. systemd 257 on Debian 13 never reads that file, so the image would
   boot without ``net.ipv4.ip_forward=1`` and the bridge-netfilter settings.
   ``install.d/60`` passes ``sysctl_conf_file: /etc/sysctl.d/99-sysctl.conf``.
   Retired once the node role's defaults resolve ``sysctl_conf_file`` to that
   file on Debian.

c. cloud-init packages. The providers role's openstack tasks install
   ``cloud-initramfs-copymods``, which Debian 13 does not have, from a
   task-level ``packages`` var. An extra var would also replace the package
   list of the kubernetes role's "Install Kubernetes" task, which uses the same
   name, so ``wrapper.yml`` includes the providers role on Debian with
   ``packages`` (``cloud-init``, ``cloud-guest-utils``,
   ``cloud-initramfs-dyn-netconf``) as an include-role var. It outranks the
   task var inside that role and does not reach other roles. Retired once
   ``providers/tasks/openstack.yml`` stops requiring
   ``cloud-initramfs-copymods`` on Debian.

d. Reverse path filtering. The node role sets ``net.ipv4.conf.all.rp_filter``
   to ``1`` on Ubuntu only, and Debian 13's
   ``/usr/lib/sysctl.d/50-default.conf`` sets ``net.ipv4.conf.*.rp_filter = 2``
   and leaves ``all`` at the kernel default. For parity with the Ubuntu image,
   ``wrapper.yml`` writes ``1`` to ``/etc/sysctl.d/99-sysctl.conf`` on Debian as
   well (see `Reverse path filtering on Resolute`_). Retired once the role's
   task also runs on Debian and passes ``sysctl_file``.

``package-installs.yaml`` adds ``netplan.io`` on Debian. DIB's ``debian``
element installs it only when ``DIB_RELEASE`` is ``bookworm``, ``stable`` or
``testing``, and DIB disables apt recommends, so a ``trixie`` build would ship
neither netplan.io nor ifupdown. With it, cloud-init renders netplan and
systemd-networkd brings up the interfaces, as on the Ubuntu images, and the
providers role's networkd-dispatcher hooks for DHCP-provided NTP servers work.
The entry can go once DIB's ``debian/install.d/10-cloud-opinions`` installs
``netplan.io`` for ``trixie``.

``finalise.d/999-ensure-machine-id`` also covers the missing
``/etc/machine-id`` on Debian (kubernetes-sigs/image-builder#2164).

Archive signature check
-----------------------

DIB's ``debian-minimal`` builds the root filesystem with debootstrap on the
build host. Without ``debian-archive-keyring`` there, debootstrap only warns
(``W: Cannot check Release signature; keyring file not available``) and
continues unverified. Debian builds therefore set
``DIB_DEBOOTSTRAP_EXTRA_ARGS=--force-check-gpg``, and a missing keyring aborts
the build with ``E: Keyring-based check was requested; aborting accordingly``.
``playbooks/pre.yml`` installs the keyring on the CI build host.

Ubuntu 24.04's ``debian-archive-keyring`` verifies trixie's ``InRelease``
through the Debian 12 archive key. Once Debian stops co-signing trixie with
that key after Debian 14's release, this keyring can no longer verify it and
the Debian build fails with the same ``E:`` line. The remedy is a newer
``debian-archive-keyring`` on the build host.

``DIB_APT_KEYRING`` is not used: ``debian-minimal`` pipes that keyring into
``apt-key`` inside the chroot, and Debian 13 has no ``apt-key``.
