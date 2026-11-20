## Why

The Kubernetes deployment publishes Jenkins twice. The intended path is the
nginx proxy at `https://<host>/jenkins/`. The second path is
`k8s/jenkins-deployment.yaml`, which binds the Jenkins container's HTTPS
listener to **host port 8443**, and `install.sh`, which tells the operator to
use it. Host port 8443 goes straight to Jenkins, so anything the proxy does —
TLS with the NITA certificate, and the webapp-session gate being added in
`nita-webapp/gate-jenkins-behind-webapp-session` — is bypassed by changing the
port number in the address bar.

Separately, `k8s/jenkins-network-policy.yaml` allows ingress to Jenkins port
8080 only from pods labelled `io.kompose.service: webapp` (and Jenkins itself).
The nginx proxy pod is labelled `io.kompose.service: proxy` and proxies
`/jenkins/` to `jenkins:8080`. On a CNI that enforces NetworkPolicy, the
proxied path is therefore blocked and the only working route to the Jenkins UI
*is* the host-port bypass. The `kubernetes` spec codifies both facts
("Ingress on port 8443 SHALL remain unrestricted"; 8080 restricted to webapp).

## What Changes

- **Remove the host-port binding.** `jenkins-deployment.yaml` no longer sets
  `hostPort: 8443`. The container still listens on 8443 and the ClusterIP
  Service still exposes it; it is simply not published on the node.
- **NetworkPolicy allows the proxy and restricts 8443.** Ingress on 8080 is
  permitted from `webapp`, `proxy`, and `jenkins` pods. Ingress on 8443 is
  permitted from `jenkins` pods only — that port is used by the
  `nita-cmd jenkins …` scripts, which run `jenkins-cli.jar` inside the Jenkins
  pod via `kubectl exec` and connect to `https://jenkins:8443/jenkins/`.
- **Operator-facing text points at the proxy.** `install.sh`'s closing message
  and `docs/nita-examples.md` give `https://<host>/jenkins/` as the Jenkins
  URL. Stale `docker ps` output in `docs/containers.md` showing
  `0.0.0.0:8443->8443/tcp` is refreshed.
- **Spec is corrected.** The `kubernetes` capability's port-exposure and
  NetworkPolicy requirements are modified to match.

## Capabilities

### Modified Capabilities

- `kubernetes`: Jenkins is reachable from outside the cluster only through the
  proxy; the Jenkins NetworkPolicy admits the proxy pod on 8080 and confines
  8443 to the Jenkins pod.

## Impact

- **Files:** `k8s/jenkins-deployment.yaml`, `k8s/jenkins-network-policy.yaml`,
  `install.sh`, `docs/nita-examples.md`, `docs/containers.md`,
  `docs/pods.md` if it quotes the 8443 URL.
- **Operators:** bookmarks to `https://<host>:8443/` stop working after the
  next `apply-k8s.sh`; the replacement is `https://<host>/jenkins/`. No
  Jenkins data or job changes.
- **`nita-cmd jenkins …`:** unaffected. These commands exec into the Jenkins
  pod and talk to `jenkins:8443` from inside it, which the new policy permits.
- **No change** to `nita-jenkins` or `nita-webapp` images, to the Service
  manifest, or to certificates.
- **Companion changes:** `nita-webapp/gate-jenkins-behind-webapp-session`
  (session gate at the proxy) and
  `nita-jenkins/revoke-anonymous-build-and-enable-csrf` (Jenkins-side
  hardening). Deploy the hardening first, this networking change second, and
  the webapp session gate last. This removes anonymous build/cancel access
  before closing the direct route, and ensures proxy connectivity is ready
  before the gate is enabled.
