# NITA 22.8

Welcome to NITA 22.8.

NITA is an open source platform for automating the building and testing of complex networks.

# Release Notes

For a list of new features, bug fixes and other release details, please look at the [NITA Webapp README](https://github.com/Juniper/nita-webapp/blob/22.8/README.md#217-new-features-and-bug-fixes).

# History

NITA was developed by a small team of Professional Services consultants at Juniper Networks in 2015 and it has been fed and watered by them ever since. In 2020 it was open sourced and made available on GitHub to allow anyone in the industry to use for free and to contribute to if they wished.

# What Does NITA Do?

As a platform, NITA comprises some of the best Automation tools currently available, such as:

* Ansible, for configuration change management
* Jenkins, for automation and job control
* Robot Framework, for test automation
* Docker, for packaging and easy deployment

In a nutshell, NITA can be used as a toolbox from which you can automate the deployment and testing of very complex networks. It is vendor neutral and so can be used to build and test networks from all of the leading vendors in the market. And because it is a toolbox it can be extended to include any other tool that you may need.

# Examples

If you want to experiment to see what NITA can do, we currently have [3 example projects](https://github.com/Juniper/nita/tree/main/examples) that are provided in this repository:

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

# Installation

You have landed on the meta repository which links to all of the Juniper Networks NITA submodules on GitHub. Modules can be downloaded independently from these links:

* https://github.com/Juniper/nita-webapp
* https://github.com/Juniper/nita-ansible
* https://github.com/Juniper/nita-jenkins
* https://github.com/Juniper/nita-robot
* https://github.com/Juniper/nita-yaml-to-excel

Please refer to the README in each submodule for more details.

# Porting of Juniper NITA project to Kubernetes

The setup of the infrastructure pods is straightforward, and at the end of the setup we should have 4 running pods that are:
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
Other special considerations are configmaps for jenkins and its proxy:
```
kubectl create cm jenkins-keystore --from-file=/home/jcluser/nita-jenkins/certificates/jenkins_keystore.jks --namespace nita
kubectl create cm proxy-config-cm --from-file=/home/jcluser/nginx/nginx.conf --namespace nita
kubectl create cm proxy-cert-cm --from-file=/home/jcluser/nginx/certificates/ --namespace nita
```
as shown here:
```
jcluser@ubuntu:~$ kubectl get cm -n nita
NAME               DATA   AGE
jenkins-keystore   1      52d
proxy-cert-cm      2      52d
proxy-config-cm    1      52d
```

# Getting Involved

We hope that you enjoy using NITA, and if you do, please give the code a star on GitHub. If you spot anything wrong please raise an Issue and if you want to contribute please raise a Pull Request on the work that you have done. You can find out more details about how to contribute by reading the [CONTRIBUTE.md](CONTRIBUTE.md) document.

# Copyright

Copyright 2022, Juniper Networks, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
