## 1. NetworkPolicy

- [x] 1.1 Create `k8s/jenkins-network-policy.yaml` with a `NetworkPolicy` in the `nita` namespace that allows ingress to the Jenkins pod on port 8080 only from pods labelled `io.kompose.service: webapp`
- [x] 1.2 Add a second ingress rule in the same NetworkPolicy allowing all sources on port 8443

## 2. Jenkins Service Manifest Cleanup

- [x] 2.1 Remove `metadata.resourceVersion` from `k8s/jenkins-service.yaml`
- [x] 2.2 Remove `metadata.uid` from `k8s/jenkins-service.yaml`
- [x] 2.3 Remove `spec.clusterIP` and `spec.clusterIPs` from `k8s/jenkins-service.yaml`

## 3. Verification

- [x] 3.1 Run `kubectl apply -f k8s/jenkins-service.yaml` on a clean cluster and confirm exit code 0
- [x] 3.2 Apply all manifests with `kubectl apply -f k8s/` and confirm NetworkPolicy `jenkins-network-policy` appears in `kubectl get networkpolicy -n nita`
- [x] 3.3 Confirm webapp pod can trigger a Jenkins job on port 8080 (no 403)
- [x] 3.4 Confirm that a pod without the webapp label cannot reach Jenkins port 8080
