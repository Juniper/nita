#!/bin/bash

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

FILES="nita-namespace.yaml pv.yaml pv2.yaml mariadb-persistentvolumeclaim.yaml jenkins-home-persistentvolumeclaim.yaml cluster-role.yaml db-deployment.yaml db-service.yaml jenkins-deployment.yaml jenkins-service.yaml proxy-deployment.yaml role-binding.yaml service-account.yaml storageClass.yaml webapp-deployment.yaml webapp-service.yaml junos-mcp-deployment.yaml junos-mcp-service.yaml"

for f in ${FILES}; do
    envsubst '${CONTAINER_REGISTRY} ${CSRF_TRUSTED_ORIGINS}' < ${f} | kubectl apply -f -
done
