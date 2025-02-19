

# Install libraries
pip install kopf
pip install confluent-kafka
pip install kubernetes


kubectl apply -f crd.yaml


# start operator
kopf run kafka_acl_operator.py