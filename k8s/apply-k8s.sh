#!/bin/bash

set -e

CONTAINER_REGISTRY=${CONTAINER_REGISTRY:=ghcr.io/aburston}
export CONTAINER_REGISTRY

# Build CSRF_TRUSTED_ORIGINS from the current hostname and all host IPs unless
# the caller has already set it.
if [[ -z "${CSRF_TRUSTED_ORIGINS:-}" ]]; then
    _origins="https://localhost,http://localhost"
    _host=$(hostname 2>/dev/null || true)
    [[ -n "$_host" ]] && _origins="https://${_host},http://${_host},${_origins}"
    for _ip in $(hostname -I 2>/dev/null); do
        _origins="https://${_ip},http://${_ip},${_origins}"
    done
    CSRF_TRUSTED_ORIGINS="${_origins}"
fi
export CSRF_TRUSTED_ORIGINS

echo "Applying k8s YAML file to setup necessary pods!!!"
echo "Please be sure you are in the same folder as the yaml files"
echo "Using container registry: ${CONTAINER_REGISTRY}"
echo "Using CSRF trusted origins: ${CSRF_TRUSTED_ORIGINS}"

BASE_FILES="nita-namespace.yaml storageClass.yaml pv.yaml pv2.yaml mariadb-persistentvolumeclaim.yaml jenkins-home-persistentvolumeclaim.yaml service-account.yaml cluster-role.yaml role-binding.yaml"
WORKLOAD_FILES="db-service.yaml db-deployment.yaml webapp-service.yaml webapp-deployment.yaml jenkins-service.yaml jenkins-deployment.yaml proxy-deployment.yaml"
FILES="${BASE_FILES} ${WORKLOAD_FILES}"
REQUIRED_CONFIGMAPS="proxy-config-cm proxy-cert-cm jenkins-crt jenkins-keystore"

ApplyYaml() {
    envsubst '${CONTAINER_REGISTRY} ${CSRF_TRUSTED_ORIGINS}' < "$1" | kubectl apply -f -
}

for f in ${BASE_FILES}; do
    ApplyYaml "${f}"
done

missing=0
for cm in ${REQUIRED_CONFIGMAPS}; do
    if ! kubectl get cm "${cm}" --namespace nita >/dev/null 2>&1; then
        echo "Error: required ConfigMap \"${cm}\" is missing in namespace nita." >&2
        echo "Create the proxy and Jenkins ConfigMaps before applying workloads." >&2
        missing=1
    fi
done

[ "${missing}" -eq 0 ] || exit 1

for f in ${WORKLOAD_FILES}; do
    ApplyYaml "${f}"
done
