## ADDED Requirements

### Requirement: Jenkins Port Isolation via NetworkPolicy
The system SHALL deploy a `NetworkPolicy` in the `nita` namespace that restricts
ingress to the Jenkins pod on port 8080 to only pods labelled
`io.kompose.service: webapp` in the same namespace. Ingress on port 8443 SHALL
remain unrestricted.

#### Scenario: Webapp pod can reach Jenkins on port 8080
- **WHEN** a request originates from the pod labelled `io.kompose.service: webapp`
  in the `nita` namespace and targets the Jenkins pod on port 8080
- **THEN** the connection is permitted

#### Scenario: Non-webapp pod cannot reach Jenkins on port 8080
- **WHEN** a request originates from any pod NOT labelled `io.kompose.service: webapp`
  and targets the Jenkins pod on port 8080
- **THEN** the connection is dropped by the NetworkPolicy

#### Scenario: Any pod can reach Jenkins on port 8443
- **WHEN** any pod in any namespace makes a request to the Jenkins pod on port 8443
- **THEN** the connection is permitted

#### Scenario: NetworkPolicy exists after apply
- **GIVEN** `apply-k8s.sh` has completed successfully
- **WHEN** `kubectl get networkpolicy -n nita` is run
- **THEN** a NetworkPolicy named `jenkins-network-policy` is listed

### Requirement: Declarative Jenkins Service Manifest
The Jenkins Service manifest SHALL contain no cluster-assigned immutable fields
(`clusterIP`, `clusterIPs`, `resourceVersion`, `uid`) so that `kubectl apply`
succeeds idempotently on any cluster.

#### Scenario: Jenkins service applies without error on a clean cluster
- **GIVEN** no prior NITA install on the cluster
- **WHEN** `kubectl apply -f k8s/jenkins-service.yaml` is run
- **THEN** the command exits with code 0 and the service is created
