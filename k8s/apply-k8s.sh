#!/bin/bash

CONTAINER_REGISTRY=${CONTAINER_REGISTRY:=ghcr.io/juniper}
GITHUB_ORG=${GITHUB_ORG:=Juniper}
NITA_WEBAPP_IMAGE=${NITA_WEBAPP_IMAGE:=${CONTAINER_REGISTRY}/nita-webapp:latest}
NITA_JENKINS_IMAGE=${NITA_JENKINS_IMAGE:=${CONTAINER_REGISTRY}/nita-jenkins:latest}
NITA_ANSIBLE_IMAGE=${NITA_ANSIBLE_IMAGE:=${CONTAINER_REGISTRY}/nita-ansible:latest}
NITA_ROBOT_IMAGE=${NITA_ROBOT_IMAGE:=${CONTAINER_REGISTRY}/nita-robot:latest}
JUNOS_MCP_IMAGE=${JUNOS_MCP_IMAGE:=${CONTAINER_REGISTRY}/junos-mcp-server:latest}
export CONTAINER_REGISTRY GITHUB_ORG NITA_WEBAPP_IMAGE NITA_JENKINS_IMAGE NITA_ANSIBLE_IMAGE NITA_ROBOT_IMAGE JUNOS_MCP_IMAGE

# Build CSRF_TRUSTED_ORIGINS from the current hostname and all host IPs unless
# the caller has already set it.
if [[ -z "${CSRF_TRUSTED_ORIGINS:-}" ]]; then
    _origins="https://localhost,http://localhost"
    _host=$(hostname 2>/dev/null || true)
    [[ -n "$_host" ]] && _origins="https://${_host},http://${_host},${_origins}"
    for _ip in $(hostname -I 2>/dev/null || true); do
        _origins="https://${_ip},http://${_ip},${_origins}"
    done
    CSRF_TRUSTED_ORIGINS="${_origins}"
fi
export CSRF_TRUSTED_ORIGINS

set -e

echo "Applying k8s YAML file to setup necessary pods!!!"
echo "Please be sure you are in the same folder as the yaml files"
echo "Using container registry: ${CONTAINER_REGISTRY}"
echo "Using webapp image: ${NITA_WEBAPP_IMAGE}"
echo "Using Jenkins image: ${NITA_JENKINS_IMAGE}"
echo "Using Ansible image: ${NITA_ANSIBLE_IMAGE}"
echo "Using Robot image: ${NITA_ROBOT_IMAGE}"
echo "Using Junos MCP image: ${JUNOS_MCP_IMAGE}"
echo "Using CSRF trusted origins: ${CSRF_TRUSTED_ORIGINS}"

BASE_FILES="nita-namespace.yaml storageClass.yaml pv.yaml pv2.yaml mariadb-persistentvolumeclaim.yaml jenkins-home-persistentvolumeclaim.yaml service-account.yaml cluster-role.yaml role-binding.yaml"
WORKLOAD_FILES="db-service.yaml db-deployment.yaml webapp-service.yaml webapp-deployment.yaml jenkins-service.yaml jenkins-network-policy.yaml jenkins-deployment.yaml proxy-deployment.yaml"
REQUIRED_CONFIGMAPS="proxy-config-cm proxy-cert-cm jenkins-crt jenkins-keystore"

ApplyYaml() {
    # shellcheck disable=SC2016 -- envsubst needs literal variable names here.
    envsubst '${CONTAINER_REGISTRY} ${CSRF_TRUSTED_ORIGINS} ${NITA_WEBAPP_IMAGE} ${NITA_JENKINS_IMAGE} ${NITA_ANSIBLE_IMAGE} ${NITA_ROBOT_IMAGE} ${JUNOS_MCP_IMAGE}' < "$1" | kubectl apply -f -
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
