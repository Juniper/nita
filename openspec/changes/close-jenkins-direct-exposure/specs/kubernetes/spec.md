## MODIFIED Requirements

### Requirement: Services and Port Exposure
The system SHALL expose the webapp on port 8000, Jenkins on ports 8080 and 8443, and the
proxy on ports 443 (HTTPS) and 8000 within the cluster. Only the proxy SHALL be
published on the node (host port 443). The Jenkins container SHALL NOT bind a
host port; external access to Jenkins SHALL be available exclusively through the
proxy at `https://<host>/jenkins/`.

#### Scenario: Webapp service reachable
- GIVEN the webapp deployment and service are applied
- WHEN an in-cluster request is made to the webapp service on port 8000
- THEN a valid HTTP response is returned

#### Scenario: Jenkins is not published on the node
- GIVEN the Jenkins deployment is applied
- WHEN a client outside the cluster connects to `https://<node-ip>:8443/`
- THEN the connection is refused

#### Scenario: Jenkins is reachable through the proxy
- GIVEN the proxy and Jenkins deployments are applied
- WHEN a client outside the cluster requests `https://<node-ip>/jenkins/`
- THEN the request is served by Jenkins via the proxy

### Requirement: Jenkins Port Isolation via NetworkPolicy
The system SHALL deploy a `NetworkPolicy` in the `nita` namespace that restricts
ingress to the Jenkins pod on port 8080 to pods labelled
`io.kompose.service: webapp`, `io.kompose.service: proxy`, or
`io.kompose.service: jenkins` in the same namespace, and restricts ingress on
port 8443 to pods labelled `io.kompose.service: jenkins` only.

#### Scenario: Webapp pod can reach Jenkins on port 8080
- GIVEN the NetworkPolicy is applied
- WHEN a request originates from the pod labelled `io.kompose.service: webapp`
  in the `nita` namespace and targets the Jenkins pod on port 8080
- THEN the connection is permitted

#### Scenario: Proxy pod can reach Jenkins on port 8080
- GIVEN the NetworkPolicy is applied
- WHEN a request originates from the pod labelled `io.kompose.service: proxy`
  in the `nita` namespace and targets the Jenkins pod on port 8080
- THEN the connection is permitted

#### Scenario: Non-webapp pod cannot reach Jenkins on port 8080
- WHEN a request originates from any pod NOT labelled `webapp`, `proxy`, or `jenkins`
  and targets the Jenkins pod on port 8080
- THEN the connection is dropped by the NetworkPolicy

#### Scenario: Jenkins pod can reach its own port 8443
- GIVEN the NetworkPolicy is applied
- WHEN `jenkins-cli.jar` is executed inside the Jenkins pod against `https://jenkins:8443/jenkins/`
- THEN the connection is permitted

#### Scenario: Any pod can reach Jenkins on port 8443
- WHEN a request originates from any pod NOT labelled `io.kompose.service: jenkins`
  and targets the Jenkins pod on port 8443
- THEN the connection is dropped by the NetworkPolicy (the former unrestricted 8443 ingress is withdrawn)

#### Scenario: NetworkPolicy exists after apply
- GIVEN `apply-k8s.sh` has completed successfully
- WHEN `kubectl get networkpolicy -n nita` is run
- THEN a NetworkPolicy named `jenkins-network-policy` is listed
