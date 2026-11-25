# Network Implementation and Test Automation (NITA) 26.10

Welcome to NITA 26.10

NITA is an open source platform for automating the building and testing of complex networks.

# Release Notes

This release updates the NITA platform infrastructure to keep pace with
upstream dependency changes and strengthens reliability through readiness
probes, an expanded integration test suite, and improved CI diagnostics.

## 26.10

* New an revamped interface added to ``nita-webapp``

For a full list of webapp-level changes in this release, please refer to the
[NITA Webapp README](https://github.com/Juniper/nita-webapp/blob/main/README.md#2610).

## 26.5 New Features and Bug Fixes

* Upgraded MariaDB from 10.4.12 to 10.11, required by Django 5 and the
  updated ``nita-webapp``.
* Added ``readinessProbe`` to the webapp and database Kubernetes deployments
  so that Kubernetes only routes traffic once each pod is fully initialised.
* Fixed a missing ``get``, ``list`` and ``watch`` verb set in the
  ``modify-pods`` ClusterRole that prevented Jenkins from querying pod state.
* Added a full E2E API integration test suite (pytest) that runs against the
  deployed Kubernetes stack as part of CI, covering authentication, network
  type upload, network lifecycle and workbook operations.
* Upgraded all GitHub Actions steps to Node.js 24 native action versions.
* Improved CI diagnostic output on failure: rolling pod status, recent events,
  and the last 500 lines of webapp and Jenkins pod logs are now captured
  automatically when the integration tests fail.

We recommend Ubuntu 22.04 LTS or AlmaLinux 9.3 Server and at least 8 GB of
free memory and 20 GB of storage space.

For a full list of webapp-level changes in this release, please refer to the
[NITA Webapp README](https://github.com/Juniper/nita-webapp/blob/main/README.md#265-new-features-and-bug-fixes).

# Software Inventory

NITA provides a source-level SBOM and component/license manifest through the
Software Inventory workflow and new GitHub releases. See the
[software inventory guide](docs/software-inventory.md) for downloads, local
generation, maintenance, and coverage limitations.

# Installation

A new ``install.sh`` script is provided with this release, which makes it easy to install everything that you need in one go. It should work for most people in most cases, if you are running either Ubuntu 22.04 LTS or AlmaLinux 9.3 Server. Because the script can install required system dependencies you will need super user access to run it, either as ``root`` or as a user with ``sudo`` privileges. Simply download the raw script file from this GitHub repository, make it executable and then run it like this:

```
$ wget https://raw.githubusercontent.com/Juniper/nita/refs/heads/main/install.sh
$ chmod 755 install.sh
$ sudo -E ./install.sh
[sudo] password for user:
install.sh: NITA install script.
Install system dependencies (y|n|q)? [y]
.
.
.
```
Answer ``Y`` for each action that you want to perform, ``N`` to skip and ``Q`` to quit out of the script completely. Most people will just need to press enter (for ``Y``) and accept the defaults. Note that on a barebones system, you will need approximately 8GB of free storage in order to install NITA, which includes all of the system dependencies and the Kubernetes pods.

Package update and installation failures stop the installer. Debug output does
not include `KEYPASS`.

## Environment Variables

The ``install.sh`` script uses several environment variables, which you can set in the parent shell beforehand if you want to use something other than the defaults. These variables are outlined in this table:

Environment Variable | Default Value | Meaning
---|---|---
``NITAROOT`` | ``/opt`` | Where to install the NITA repositories
``BINDIR`` | ``/usr/local/bin`` | Where to install executables such as ``nita-cmd``
``BASH_COMPLETION`` | ``/etc/bash_completion.d`` | Location of bash completion files
``K8SROOT`` | ``$NITAROOT/nita/k8s`` | Location of Kubernetes ``YAML`` files
``PROXY`` | ``$K8SROOT/proxy`` | Parent directory for proxy certificates
``CERTS`` | ``$PROXY/certificates`` | Location of proxy certificate files
``JENKINS`` | ``/var/jenkins_home`` | Location of Jenkins keys and certificate files
``KEYPASS`` | ``nita123`` | Passkey used to create self-signed Jenkins keys
``KUBEROOT`` | ``/etc/kubernetes`` | System location for Kubernetes configuration
``KUBECONFIG`` | ``$KUBEROOT/admin.conf`` | Location of user's Kubernetes configuration
``CONTAINER_REGISTRY`` | ``ghcr.io/juniper`` | Registry namespace used to construct default NITA image references
``GITHUB_ORG`` | ``Juniper`` | GitHub organization used when cloning NITA repositories and configuration
``NITA_GIT_REF`` | ``main`` | NITA branch or tag to clone for installer manifests and scripts
``NITA_WEBAPP_IMAGE`` | ``ghcr.io/juniper/nita-webapp:latest`` | Complete Webapp image reference; a tag or digest is accepted
``NITA_JENKINS_IMAGE`` | ``ghcr.io/juniper/nita-jenkins:latest`` | Complete Jenkins image reference; a tag or digest is accepted
``NITA_ANSIBLE_IMAGE`` | ``ghcr.io/juniper/nita-ansible:latest`` | Complete Ansible worker image reference passed into Jenkins
``NITA_ROBOT_IMAGE`` | ``ghcr.io/juniper/nita-robot:latest`` | Complete Robot worker image reference passed into Jenkins
``JUNOS_MCP_IMAGE`` | ``ghcr.io/juniper/junos-mcp-server:latest`` | Complete optional Junos MCP image reference
``JUNOS_MCP_DEVICES`` | ``$NITAROOT/nita/examples/mcp/devices.json`` | Default device mapping file for optional Junos MCP server pod
``JUNOS_MCP_TOKEN_ID`` | ``nita-lab`` | Internal MCP token identifier
``JUNOS_MCP_TOKEN_VALUE`` | generated | Internal MCP token; existing installations retain their token
``JUNOS_MCP_ROTATE`` | ``false`` | Set to ``true`` with a new token value to rotate the MCP token
``DEBUG`` | unset | Set it to true in the parent shell, to see additional output
``IGNORE_WARNINGS`` | unset | Set it to true in the parent shell if you want to install NITA and ignore any important warnings

When preparing the proxy certificate, the installer reuses a valid certificate
and key in `CERTS`. If those files are missing, it attempts to restore the
existing pair from the Traefik TLS Secret or the legacy `proxy-cert-cm`.
If a proxy deployment exists but no usable
pair can be found, installation stops rather than replacing its certificate.
The installer stores the pair in the `nita-traefik-tls` TLS Secret.

### Traefik migration and rollback

The main proxy uses Traefik v3.7.19 with the dedicated `nita-traefik`
IngressClass and retains `deployment/proxy` and host port 443. Install a
webapp image that implements the Traefik forward-auth contract together with
this proxy; older webapp images and the new proxy are not compatible. Before
upgrading, back up the running proxy and webapp Deployment manifests and image
references, the existing proxy configuration and TLS resources, and the MCP
Deployment and Secret if MCP is installed:

```shell
python3 k8s/backup-proxy.py nita-proxy-backup
```

Use a new backup directory for each upgrade. The backup includes existing
Nginx and Traefik resources, strips server-managed fields, and fails if a
referenced proxy resource is missing. Restrict access to the backup: it
contains private keys and tokens.

Run the new installer from a checkout containing this migration and select a
compatible `NITA_WEBAPP_IMAGE`. The installer does not update an existing
`$NITAROOT/nita` checkout; update that checkout separately or point `K8SROOT`
at the new checkout's `k8s` directory. Answer yes to installing NITA
repositories to apply the main-proxy migration, and yes to the MCP prompt only
if MCP is installed or desired. `NITA_GIT_REF` affects fresh clones only.

The installer preserves the old Nginx ConfigMaps and MCP Secret for rollback.
The proxy changes require a brief interruption because only one pod can bind
host port 443. It waits for the rollout and checks the certificate, webapp
route, and anonymous Jenkins login redirect. If validation fails, restore the
backed-up Nginx proxy and the compatible old webapp Deployment together with
the commands below. If MCP was migrated, restore its Secret, ConfigMap and
Deployment separately. Do not remove the old resources before confirming the
migration.

```shell
kubectl apply -f nita-proxy-backup/proxy-and-webapp.json
kubectl rollout status deployment/webapp -n nita
kubectl rollout status deployment/proxy -n nita
# When rolling MCP back:
kubectl apply -f nita-proxy-backup/mcp.json
kubectl rollout status deployment/junos-mcp -n nita
```

For an intentional certificate replacement, validate
the new pair, update the files in `CERTS`, then update `nita-traefik-tls` with
the commands below. The installer rejects a certificate that differs from the
currently active proxy certificate.

```shell
kubectl create secret tls nita-traefik-tls -n nita \
  --cert="$CERTS/nginx-certificate.crt" --key="$CERTS/nginx-certificate-key.key" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/proxy -n nita
kubectl rollout status deployment/proxy -n nita
```

The five image variables are complete references, not tag fragments. This
allows components to be selected independently and supports immutable pins:

```shell
export NITA_WEBAPP_IMAGE=ghcr.io/juniper/nita-webapp:sha-0123456789ab
export NITA_JENKINS_IMAGE=ghcr.io/juniper/nita-jenkins@sha256:<digest>
sudo -E ./install.sh
```

For a coordinated CI test before the compatible webapp image is published,
manually run the NITA CI workflow with `webapp_repository` set to the public
companion repository (`owner/repo`) and `webapp_ref` set to its full commit
SHA. CI builds that revision locally and loads the image into Kind; it does not
publish it. Leave both inputs empty to test the published image selected by the
`NITA_WEBAPP_IMAGE` repository variable or its default. This source-build
verification does not replace testing the final published release image.

## Container Images and Architectures

The component workflows publish official NITA images from the Juniper source
repositories to GHCR as multi-platform manifests for `linux/amd64` and
`linux/arm64`. Existing canonical `latest` packages may remain amd64-only until
the corresponding publisher changes land and run on upstream `main`.
`latest` follows the upstream `main` branch, `sha-<short-commit>` identifies an
immutable source build, and an intentionally pushed Git tag is published under
that exact tag. Release tags must already be valid Docker tags: 1-128 ASCII
letters, digits, underscores, periods, or dashes, starting with a letter,
digit, or underscore. The workflow rejects incompatible Git tags instead of
silently changing them. The scheduled Junos MCP image uses
`source-<upstream-sha>-run-<workflow-run-id>` because its contents follow a
separate upstream repository. `VERSION.txt` remains application and local-build
metadata; CI does not edit it or use it to tag images.

Once the canonical manifests contain real ARM application images, the
multi-platform images support ARM Kubernetes workloads. The upstream ARM Kind
job remains gated until then. The complete NITA host installation remains
officially tested on x86_64, and `install.sh` retains its warning on other host
architectures while ARM hosted-runner support remains experimental. See
[Containers](docs/containers.md) and
[Custom Containers](docs/custom-containers.md) for image inspection and
override examples.

## Optional: Junos MCP Server

NITA can optionally install a [Junos Model Context Protocol (MCP) server](https://github.com/Juniper/junos-mcp-server) as a Kubernetes pod that runs on port 8090. This MCP server provides a bridge between LLM-compatible clients (such as Claude Desktop or VSCode with GitHub Copilot) and Juniper Junos network devices.

During the ``install.sh`` execution, you will be prompted:

```
Install Junos MCP server pod on port 8090 (y|n|q)? [y]
```

If you answer ``Y``, the installer will:

1. Select ``$JUNOS_MCP_IMAGE`` (default: ``ghcr.io/juniper/junos-mcp-server:latest``)
2. Create a ConfigMap from the default device mapping file at ``$JUNOS_MCP_DEVICES`` (default: ``/opt/nita/examples/mcp/devices.json``)
3. Generate or reuse an internal MCP token and Traefik proxy configuration
4. Deploy the MCP server pod and service in the ``nita`` namespace, listening on port 8090; Kubernetes pulls the selected image when needed

For the packaged NITA lab/demo deployment, the MCP backend stays token-protected on loopback inside the pod and a Traefik sidecar listens on port 8090, injecting the internal token on behalf of clients. External access is unauthenticated HTTP and is suitable only for trusted lab/demo networks.

### Default Device List

The Junos MCP server uses a default device list located at ``examples/mcp/devices.json``. This file contains sample device configurations that the MCP server can interact with. You can customize this list by:

- Editing the file directly before installation
- Providing an alternative file path via the ``JUNOS_MCP_DEVICES`` environment variable
- Updating the ConfigMap after installation using:
  ```
  kubectl delete cm junos-mcp-devices-cm -n nita
  kubectl create cm junos-mcp-devices-cm --from-file=devices.json=/path/to/your/devices.json -n nita
  kubectl rollout restart deploy/junos-mcp -n nita
  ```

### Verifying the MCP Server

After installation, verify that the Junos MCP server is running:

```
# Check deployment status
kubectl -n nita get deploy junos-mcp -o wide

# Check pod status
kubectl -n nita get pods -l app=junos-mcp -o wide

# Check service endpoint (accessible on node IP port 8090)
kubectl -n nita get svc junos-mcp -o wide

# View server logs
kubectl -n nita logs deploy/junos-mcp --tail=100

# View proxy logs
kubectl -n nita logs deploy/junos-mcp -c junos-mcp-proxy --tail=100
```

The MCP server will be accessible at ``http://<node-ip>:8090/mcp/`` from any client on the network.

The upstream MCP server still enforces token authentication on its streamable HTTP transport. NITA hides that token behind the in-pod proxy for lab/demo installs. If you prefer explicit client authentication instead, replace the proxy flow with a mounted ``.tokens`` file and send ``Authorization: Bearer <token>`` from the client.

### Refreshing MCP Auth And Proxy Resources

Rerun the optional MCP installation to reuse its existing token. To rotate it,
set `JUNOS_MCP_ROTATE=true` and `JUNOS_MCP_TOKEN_VALUE` to the new value
in the installer environment; the installer updates the single Secret used by
both containers and restarts the pod. Avoid exposing token values in shell
history or logs. If a rollout fails, restore the backed-up MCP Deployment and
matching Secret and wait for readiness. Clients still connect to
``http://<node-ip>:8090/mcp/`` without an Authorization header.

# History

NITA was developed by a small team of Professional Services consultants at Juniper Networks in 2015 and it has been fed and watered by them ever since. In 2020 it was open sourced and made available on GitHub to allow anyone in the industry to use for free and to contribute to if they wished.

# What Does NITA Do?

As a platform, NITA comprises some of the best Automation tools currently available, such as:

* Ansible, for configuration change management
* Jenkins, for automation and job control
* Robot Framework, for test automation
* Kubernetes, for container orchestration

In a nutshell, NITA can be used as a toolbox from which you can automate the deployment and testing of very complex networks. It is vendor neutral and so can be used to build and test networks from all of the leading vendors in the market. And because it is a toolbox it can be extended to include any other tool that you may need.

Here is a short video declaring how NITA can be used in your project, please follow the link:
[YouTube|NITA](https://www.youtube.com/watch?v=6edtVe8Ueis)

# Example Projects

If you want to experiment to see what NITA can do, we currently have [3 example projects](https://github.com/Juniper/nita/tree/main/examples) that are provided in this repository, please proceed to review the [Examples README](https://github.com/Juniper/nita/tree/main/docs/nita-examples.md) to familiarise yourself with NITA Webapp usage:

* [ChatGPT Integration with Robot and Jenkins](https://github.com/Juniper/nita/tree/main/examples/chatgpt).

    Ever needed help investigating why an automated test has failed? This example will send failed test case descriptions to ChatGPT and ask for the top suggestions on how to solve them. All of a sudden, you will look like a genius!

* Build and test an [EVPN VXLAN data centre using Juniper QFX devices](https://github.com/Juniper/nita/tree/main/examples/evpn_vxlan_erb_dc)

    This includes all of the config that you need to build the data centre fabric and VXLAN overlay along with 14 example Robot tests for the firewalls, switches, BGP leaf and spine devices and end IP connectivity.
We show integration with other operational tools for "Day 2 Management", storing inventory in Netbox and having that push changes to the network via the Juniper Paragon Insights product.

* Build and test a [Simple DC WAN topology based on IPCLOS and eBGP](https://github.com/Juniper/nita/tree/main/examples/ebgp_wan)

    This is between 2 example datacentres, with 13 example Robot tests for border leaf routers, DC spines and WAN PE devices, plus BGP and IP connectivity tests.

# Training

If you are planning on using NITA or any of the technologies related to NITA then please consider following the Juniper Networks Automation and DevOps Learning Path
and taking the Junos Platform and Automation training courses.  These will give you the essential knowledge you need to do successful network automation! For more information, please see the link below:

https://learningportal.juniper.net/juniper/user_activity_info.aspx?id=10840

# Other NITA Repositories

You have landed on the meta repository which links to all of the Juniper Networks NITA submodules on GitHub. Modules can be downloaded independently from these links:

* https://github.com/Juniper/nita-webapp
* https://github.com/Juniper/nita-ansible
* https://github.com/Juniper/nita-jenkins
* https://github.com/Juniper/nita-robot
* https://github.com/Juniper/nita-yaml-to-excel

Please refer to the README in each submodule for more details.

# Porting NITA to Kubernetes

This section gives some details of the pods used in NITA, which you may find helpful if you want to go off-piste. The setup of the infrastructure pods is straightforward, and at the end of the setup we should have 4 running pods that are:
```
kubectl get pods -n nita
NAME                      READY   STATUS    RESTARTS       AGE
db-6878b6446-gk6rs        1/1     Running   5 (3d1h ago)   52d
jenkins-577757858-jqvg5   1/1     Running   0              4h56m
proxy-6d75b768bc-kpdpr    1/1     Running   7 (3d1h ago)   52d
webapp-67d64dbb99-pfrb9   1/1     Running   0              25h
```
The files ```pv.yaml``` and ```pv2.yaml``` create persistent volumes for Jenkins and MariaDB pods, which are claimed with the files ```jenkins-home-persistenvolumeclaime.yaml``` and ```mariadb-persistentvolumeclaim.yaml```:

```
jcluser@ubuntu:~$ kubectl get pv -n nita
NAME             CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                  STORAGECLASS   REASON   AGE
pv-volume        2Gi        RWO            Retain           Bound    default/mariadb        manual                  52d
task-pv-volume   20Gi       RWO            Retain           Bound    default/jenkins-home   manual                  52d
```
and
```
jcluser@ubuntu:~$ kubectl get pvc -n nita
NAME           STATUS   VOLUME           CAPACITY   ACCESS MODES   STORAGECLASS   AGE
jenkins-home   Bound    task-pv-volume   20Gi       RWO            manual         52d
mariadb        Bound    pv-volume        2Gi        RWO            manual         52d
```
The files ```jenkins-deployment.yaml```, ```db-deployment.yaml```, ```proxy-deployment.yaml``` and ```webapp-deployment.yaml``` are used to spin the actual deployments of the containers:
```
jcluser@ubuntu:~$ kubectl get deployments -n nita
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
db        1/1     1            1           52d
jenkins   1/1     1            1           5h21m
proxy     1/1     1            1           52d
webapp    1/1     1            1           25h
```
The Services expose the application ports inside the cluster. Traefik listens
on host port 443 and routes via the NITA Ingress resources:
```
jcluser@ubuntu:~$ kubectl get services -n nita
NAME         TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE
db           ClusterIP   10.109.37.245   <none>        3306/TCP            52d
jenkins      ClusterIP   10.104.250.46   <none>        8443/TCP,8080/TCP   52d
webapp       ClusterIP   10.108.92.21    <none>        8000/TCP            52d
```
The files ```role.yaml```, ```role-binding.yaml``` and ```service-account.yaml``` allow the jenkins pod to make API calls with ```kubectl``` to the host kubernetes engine:
```
jcluser@ubuntu:~$ kubectl get role
NAME          CREATED AT
modify-pods   2023-08-22T13:17:17Z
```
and:
```
jcluser@ubuntu:~$ kubectl get sa
NAME                   SECRETS   AGE
default                0         52d
internal-jenknis-pod   0         52d
```
To be able to use the nita-cli Jenkins commands we have to extract the crt from the jenkins_keystore create a Kubernetes configMap and the jenkins-deployment yaml will load that at pod initialization.
First create a jenkins_keystore if you did not create one previously:
```
keytool -genkey -keyalg RSA -alias selfsigned -keystore jenkins_keystore.jks -keypass nita123 -storepass nita123 -keysize 4096 -dname "cn=jenkins, ou=, o=, l=, st=, c="
keytool -importkeystore -srckeystore jenkins_keystore.jks -destkeystore jenkins.p12 -deststoretype PKCS12
openssl pkcs12 -in jenkins.p12 -nokeys -out jenkins.crt
```
Create the Jenkins ConfigMaps, then prepare the Traefik ConfigMaps and TLS
Secret before applying the workloads:
```
kubectl create configmap jenkins-crt --from-file=/home/jcluser/nita-jenkins/certificates/jenkins.crt --namespace nita
kubectl create cm jenkins-keystore --from-file=/home/jcluser/nita-jenkins/certificates/jenkins_keystore.jks --namespace nita
export CERTS=/path/to/proxy/certificates
bash k8s/prepare-traefik.sh
```
as shown here:
```
jcluser@ubuntu:~$ kubectl get cm -n nita
NAME               DATA   AGE
jenkins-crt        1      52d
jenkins-keystore   1      52d
nita-traefik-config        2      1m
nita-traefik-bodylimit     3      1m
nita-traefik-identityguard 3      1m
```

# Troubleshooting

## Windows CRLF problems

In this section, we'll be going over a step by step tutorial on how to fix a common failure when loading Nita projects from windows. This issue manifests when triggering an action for example 'build'.

Heres an example of the problem occuring during the dump action for the WAN example:
```
Started by user unknown or anonymous
Running as SYSTEM
Building in workspace /project/ebgp_wan_0.3-WAN
Copying file to data.json
[ebgp_wan_0.3-WAN] $ /bin/sh -xe /tmp/jenkins12043159907366045566.sh
+ write_yaml_files.py
+ python3 create_ansible_job_k8s.py dump juniper/nita-ansible:22.8-2
+ kubectl apply -f dump.yaml
job.batch/dump created
+ kubectl wait --for=jsonpath={.status.ready}=1 job/dump
error: timed out waiting for the condition on jobs/dump
Build step 'Execute shell' marked build as failure
Finished: FAILURE
```
This occurs because windows uses a different format for text files.

If you are editing files on a Windows platform, take care not to introduce DOS-style line endings. If you're using git, the following command can be used to tell git not to use CRLF:

```
$ git config --global core.autocrlf false
```

If that doesn't work you could try installing this version of git: https://git-scm.com/install/windows

Then you should make sure to follow this installation setup:

Once you've downloaded the setup for git bash, run it, the main bit you would need to check for the installation is the "Configuring the line ending conversions" for this option you would need to tick the "Checkout as-is, commit as-is" this will stop the text files from changing and will stay as it is. When you've ticked that box, you don't need to change the other boxes, install git. After installing that you can start by removing NITA and git-cloning NITA again. Once thats done the problem should be fixed.

# Getting Involved

We hope that you enjoy using NITA, and if you do, please give the code a star on GitHub. If you spot anything wrong please raise an Issue and if you want to contribute please raise a Pull Request on the work that you have done. You can find out more details about how to contribute by reading the [CONTRIBUTE.md](CONTRIBUTE.md) document.

# Copyright

Copyright 2024, Juniper Networks, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
