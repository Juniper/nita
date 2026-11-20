## Context

Current manifests, as applied by `k8s/apply-k8s.sh`:

- `jenkins-deployment.yaml`: container listens on 8080 (HTTP, `--prefix=/jenkins`)
  and 8443 (HTTPS, Jenkins's own keystore). `ports:` declares
  `containerPort: 8443, hostPort: 8443`.
- `jenkins-service.yaml`: ClusterIP `jenkins` exposing 8080 and 8443.
- `jenkins-network-policy.yaml`: ingress 8080 from pods labelled `webapp` or
  `jenkins`; ingress 8443 from anywhere.
- `proxy-deployment.yaml`: nginx, labelled `io.kompose.service: proxy`,
  `hostPort: 443`, config from the `proxy-config-cm` ConfigMap, which
  `install.sh` builds from `nita-webapp/nginx/nginx.conf`. That config proxies
  `/jenkins/` to `http://jenkins:8080/jenkins/`.

Consumers of port 8443: the `nita-cmd jenkins …` scripts in `nita-jenkins`
(`kubectl exec` into the Jenkins pod, then `jenkins-cli.jar -s
https://admin:admin@jenkins:8443/jenkins/ …`), and humans following the
`install.sh` message. The webapp never uses 8443; it uses `jenkins:8080`.

## Goals / Non-Goals

**Goals**

- The only route from outside the cluster to Jenkins is the nginx proxy.
- The proxy pod is permitted to reach Jenkins on 8080.
- `nita-cmd jenkins …` keeps working unchanged.
- Operator documentation gives the proxied URL.

**Non-Goals**

- Removing Jenkins's HTTPS listener or keystore (would require changing the
  `nita-cmd` scripts in another repo; they can move to `http://jenkins:8080`
  later).
- Changing the Service manifest.
- Anything about Jenkins authorisation (companion `nita-jenkins` change).

## Decisions

### Decision 1: Drop `hostPort`, keep `containerPort`

**Choice:** Delete `hostPort: 8443` from the Jenkins container's `ports`
entry; keep `containerPort: 8443`.

**Rationale:** `hostPort` is what publishes the port on the node; it is the
whole bypass. `containerPort` is informational and documents that the
listener exists for in-cluster use. Keeping the listener avoids touching the
`JENKINS_OPTS` keystore flags and the `nita-cmd` scripts in the same change.

### Decision 2: Allow `proxy` on 8080; confine 8443 to `jenkins`

**Choice:**

```yaml
ingress:
  - ports: [{port: 8080, protocol: TCP}]
    from:
      - podSelector: {matchLabels: {io.kompose.service: webapp}}
      - podSelector: {matchLabels: {io.kompose.service: proxy}}
      - podSelector: {matchLabels: {io.kompose.service: jenkins}}
  - ports: [{port: 8443, protocol: TCP}]
    from:
      - podSelector: {matchLabels: {io.kompose.service: jenkins}}
```

**Rationale:** The proxy must reach 8080 for `/jenkins/` to work at all — its
absence from the current policy is a latent defect masked by CNIs that do not
enforce NetworkPolicy. 8443 has exactly one legitimate caller, the Jenkins pod
itself (via `kubectl exec`); when a pod connects to its own Service the source
is the pod, so a `jenkins` podSelector admits it. Everything else on 8443 is
denied, which matches the intent now that the port is no longer published.

**Rejected:** deleting the 8443 rule entirely (would deny the pod-to-self
path on enforcing CNIs and break `nita-cmd jenkins …`); allowing 8443 from
the whole namespace (unnecessarily broad).

### Decision 3: Documentation says `/jenkins/`, not `:8443`

**Choice:** `install.sh` prints `https://${HOST}/jenkins/`; `docs/nita-examples.md`
follows; `docs/containers.md`'s pasted `docker ps` output drops the
`0.0.0.0:8443->8443/tcp` mapping.

**Rationale:** Operators do what the install script tells them. If it still
advertises `:8443` the bypass is gone but the confusion remains.

## Risks / Trade-offs

- **Enforcing CNI, first apply.** On a cluster that enforces NetworkPolicy,
  the current policy already breaks the proxied path. After this change the
  proxied path works and the direct path is gone — strictly better, but
  operators who were using `:8443` because `/jenkins/` "never worked" will
  need the new URL. The install message covers it.
- **Non-enforcing CNI.** The NetworkPolicy change is a no-op in practice; the
  `hostPort` removal is what matters and is CNI-independent.
- **Jenkins "reverse proxy setup is broken" monitor.** Unaffected; the proxy
  configuration and `JENKINS_URL` handling are unchanged.

## Migration Plan

1. Deploy `nita-jenkins/revoke-anonymous-build-and-enable-csrf` first and
  verify authenticated build clients still work.
2. Apply the updated manifests with `apply-k8s.sh` (Deployment rollout restarts
  the Jenkins pod; `jenkins_home` is a PVC so no data is lost).
3. Verify `https://<host>:8443/` is refused, the proxy pod can reach Jenkins
  on 8080, and `https://<host>/jenkins/` loads through the proxy.
4. Run `nita-cmd jenkins version` and confirm it still answers.
5. Deploy `nita-webapp/gate-jenkins-behind-webapp-session` after proxy
  connectivity is confirmed.

Rollback: re-add `hostPort: 8443` and re-apply.
