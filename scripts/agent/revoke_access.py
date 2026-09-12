#!/usr/bin/env python3
"""Delete all agent RBAC objects and the agent ServiceAccount.

This script deletes every resource matching those labels across all namespaces.

"""

import logging

from kubernetes import config, dynamic
from kubernetes.client import ApiClient

LABEL_SELECTOR = (
    "app.kubernetes.io/component=access-control,"
    "app.kubernetes.io/managed-by=ITBench"
)

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def revoke_all(dyn: dynamic.DynamicClient) -> None:
    """Delete all agent RBAC objects and ServiceAccount identified by the ITBench labels."""
    crb_res = dyn.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="ClusterRoleBinding")
    cr_res = dyn.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="ClusterRole")
    rb_res = dyn.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="RoleBinding")
    role_res = dyn.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="Role")
    sa_res = dyn.resources.get(api_version="v1", kind="ServiceAccount")

    # Cluster-scoped resources
    for resource in (crb_res, cr_res):
        for item in resource.get(label_selector=LABEL_SELECTOR).items:
            logger.info("Deleting %s/%s.", resource.kind, item.metadata.name)
            resource.delete(name=item.metadata.name)

    # Namespace-scoped resources — omit namespace to list across all namespaces
    for resource in (rb_res, role_res, sa_res):
        for item in resource.get(label_selector=LABEL_SELECTOR).items:
            logger.info("Deleting %s/%s in namespace %s.", resource.kind, item.metadata.name, item.metadata.namespace)
            resource.delete(name=item.metadata.name, namespace=item.metadata.namespace)


def main() -> None:
    config.load_kube_config()

    dyn_client = dynamic.DynamicClient(ApiClient())
    revoke_all(dyn_client)
    logger.info("Revocation complete.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.logging import configure_logging
    configure_logging()
    main()
