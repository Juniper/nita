#!/bin/bash

echo "Applying k8s YAML file to setup necessary pods!!!"
echo "Please be sure you are in the same folder as the yaml files"
kubectl apply -f nita-namespace.yaml,pv.yaml,pv2.yaml,mariadb-persistentvolumeclaim.yaml,jenkins-home-persistentvolumeclaim.yaml,cluster-role.yaml,db-deployment.yaml,db-service.yaml,jenkins-deployment.yaml,jenkins-service.yaml,proxy-deployment.yaml,role-binding.yaml,service-account.yaml,storageClass.yaml,webapp-deployment.yaml,webapp-service.yaml
