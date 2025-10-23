# Network Implementation and Test Automation (NITA) 23.12

Welcome to NITA 23.12

NITA is an open source platform for automating the building and testing of complex networks.

# Release Notes

The major change in this version is that all components now run within pods under the control of Kubernetes, rather than as Docker containers. Consequently we have updated some infrastructure as well as the ``nita-cmd`` CLI to support Kubernetes.

We have also tested extensively on Ubuntu version 22.04.03 LTS and AlmaLinux 9.3 Server, either of which is required if you wish to use the new ``install.sh`` script. We recommend that your system has at least 8GB of free memory and 20GB of storage space.

For a list of previous features, bug fixes and other release details, please look at the [NITA Webapp README](https://github.com/Juniper/nita-webapp/blob/22.8/README.md#217-new-features-and-bug-fixes).

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

## Environment Variables

The ``install.sh`` script uses several environment variables, which you can set in the parent shell beforehand if you want to use something other than the defaults. These variables are outlined in this table:

Environment Variable | Default Value | Meaning
---|---|---
``NITAROOT`` | ``/opt`` | Where to install the NITA repositories
``BINDIR`` | ``/usr/local/bin`` | Where to install executables such as ``nita-cmd``
``BASH_COMPLETION`` | ``/etc/bash_completion.d`` | Location of bash completion files
``K8SROOT`` | ``$NITAROOT/nita/k8s`` | Location of Kubernetes ``YAML`` files
``PROXY`` | ``$K8SROOT/proxy`` | Location of ``nginx`` configuration
``CERTS`` | ``$PROXY/certificates`` | Location of ``nginx`` certificate files
``JENKINS`` | ``$K8SROOT/jenkins`` | Location of Jenkins keys and certificate files
``KEYPASS`` | ``nita123`` | Passkey used to create self-signed Jenkins keys
``KUBEROOT`` | ``/etc/kubernetes`` | System location for Kubernetes configuration
``KUBECONFIG`` | ``$KUBEROOT/admin.conf`` | Location of user's Kubernetes configuration
``DEBUG`` | unset | Set it to true in the parent shell, to see additional output
``IGNORE_WARNINGS`` | unset | Set it to true in the parent shell if you want to install NITA and ignore any important warnings

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
The files ```db-service.yaml```, ```jenkins-service.yaml```, ```proxy-service.yaml``` and ```webapp-service.yaml``` are used to expose ports between the applications and to the outside world:
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
Other special considerations are configmaps for jenkins and its proxy:
```
kubectl create configmap jenkins-crt --from-file=/home/jcluser/nita-jenkins/certificates/jenkins.crt --namespace nita
kubectl create cm jenkins-keystore --from-file=/home/jcluser/nita-jenkins/certificates/jenkins_keystore.jks --namespace nita
kubectl create cm proxy-config-cm --from-file=/home/jcluser/nginx/nginx.conf --namespace nita
kubectl create cm proxy-cert-cm --from-file=/home/jcluser/nginx/certificates/ --namespace nita
```
as shown here:
```
jcluser@ubuntu:~$ kubectl get cm -n nita
NAME               DATA   AGE
jenkins-crt        1      52d
jenkins-keystore   1      52d
proxy-cert-cm      2      52d
proxy-config-cm    1      52d
```

# Troubleshooting

## Windows CRLF problems

In this section, we'll be going over a step by step tutorial on how to fix a common faiure when loading Nita projects from windows. This issue manifests when triggering an action for example 'build'.

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
$ git config --global core.autocrlf true
```

If that doesn't work you could try installing this version of git: https://git-scm.com/install/windows

Then you should make sure to follow this installation setup:

Once you've downloaded the setup for git bash, run it, the main bit you would need to check for the installation is the "Configuring the line ending conversions" for this option you would need to tick the "Checkout as-is, committ as-is" this will stop the text files from changing and will stay as it is. When you've ticked that box, you don't need to change the other boxes, install git. After installing that you can start by removing NITA and git-cloning NITA again. Once thats done the problem should be fixed.

# Getting Involved

We hope that you enjoy using NITA, and if you do, please give the code a star on GitHub. If you spot anything wrong please raise an Issue and if you want to contribute please raise a Pull Request on the work that you have done. You can find out more details about how to contribute by reading the [CONTRIBUTE.md](CONTRIBUTE.md) document.

# Copyright

Copyright 2024, Juniper Networks, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
