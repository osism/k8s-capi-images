========
k8s-capi
========

A diskimage-builder element that reproduces the Cluster API (CAPI)
``ubuntu-2404-kube-vX.YY`` images locally without Packer. Instead of
reimplementing the provisioning in Bash, it fetches
`kubernetes-sigs/image-builder <https://github.com/kubernetes-sigs/image-builder>`_
at a pinned git ref and runs image-builder's *original* Ansible roles
(``node`` → ``setup``, ``providers``, ``containerd``, ``kubernetes``,
``sysprep``) unchanged inside the build chroot.

The central problem this element solves is that image-builder's roles assume a
booted VM with a running ``systemd``, while the diskimage-builder chroot has no
init system. The element supplies build-time shims and a ``policy-rc.d`` so the
daemon-touching tasks succeed while still writing their configuration files, and
starts ``containerd`` manually for the Kubernetes image pre-pull.

Inputs
======

Both inputs are environment variables (see ``environment.d/10-k8s-capi.bash``):

``DIB_K8S_IMAGE_BUILDER_REF``
  Immutable **commit SHA** of ``kubernetes-sigs/image-builder`` to clone and
  run -- not a tag or branch, since the cloned roles run as root on the build
  host and ship in every node image. Defaults to the commit for tag ``v0.1.52``
  (``3428a09fcb4293b22a01a5e32cc007a9dacad6ec``).

``DIB_K8S_CAPI_OVERRIDE``
  Absolute path to one of the ``overrides/*.json`` files in this repository.
  It selects the Kubernetes series (and, for the ``-gardener`` variants, the
  containerd/runc versions). There is no default; the build fails loudly if it
  is unset or points at a missing file.

Usage
=====

The element is normally driven through ``build-local.sh`` at the repository
root, which sets the inputs and invokes::

    disk-image-create -a amd64 -t qcow2 \
        -o output/ubuntu-2404-kube-v1.33.12 \
        ubuntu vm growroot openssh-server k8s-capi

How it works
============

``extra-data.d/10-fetch-image-builder`` (outside the chroot)
  Clones image-builder at ``DIB_K8S_IMAGE_BUILDER_REF`` and stages, under
  ``$TMP_HOOKS_PATH/image-builder`` (visible as ``/tmp/in_target.d/image-builder``
  in the chroot): the ``ansible/`` tree and ``ansible.cfg``, the
  ``packer/config/*.json`` role inputs, the six build shims, ``wrapper.yml``,
  and the selected override. It normalizes the config JSONs by rewriting
  Packer ``{{ user `x` }}`` references to Ansible ``{{ x }}`` and replacing
  JSON ``null`` with the empty string, so a direct ``ansible-playbook`` run
  behaves like Packer's variable handling.

``install.d/50-install-ansible`` (in the chroot)
  Builds a throwaway virtualenv with the ``ansible-core`` version image-builder
  pins at the chosen ref and installs the ``community.general`` and
  ``ansible.posix`` collections the roles import.

``install.d/60-run-image-builder`` (in the chroot)
  Writes ``/usr/sbin/policy-rc.d`` (so apt does not start services; DIB removes
  it again in its own cleanup phase), prepends the shims and the venv to
  ``PATH``, and runs ``wrapper.yml`` with the staged config JSONs and the
  override.

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

If the in-chroot ``containerd`` pre-pull proves unstable in a given build
environment (overlayfs/cgroup constraints), the documented fallback is to pull
the images on first boot via a ``systemd`` oneshot instead. That fallback is not
implemented here; the in-chroot pre-pull is the default.
