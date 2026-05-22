## Why

The webapp will call Jenkins on port 8080 without credentials once `nita-jenkins` is reconfigured for anonymous internal access. Without complementary k8s changes, Jenkins port 8080 remains reachable from any pod in the cluster (no NetworkPolicy) and the webapp deployment still carries now-unused `JENKINS_USER`/`JENKINS_PASS` env vars; additionally, `jenkins-service.yaml` contains hardcoded cluster-specific fields (`clusterIP`, `resourceVersion`, `uid`) that cause `kubectl apply` to fail on a clean cluster.

## What Changes

- **New** `k8s/jenkins-network-policy.yaml`: `NetworkPolicy` that permits ingress to Jenkins port 8080 only from pods labelled `io.kompose.service: webapp` in the `nita` namespace; all traffic on port 8443 remains unrestricted.
- **Modified** `k8s/webapp-deployment.yaml`: Remove `JENKINS_USER` and `JENKINS_PASS` environment variables — credentials are no longer used by the webapp.
- **Modified** `k8s/jenkins-service.yaml`: Remove hardcoded `clusterIP`, `resourceVersion`, and `uid` fields to allow idempotent `kubectl apply` on any cluster.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `kubernetes`: Adding a NetworkPolicy requirement that restricts unauthenticated Jenkins port 8080 access to the webapp pod only, and removing the requirement for Jenkins credentials in the webapp deployment.

## Impact

- `k8s/` manifests: three files changed (one new, two modified)
- No application code changes
- Depends on `nita-jenkins` (`jenkins-anonymous-internal-access`) being deployed before the webapp is updated — the NetworkPolicy is safe to apply independently
