# kubernetes-capi-images

Images intended for use with Kubernetes CAPI providers. More details on
https://image-builder.sigs.k8s.io/capi/capi.html.

The images are built with the [Image Builder](https://github.com/kubernetes-sigs/image-builder/),
a collection of cross-provider Kubernetes virtual machine image building utilities.

## Ubuntu 22.04

The following images contain the latest stable releases, which are updated as required.
This means that the image for version `1.21` contains, for example, version `1.21.1`.

* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.26/ubuntu-2204-kube-v1.26.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.25/ubuntu-2204-kube-v1.25.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.24/ubuntu-2204-kube-v1.24.qcow2

### v1.26

* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.26/ubuntu-2204-kube-v1.26.4.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.26/ubuntu-2204-kube-v1.26.4.qcow2.CHECKSUM
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.26/ubuntu-2204-kube-v1.26.3.qcow2

### v1.25

* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.25/ubuntu-2204-kube-v1.25.9.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.25/ubuntu-2204-kube-v1.25.9.qcow2.CHECKSUM
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.25/ubuntu-2204-kube-v1.25.8.qcow2

### v1.24

* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.24/ubuntu-2204-kube-v1.24.13.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.24/ubuntu-2204-kube-v1.24.13.qcow2.CHECKSUM
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2204-kube-v1.24/ubuntu-2204-kube-v1.24.12.qcow2

## Ubuntu 20.04 (Archived)

These images are no longer updated. Please use the Ubuntu 22.04 images.

* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.26/ubuntu-2004-kube-v1.26.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.25/ubuntu-2004-kube-v1.25.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.24/ubuntu-2004-kube-v1.24.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.23/ubuntu-2004-kube-v1.23.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.22/ubuntu-2004-kube-v1.22.qcow2
* https://minio.services.osism.tech/openstack-k8s-capi-images/ubuntu-2004-kube-v1.21/ubuntu-2004-kube-v1.21.qcow2

## Images provided by Vexxhost

Ubuntu 22.04 based [CAPI images from Vexxhost](https://github.com/vexxhost/magnum-cluster-api).

* [v1.26.2](https://object-storage.public.mtl1.vexxhost.net/swift/v1/a91f106f55e64246babde7402c21b87a/magnum-capi/ubuntu-2204-v1.26.2.qcow2)
* [v1.25.3](https://object-storage.public.mtl1.vexxhost.net/swift/v1/a91f106f55e64246babde7402c21b87a/magnum-capi/ubuntu-2004-v1.25.3.qcow2)
* [v1.24.7](https://object-storage.public.mtl1.vexxhost.net/swift/v1/a91f106f55e64246babde7402c21b87a/magnum-capi/ubuntu-2004-v1.24.7.qcow2)
* [v1.23.13](https://object-storage.public.mtl1.vexxhost.net/swift/v1/a91f106f55e64246babde7402c21b87a/magnum-capi/ubuntu-2004-v1.23.13.qcow2)
