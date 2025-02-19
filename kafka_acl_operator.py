import kopf
import logging
from confluent_kafka.admin import AdminClient, AclBinding, AclOperation, AclPermissionType, ResourceType, \
    ResourcePatternType, AclBindingFilter
from kubernetes import client, config

# Load Kubernetes config (needed when running outside the cluster)
try:
    # Try to load in-cluster config (when running inside Kubernetes)
    config.load_incluster_config()
except Exception:
    # Fallback: Load kubeconfig from local machine (for local debugging)
    config.load_kube_config()

# Kafka Admin Client Configuration
KAFKA_CONFIG = {
    "bootstrap.servers": "127.0.0.1:64154"
}
admin_client = AdminClient(KAFKA_CONFIG)

# Function to map operations from CRD to Kafka ACL API
ACL_OPERATIONS = {
    "Read": AclOperation.READ,
    "Write": AclOperation.WRITE,
    "Create": AclOperation.CREATE,
    "Delete": AclOperation.DELETE,
    "Alter": AclOperation.ALTER,
}

@kopf.on.create('kafkaacls.kafka.acl.io')
def create_kafka_acl(spec, **kwargs):
    """Handles the creation of a Kafka ACL."""
    principal = spec.get("principal")
    topic = spec.get("topic")
    operations = spec.get("operations", [])

    if not principal or not topic:
        raise kopf.PermanentError("Both 'principal' and 'topic' are required fields!")

    acl_bindings = [
        AclBinding(
            restype=ResourceType.TOPIC,
            name=topic,
            resource_pattern_type=ResourcePatternType.LITERAL,
            principal=principal,
            host="*",
            operation=ACL_OPERATIONS[op],
            permission_type=AclPermissionType.ALLOW
        )
        for op in operations
    ]

    # Apply ACLs to Kafka
    try:
        admin_client.create_acls(acl_bindings)
        logging.info(f"Kafka ACLs applied: {principal} -> {operations} on {topic}")
    except Exception as e:
        raise kopf.TemporaryError(f"Failed to set ACL: {e}", delay=10)

@kopf.on.delete('kafkaacls.kafka.acl.io')
def delete_kafka_acl(spec, **kwargs):
    """Handles the deletion of a Kafka ACL."""
    principal = spec.get("principal")
    topic = spec.get("topic")

    # acl_bindings = [
    #     AclBinding(
    #         restype=ResourceType.TOPIC,
    #         name=topic,
    #         resource_pattern_type=ResourcePatternType.LITERAL,
    #         principal=principal,
    #         host="*",
    #         operation=AclOperation.DELETE,
    #         permission_type=AclPermissionType.ALLOW
    #     )
    # ]

    acl_filter = AclBindingFilter(
        restype=ResourceType.TOPIC,
        name=topic,
        resource_pattern_type=ResourcePatternType.LITERAL,
        principal=principal,
        host="*",
        operation=AclOperation.DELETE,  # Ensure this is a valid operation
        permission_type=AclPermissionType.ALLOW
    )


    try:
        admin_client.delete_acls(acl_filter)
        logging.info(f"Deleted Kafka ACLs for {principal} on {topic}")
    except Exception as e:
        logging.error(f"Failed to delete ACL: {e}")

