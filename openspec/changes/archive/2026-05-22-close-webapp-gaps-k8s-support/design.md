## Context

NITA's webapp will call Jenkins on the unauthenticated HTTP port (8080) once
`jenkins-anonymous-internal-access` is deployed. In Kubernetes, service-to-service
traffic is unrestricted by default: any pod in any namespace can reach the Jenkins
pod on port 8080, which would expose the unauthenticated endpoint cluster-wide.

Two additional housekeeping issues exist in the current `k8s/` manifests:
- `jenkins-service.yaml` contains cluster-specific immutable fields (`clusterIP`,
  `resourceVersion`, `uid`) that cause `kubectl apply` to fail on any cluster
  other than the one where the file was originally captured.
- `webapp-deployment.yaml` currently carries no Jenkins credentials — confirming
  the deployment is already clean with respect to `JENKINS_USER`/`JENKINS_PASS`.

## Goals / Non-Goals

**Goals:**
- Restrict access to Jenkins port 8080 to the `webapp` pod only via a NetworkPolicy.
- Fix `jenkins-service.yaml` so `kubectl apply` succeeds on a clean cluster.
- Confirm (and document) the absence of Jenkins credential env vars in the webapp deployment.

**Non-Goals:**
- Changing Jenkins configuration (handled in `nita-jenkins`).
- Modifying the webapp application code (handled in `nita-webapp`).
- Altering any other service's network policy.
- Enabling or requiring a CNI-specific feature (e.g., Calico-only policies).

## Decisions

### Decision 1: Standard Kubernetes NetworkPolicy over CNI-specific rules

**Choice:** Use `networking.k8s.io/v1 NetworkPolicy` with `podSelector` and
`namespaceSelector`.

**Rationale:** NITA targets any cluster with a CNI that honours the standard
NetworkPolicy API (Calico, Flannel+NetworkPolicy, Cilium, etc.). Vendor-specific
CRDs would couple the manifests to a particular CNI.

**Alternatives considered:**
- Calico `GlobalNetworkPolicy`: more expressive but non-portable.
- No policy (rely on Jenkins auth): violates defence-in-depth; anonymous port
  must not be reachable from arbitrary pods.

### Decision 2: Allow port 8443 unrestricted, restrict only 8080

**Choice:** The NetworkPolicy ingress rule covers port 8080 with a podSelector
for the webapp; port 8443 has a separate rule with no podSelector (allow all).

**Rationale:** Port 8443 is the human-facing HTTPS endpoint and must remain
accessible from the proxy pod and health probes. A single blanket deny-then-allow
policy would be fragile as new consumers of 8443 are added.

### Decision 3: Remove cluster-specific immutable fields from jenkins-service.yaml

**Choice:** Delete `metadata.resourceVersion`, `metadata.uid`, `spec.clusterIP`,
and `spec.clusterIPs` from the Service manifest.

**Rationale:** These fields are assigned by the Kubernetes API server and must not
be present in declarative manifests intended for `kubectl apply`. Their presence
causes a `422 Unprocessable Entity` error on any cluster that has not previously
created this service with exactly these values.

**Alternatives considered:**
- Use `kubectl replace` instead of `apply`: breaks the idempotent install workflow.

## Risks / Trade-offs

- **CNI without NetworkPolicy support** → If the cluster CNI does not enforce
  NetworkPolicy objects, the policy is silently ignored. Mitigation: document the
  CNI prerequisite in the install guide; `calico.yaml` is already bundled in `k8s/`.
- **Ordering dependency** → Applying the NetworkPolicy before the Jenkins pod
  exists is safe (Kubernetes applies it retroactively), but the webapp change
  (`nita-webapp: close-webapp-gaps`) must not be deployed until Jenkins is
  reconfigured for anonymous access or all job triggers will return 403.
- **Port 8080 blocked for future consumers** → Any new pod that needs to call
  Jenkins on port 8080 must have the `io.kompose.service: webapp` label or the
  NetworkPolicy must be updated. Mitigation: accept this constraint — it enforces
  the intended architecture.

## Migration Plan

1. Apply the updated manifests: `kubectl apply -f k8s/`
2. Verify NetworkPolicy is enforced: `kubectl describe networkpolicy jenkins-network-policy -n nita`
3. Confirm the Jenkins service applied without error and has no hardcoded clusterIP
4. Roll back by deleting the NetworkPolicy: `kubectl delete networkpolicy jenkins-network-policy -n nita` (all other changes are non-breaking)
