# kubernetes-capi-images

![Cirrus CI - Base Branch Build Status](https://img.shields.io/cirrus/github/osism/k8s-capi-images?style=for-the-badge)

Images intended for use with Kubernetes CAPI providers. More details on
https://image-builder.sigs.k8s.io/capi/capi.html.

The images are built with the [Image Builder](https://github.com/kubernetes-sigs/image-builder/),
a collection of cross-provider Kubernetes virtual machine image building utilities.

The images contain the latest stable releases, which are updated as required. This means
that the image for version `1.21` contains, for example, version `1.21.1`.

## Ubuntu 20.04

* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.21/ubuntu-2004-kube-v1.21.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.22/ubuntu-2004-kube-v1.22.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.23/ubuntu-2004-kube-v1.23.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.24/ubuntu-2004-kube-v1.24.qcow2

## Flatcar

* https://minio.services.osism.tech/openstack-k8s-capi-images/flatcar-stable-3033.2.4-kube-v1.24/flatcar-stable-3033.2.4-kube-v1.24.qcow2

## Commercial support

We offer commercial support for the images we provide. There are also minor versions available
and not only the last stable release. Send an email to [info@osism.tech](mailto:info@osism.tech)
for more details on commercial support.
