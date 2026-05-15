#!/bin/bash

CONTAINER_REGISTRY=${CONTAINER_REGISTRY:=ghcr.io/juniper}
export CONTAINER_REGISTRY

echo "Applying k8s YAML file to setup necessary pods!!!"
echo "Please be sure you are in the same folder as the yaml files"
echo "Using container registry: ${CONTAINER_REGISTRY}"

FILES="nita-namespace.yaml pv.yaml pv2.yaml mariadb-persistentvolumeclaim.yaml jenkins-home-persistentvolumeclaim.yaml cluster-role.yaml db-deployment.yaml db-service.yaml jenkins-deployment.yaml jenkins-service.yaml proxy-deployment.yaml role-binding.yaml service-account.yaml storageClass.yaml webapp-deployment.yaml webapp-service.yaml"

for f in ${FILES}; do
    envsubst '${CONTAINER_REGISTRY}' < ${f} | kubectl apply -f -
done
