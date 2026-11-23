#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
export NITA_NAMESPACE="${NITA_NAMESPACE:-nita}"

write_yaml_files.py
python3 ./enrich_variables.py .
python3 ./create_ansible_job_k8s.py build
kubectl create -f build.yaml -n "$NITA_NAMESPACE"
pod=""
for attempt in $(seq 1 600); do
    pod=$(kubectl get pods -l job-name=build -o name -n "$NITA_NAMESPACE")
    if [ -n "$pod" ]; then
        break
    fi
    sleep 1
done
if [ -z "$pod" ]; then
    kubectl describe job/build -n "$NITA_NAMESPACE"
    echo "Timed out waiting for the Ansible build pod." >&2
    exit 1
fi
kubectl logs "$pod" -f --pod-running-timeout=600s -n "$NITA_NAMESPACE"
if ! kubectl wait --for=condition=complete job/build --timeout=30s -n "$NITA_NAMESPACE"; then
    kubectl describe job/build -n "$NITA_NAMESPACE"
    echo "Ansible build did not complete successfully." >&2
    exit 1
fi
