# NITA Integration – PAA Single‑Site Ansible

A short, practical guide for wiring the **Paragon Active Assurance (PAA) single‑site Ansible package** into **Juniper NITA** so your pipelines can deploy agents and trigger tests.

---

## 1) Overview

- **What you have**: an Ansible project that deploys PAA Test Agents to a Kubernetes cluster (`site_deploy.yml`, templated Deployments/Secrets/NADs).
- **What NITA brings**: a CI/CD wrapper (Jenkins + `nita-ansible` runner + Robot Framework) to provision, configure, test, and report.
- **Goal**: Add pipeline stages that (a) deploy PAA agents and (b) call the PAA REST API to run measurements and collect KPIs.

> This guide focuses on the minimal steps. For L2/Multus or multi‑cluster placement, see your main README’s advanced sections.

---

## 2) Prerequisites

- NITA installed and reachable (Jenkins up).
- Access to the **target Kubernetes cluster** (where agents will run). Jenkins must have a kubeconfig or in‑cluster RBAC.
- PAA Control Center **account/token/host**.
- Your **PAA Ansible project** in a Git repo Jenkins can clone (or mounted into the runner).

---

## 3) Quick Start (Jenkins pipeline)

1. **Create Jenkins credentials** (recommended):
   - `paa-account` (Secret Text) → PAA account name
   - `paa-token` (Secret Text) → PAA API token
   - `paa-host` (Secret Text) → e.g., `https://paa.example.com`
   - Optional: configure `KUBECONFIG` or in‑cluster permissions for Jenkins.

2. **Add a Jenkins Declarative Pipeline** (simplest working example):

```groovy
pipeline {
  agent any

  environment {
    PAA_ACCOUNT = credentials('paa-account')
    PAA_TOKEN   = credentials('paa-token')
    PAA_HOST    = credentials('paa-host')
    // Ensure KUBECONFIG points to the cluster where you want agents
    // env var can also be set by Jenkins pod or a secret mount
  }

  stages {
    stage('Checkout PAA Ansible') {
      steps {
        // Replace with your repo URL/branch
        git url: 'https://your.git/paa-single-site-ansible.git', branch: 'main'
      }
    }

    stage('Deploy PAA Agents') {
      steps {
        sh '''
          cd ansible
          ansible-galaxy collection install -r collections.yml
          ansible-playbook site_deploy.yml             -e k8s_kubeconfig=$KUBECONFIG             -e paa_account=$PAA_ACCOUNT             -e paa_token=$PAA_TOKEN             -e paa_host=$PAA_HOST             -e networks_enabled=false
        '''
      }
    }

    stage('Trigger PAA Test (example)') {
      steps {
        writeFile file: 'ansible/run_paa_test.yml', text: '''
        - hosts: local
          gather_facts: false
          vars:
            paa_host: "{{ lookup('env','PAA_HOST') }}"
            paa_token: "{{ lookup('env','PAA_TOKEN') }}"
          tasks:
            - name: Start a measurement (simplified example)
              uri:
                url: "{{ paa_host }}/rest/<measurements_endpoint>"
                method: POST
                headers:
                  Authorization: "Token {{ paa_token }}"
                  Content-Type: "application/json"
                body_format: json
                body:
                  name: "Build {{ lookup('env','BUILD_NUMBER') }} – smoke"
                  # TODO: fill with required fields from your PAA REST model
              register: start_resp

            - debug:
                var: start_resp.json
        '''
        sh 'ansible-playbook ansible/run_paa_test.yml'
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'ansible/*.yml', allowEmptyArchive: true
    }
  }
}
```

**Notes**
- Replace `<measurements_endpoint>` with your actual endpoint path from PAA REST (e.g., measurements or tasks in your deployment).
- Set `networks_enabled=true` only if your cluster has Multus/OVS/Whereabouts and you want L2 agents.
- Use Jenkins credentials for secrets; don’t hardcode tokens in the repo.

---

## 4) Run playbooks via `nita-ansible` CLI (alternative)

If you prefer the NITA runner shell for debugging:

```bash
# from your NITA control node or where nita-cmd is available
nita-cmd ansible cli
# inside the nita-ansible shell:
git clone https://your.git/paa-single-site-ansible.git
cd paa-single-site-ansible/ansible
ansible-galaxy collection install -r collections.yml
ansible-playbook site_deploy.yml   -e k8s_kubeconfig=$KUBECONFIG   -e paa_account=$PAA_ACCOUNT   -e paa_token=$PAA_TOKEN   -e paa_host=$PAA_HOST
```

> Ensure `$KUBECONFIG`, `$PAA_ACCOUNT`, `$PAA_TOKEN`, and `$PAA_HOST` are set in the environment or passed with `-e` flags.

---

## 5) Optional: Node placement & multi‑cluster

- To pin agents to specific nodes, parameterize `nodeSelector`/`tolerations` in the Deployment templates and set them via vars (e.g., `{ paa-role: l3 }`).  
- To target different clusters, pass `k8s_context` and/or separate vars files (`lab.yml`, `prod.yml`) and run the same playbook per site.

---

## 6) Troubleshooting

- **ImagePullBackOff** → verify image repo/tag and registry access; add imagePullSecrets if private.
- **RBAC errors** → reduce/adjust RBAC if you removed cluster‑admin; ensure the Jenkins SA can access the target namespace.
- **Agent not in Control Center** → check the init container log for registration errors; validate `paa_account/token/host`.
- **L2 interfaces missing** → confirm Multus/OVS/Whereabouts are installed in the cluster and `networks_enabled=true`.

---

## 7) Clean up

```bash
# remove everything by namespace
kubectl delete ns <paa_namespace>
```

---

**That’s it.** With the pipeline above, NITA will deploy PAA agents each run and can trigger a PAA measurement. Expand with Robot validation and richer PAA REST payloads as you progress.
