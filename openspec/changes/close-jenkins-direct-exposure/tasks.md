## 1. Manifests

- [x] 1.1 Remove `hostPort: 8443` from the Jenkins container `ports` entry in `k8s/jenkins-deployment.yaml` (keep `containerPort: 8443`)
- [x] 1.2 In `k8s/jenkins-network-policy.yaml`, add a `podSelector` for `io.kompose.service: proxy` to the 8080 ingress rule
- [x] 1.3 In `k8s/jenkins-network-policy.yaml`, restrict the 8443 ingress rule to `podSelector: io.kompose.service: jenkins`

## 2. Operator documentation

- [x] 2.1 `install.sh`: closing message gives `https://${HOST}/jenkins/` for the Jenkins UI
- [x] 2.2 `docs/nita-examples.md`: replace the `:8443` URL with the `/jenkins/` path
- [x] 2.3 `docs/containers.md` / `docs/pods.md`: remove or refresh output that shows `0.0.0.0:8443->8443/tcp` or a `:8443` Jenkins URL

## 3. Verification

- [x] 3.1 `kubectl apply --dry-run=client` on both manifests succeeds
- [x] 3.2 `apply-k8s.sh` rolls out cleanly
- [x] 3.3 From outside the cluster, `https://<host>:8443/` is refused and `https://<host>/jenkins/` loads through the proxy
- [x] 3.4 `nita-cmd jenkins version` and `nita-cmd jenkins jobs ls` still succeed
- [x] 3.5 Webapp trigger, SSE console, and lifecycle history still work (webapp → `jenkins:8080` path unaffected)
- [x] 3.6 `openspec validate close-jenkins-direct-exposure --strict` passes
