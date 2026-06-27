# Immutable commit SHA of kubernetes-sigs/image-builder to fetch and run in the
# chroot. It MUST be a commit SHA, not a tag or branch: the cloned roles run as
# root on the build host and are baked into every node image, so a mutable ref
# could be moved to inject arbitrary code. The default is the commit for tag
# v0.1.52; override DIB_K8S_IMAGE_BUILDER_REF to pin a different commit.
export DIB_K8S_IMAGE_BUILDER_REF=${DIB_K8S_IMAGE_BUILDER_REF:-3428a09fcb4293b22a01a5e32cc007a9dacad6ec}

# DIB_K8S_CAPI_OVERRIDE must point at one of the overrides/*.json files and is
# deliberately left unset here: there is no safe default, so extra-data.d fails
# loudly when it is missing rather than building an arbitrary Kubernetes series.
