# Paragon Active Assurance – Single‑Site Ansible Package

This repository provides a **clean, single‑site** deployment of **Paragon Active Assurance (PAA) Test Agents** on Kubernetes using **Ansible**.  
All organization-, tenant-, and site‑specific names are with **standard and configurable variables**.

---

## What is Paragon Active Assurance (PAA)?

**Paragon Active Assurance** (formerly Netrounds) is a service and network assurance solution. It uses **software Test Agents** to generate synthetic traffic and measure real user experience (latency, jitter, loss, throughput, DNS/HTTP/DHCP performance, etc.) across L2/L3 networks and services. Agents register to a **PAA Control Center** (SaaS or on‑prem), where you design tests, run campaigns, and visualize results.

This package deploys **containerized Test Agents** into your Kubernetes cluster so they can register to your Control Center and execute active tests:
- **L3 Agent** – works out‑of‑the‑box with the cluster’s default CNI; no special networking required.
- **L2 Agents (optional)** – attach to additional data‑plane networks using Multus + OVS‑CNI + Whereabouts to run L2 tests (e.g., VLAN‑based).

> You will still need credentials and access to a **PAA Control Center** in order to create tests and dashboards. This package does **not** install the Control Center itself.

---

## Contents

```
ansible/
  ansible.cfg
  collections.yml
  group_vars/
    site.yml               # Main configuration (edit this)
  inventories/
    site/
      hosts.ini            # Localhost inventory
  roles/
    paa_site/
      templates/
        deployment-l3.yaml.j2
        deployment-l2-0.yaml.j2
        deployment-l2-1.yaml.j2
        nad-ovs-a.yaml.j2
        nad-ovs-b.yaml.j2
  site_deploy.yml          # One playbook to deploy everything
README.md                  # This file
```

---

## Requirements

- **Kubernetes** cluster with `kubectl` access and a working kubeconfig (default: `~/.kube/config`).
- **Python 3.8+**, **pip**, and **Ansible** on your workstation or a jump host.
- **Ansible collections**: `kubernetes.core` (pulled via `ansible/collections.yml`).
- **PAA Control Center** account/token/host URL.
- *(Optional for L2)* **Multus**, **OVS‑CNI**, and **Whereabouts** already installed in the cluster.

> If you don’t have Multus/OVS/Whereabouts, set `networks_enabled: false` in `group_vars/site.yml` and deploy only the L3 agent.

---

## Quick Install (TL;DR)

```bash
# 1) Install Ansible and the Kubernetes collection
pip install --upgrade pip ansible
ansible-galaxy collection install -r ansible/collections.yml

# 2) Edit variables (namespace, credentials, toggles, VLANs/IPAM if needed)
$EDITOR ansible/group_vars/site.yml

# 3) Run the playbook
cd ansible
ansible-playbook site_deploy.yml
```

Verify:
```bash
kubectl -n <paa_namespace> get deploy,po
kubectl -n <paa_namespace> logs deploy/paa-agent-l3 --tail=100
```

---

## Step‑by‑Step Installation

### 1) Prepare your environment
- Ensure `kubectl get nodes` works and your context points to the target cluster.
- Install Ansible and the required collection:
  ```bash
  pip install ansible
  ansible-galaxy collection install -r ansible/collections.yml
  ```

### 2) Configure variables
Edit **`ansible/group_vars/site.yml`** (this is your only required edit). Key fields:
- `paa_namespace`: Kubernetes namespace for agents (default: `paa`).
- `paa_service_account`: ServiceAccount name for agents (default: `paa-sa`).  
- `k8s_kubeconfig`: Path to kubeconfig (default: `~/.kube/config`).
- `paa_account`, `paa_token`, `paa_host`: Credentials/endpoint for your PAA Control Center.
- `paa_image_repo`, `paa_image_tag`: Container image location/tag. Defaults to Docker Hub:
  - `netrounds/test-agent-application:4.4.3.26`
- `networks_enabled`: `true` to create NADs and deploy L2 agents; `false` to deploy only L3.
- `vlan_a`, `vlan_b`, `ipam_a_cidr`, `ipam_b_cidr`, `ipam_excludes`: Only used when `networks_enabled: true`.
- `resources`: CPU/memory requests/limits per agent class (L2/L3).

### 3) Understand what will be created
The playbook will:
- Create the namespace, ServiceAccount, and a **ClusterRoleBinding** (default: `cluster-admin` for simplicity; see *Security Hardening* below).
- Create a `Secret` named `paa-user` with your ACCOUNT/TOKEN/HOST.
- *(If `networks_enabled: true`)* create two NetworkAttachmentDefinitions (`ovs-vlan-a`, `ovs-vlan-b`) using OVS + Whereabouts.
- Deploy **one L3 agent** and **two L2 agents** (replicas configurable).

### 4) Deploy
```bash
cd ansible
ansible-playbook site_deploy.yml
```

### 5) Post‑deployment checks
```bash
# List resources
kubectl -n <paa_namespace> get all

# Check agent pod logs (registration, connectivity)
kubectl -n <paa_namespace> logs deploy/paa-agent-l3 --tail=100

# If L2 enabled, verify additional networks are attached
kubectl -n <paa_namespace> get net-attach-def
kubectl -n <paa_namespace> describe po -l app=paa-agent-l2-0
kubectl -n <paa_namespace> describe po -l app=paa-agent-l2-1
```

### 6) Confirm registration in Control Center
Log into your **PAA Control Center**, navigate to **Agents**, and verify the new agents appear. You can now create tests (e.g., throughput, latency, HTTP, DNS) that target these agents.

---

## Security Hardening (RBAC)

For simplicity, this package binds the ServiceAccount to `cluster-admin`. In production, restrict to the minimum required verbs on namespaces where agents run. As a starting point, replace the ClusterRoleBinding with a namespaced Role/RoleBinding that allows management of:
- Pods/Deployments/Secrets/ConfigMaps/ServiceAccounts in the PAA namespace
- (If Multus) access to `k8s.cni.cncf.io` NetworkAttachmentDefinitions in the namespace

> Tailor this carefully to your environment’s policies and admission controllers.

---

## Networking Modes

- **L3 mode (default)**: Uses the cluster’s primary CNI only. No special configuration required. Suitable for IP‑layer and application tests.
- **L2 mode (optional)**: Adds two attached networks via **Multus + OVS‑CNI + Whereabouts** so the agents can participate in VLAN‑tagged L2 tests.
  - Ensure OVS bridge and CNI are already configured in the cluster.
  - Set `networks_enabled: true` and adjust VLANs/IPAM in `site.yml`.

> If you don’t need L2 tests, set `networks_enabled: false` to keep things simpler.

---

## Upgrade, Scale, and Removal

- **Change image or resources**: edit `group_vars/site.yml` and re‑run the playbook.
- **Scale replicas**: adjust `replicas_l3`, `replicas_l2_0`, `replicas_l2_1` and re‑run.
- **Remove everything**: delete the namespace or use kubectl:
  ```bash
  kubectl delete ns <paa_namespace>
  ```

---

## Troubleshooting

- **ImagePullBackOff**: ensure the image repo/tag is reachable from the cluster. If using a private registry, add an ImagePullSecret and reference it in the templates.
- **Registration fails (HTTP/401/403/TLS)**:
  - Verify `paa_account`, `paa_token`, `paa_host` in `paa-user` secret.
  - If using self‑signed certs, the init container uses `--tls-no-check`. Consider trusting a custom CA instead for production.
- **No additional interfaces for L2 pods**:
  - Confirm Multus/OVS/Whereabouts are installed and `networks_enabled: true`.
  - Check `NetworkAttachmentDefinition` objects exist in the PAA namespace.
- **RBAC denied**: if you removed `cluster-admin`, ensure your custom Role/RoleBinding grants the needed verbs on the affected resources.
- **Resources Insufficient**: increase node capacity or lower `resources` in `site.yml`.

---

## FAQ

**Q: Does this deploy the PAA Control Center?**  
A: No. This only deploys **Test Agents** that register to your existing Control Center.

**Q: Can I run only the L3 agent?**  
A: Yes. Set `networks_enabled: false` and the playbook will skip L2 agents and NADs.

**Q: Where do I see results?**  
A: In the **PAA Control Center** web UI (or APIs). Create tests/campaigns targeting these agents.

**Q: Can I pin agents to specific nodes?**  
A: Add `nodeSelector`/`tolerations` in the deployment templates as needed.

---

## Glossary

- **Agent**: Containerized probe that generates traffic and measures KPIs.
- **Control Center**: Management plane where agents register and tests are orchestrated.
- **Multus**: CNI meta‑plugin allowing multiple network interfaces per pod.
- **OVS‑CNI**: CNI plugin to attach pods to Open vSwitch bridges (optionally with VLANs).
- **Whereabouts**: IPAM plugin that assigns IPs from a pool to secondary interfaces.

---

## Support & Contributions

This package is provided as a **standardized, vendor‑neutral** starting point. Open PRs/issues in your internal repository or share improvement ideas (e.g., SR‑IOV samples, custom RBAC, private registry support).

