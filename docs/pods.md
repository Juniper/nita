# NAME

``pods``. Almost everything you need to know about the pods used by NITA.

# SYNOPSIS

``nita-cmd kube [ pods | versions ] ``\
``nita-cmd [ ansible | jenkins | robot | webapp ] cli <args>...``\
``kubectl [ get | exec | describe ]``

# DESCRIPTION

NITA is packaged and executed as a series of Kubernetes pods, which communicate with one another via an Kubernetes component in charge of networking, Calico. There are four custom containers, 
Ansible, Jenkins, Robot and the NITA Webapp, and two standard containers for Nginx and MariaDB. Jenkins, Webapp, Proxy and DB are persistent 
(which means that they run continuously) whereas Ansible and Robot are ephemeral (i.e. they are started and stopped as and when required). 
The move from older NITA version that was running on Docker to the new Kubernetes infrastructure will allow new improvements 
of the product while also alowing the user to expand the functionality of the solution themselves.

# EXAMPLES

There are many ways in which you can control and troubleshoot pods operations with NITA, using either the ``nita-cmd`` or ``kubectl`` commands. 
This section shows some of the most useful examples that you should know.

# The Kubectl Client

The ``kubectl`` binary is a client for interacting with the ``kubelet`` daemon through a command line interface. It has commands that allow you to control and troubleshoot pods operations in detail. 
You can use the ``kubectl`` client directly from the shell of the NITA host server. 
For example, if you want to list the running containers you can use ``kubectl get pods -n nita``, like this:

```shell
$ kubectl get pods -n nita
NAME                       READY   STATUS    RESTARTS       AGE
db-7cc98cd974-t4ppb        1/1     Running   3 (128m ago)   90d
jenkins-768f9cd99b-fprh8   1/1     Running   3 (128m ago)   90d
proxy-86dfdffcf5-zqzmq     1/1     Running   3 (128m ago)   90d
webapp-75d694ff55-xk252    1/1     Running   3 (128m ago)   90d
```
Here you can see the two persistent NITA pods (Jenkins and the Webapp) plus pods for the Nginx webserver and the Maria SQL database. 

The trouble is that the ``kubectl`` client has a lot of options (type ``kubectl help`` to see what options are available) and this can make it complicated to use. 
Therefore we have provided a number of shortcuts for the most useful options with the ``nita-cmd`` command, as outlined below. 

## The ``nita-cmd`` Command

### ``nita-cmd kube ...``

You can use the ``nita-cmd kube pods`` command to get information about the infrastructure components used by NITA. The following options are supported:

| Command | Description |
|---|---|
|``nita-cmd kube pods`` | List all running NITA pods |
|``nita-cmd kube nodes`` | List all nodes in the Kubernetes clsuter |
|``nita-cmd kube cm`` | List all configured config-maps |
|``nita-cmd kube ns all`` | List all configured namespaces |

If you read the nita-cmd documentation you will see that it is in fact just a wrapper for other shell scripts. When you run the ``nita-cmd kube pods`` command, 
it is actually running the ``kubectl get pods -n nita`` command and filtering the output. For example, to see what pods are currently running on the NITA host, do this:

```
$ nita-cmd kube pods 
NAME                       READY   STATUS    RESTARTS       AGE
db-7cc98cd974-t4ppb        1/1     Running   3 (132m ago)   90d
jenkins-768f9cd99b-fprh8   1/1     Running   3 (132m ago)   90d
proxy-86dfdffcf5-zqzmq     1/1     Running   3 (133m ago)   90d
webapp-75d694ff55-xk252    1/1     Running   3 (132m ago)   90d
```

## Accessing a Container's Shell

### With ``nita-cmd``

You can log into a NITA container by providing the ``cli`` argument to the appropriate ``nita-cmd`` command. 

| Command | Description |
|---|---|
| ``nita-cmd jenkins cli [ jenkins \| root ]`` | Log into the container shell as either the jenkins or root user |
| ``nita-cmd webapp cli`` | Log into the webapp container shell |

```shell
$ nita-cmd webapp cli 
root@webapp-75d694ff55-xk252:/app#
```
## Ephemeral Containers

NITA uses two pods for Ansible and Robot that are only started and stopped when needed (usually under the control of Jenkins). These containers are called ephemeral 
containers because of this behaviour. It is important to be aware that any information used by these containers during their execution is only temporary and is lost 
(or more accurately "reset") when they are stopped. They are started by a Kubernetes job and after execution they will be cleared in 2 minutes.

## The Jenkins Container

Some useful commands with which to control the Jenkins container are listed in the table below:

| Command | Description |
|---|---|
|``nita-cmd jenkins [ up \| down ]`` | Create and start, or stop and remove the container | 
|``nita-cmd jenkins [ start \| stop \| restart \| status ]`` | Start, stop or restart a container, or look at the status |
|``nita-cmd jenkins [ ips \| ports ]`` | See what IP address and ports are being used by the container |
|``nita-cmd jenkins cli [ jenkins \| root ]`` | Log into the container shell as either user |
|``nita-cmd jenkins volumes`` | Look at what directories are shared with the host and the container |

You can also control job execution directly via ``nita-cmd`` by running ``nita-cmd jenkins jobs``.

Note that NITA creates two jobs in Jenkins, "network_template_mgr" and "network_type_validator" which are the workflows behind adding new projects and networks, 
so please do not delete or edit them.

```shell
$ nita-cmd jenkins jobs  ls
May 01, 2024 12:20:40 PM hudson.cli.CLI _main
INFO: Skipping HTTPS certificate checks altogether. Note that this is not secure at all.
network_template_mgr
network_type_validator
```
## MariaDB Container

You might want to access the MariaDB container to run some SQL queries on the database, for example if you were troubleshooting a problem or running a report. 
You can access the database once you have logged into the MariaDB container by running the ``mysql`` command (the default user credentials are root/root) , like this:

```shell
$ kubectl exec -it -n nita db-7cc98cd974-t4ppb -- bash
root@db-7cc98cd974-t4ppb:/# mysql -u root -p 
Enter password: 
Welcome to the MariaDB monitor.  Commands end with ; or \g.
Your MariaDB connection id is 15
Server version: 10.4.12-MariaDB-1:10.4.12+maria~bionic mariadb.org binary distribution

Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

MariaDB [(none)]> use Sites;
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A
MariaDB [Sites]> show tables;
+----------------------------+
| Tables_in_Sites            |
+----------------------------+
| auth_group                 |
| auth_group_permissions     |
| auth_permission            |
| auth_user                  |
| auth_user_groups           |
| auth_user_user_permissions |
| django_admin_log           |
| django_content_type        |
| django_migrations          |
| django_session             |
| ngcn_action                |
| ngcn_actioncategory        |
| ngcn_actionhistory         |
| ngcn_actionproperty        |
| ngcn_campusnetwork         |
| ngcn_campustype            |
| ngcn_campustype_resources  |
| ngcn_campustype_roles      |
| ngcn_resource              |
| ngcn_role                  |
| ngcn_workbook              |
| ngcn_worksheets            |
+----------------------------+
22 rows in set (0.001 sec)
```
From here, you can run all kinds of SQL statements and queries... see the MariaDB Knowledge Base on [SQL Statements](https://mariadb.com/kb/en/sql-statements/) for more details. 
Note that we don't advise you to alter either the database or table structures used by NITA, but read-only queries should be safe enough.

# VERSION

This document is relevant for NITA version 23.12.

# SEE ALSO

``nita-cmd``
