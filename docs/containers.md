# NAME

Containers. Almost everything you need to know about the containers used by NITA.

# SYNOPSIS

``nita-cmd containers [ ls | versions ] ``\
``nita-cmd [ ips | stats ]``\
``nita-cmd [ ansible | jenkins | robot | webapp ] cli <args>...``\
``docker [ ps | exec | run ]``

# DESCRIPTION

NITA is packaged and executed as a series of Docker containers, which communicate with one another via an internal IPv4 subnet. There are four custom containers, one each for Ansible, Jenkins, Robot and the NITA Webapp, and two standard containers for Nginx and MariaDB. Of the custom containers, Jenkins and the Webapp are persistent (which means that they run continuously) whereas Ansible and Robot are ephemeral (i.e. they are started and stopped as and when required). Using a container based approach allows NITA to be easily packaged, distributed, deployed and run, and it also allows a user to add further custom containers if they wish to expand the functionality of the solution themselves later.

# EXAMPLES

There are many ways in which you can control and troubleshoot container operations with NITA, using either the ``nita-cmd`` or ``docker`` commands. This section shows some of the most useful examples that you should know.

## The Docker Client

The ``docker`` binary is a client for interacting with the ``dockerd`` daemon through a command line interface. It has over 30 commands that allow you to control and troubleshoot container operations in detail. You can use the ``docker`` client directly from the shell of the NITA host server. For example, if you want to list the running containers you can use ``docker ps``, like this:

```shell
$ docker ps
CONTAINER ID        IMAGE                         COMMAND                  CREATED             STATUS                    PORTS                                         NAMES
906f4235bd96        nginx:1.17.9                  "nginx -g 'daemon of…"   4 months ago        Up 47 minutes             80/tcp, 0.0.0.0:443->443/tcp                  nitawebapp_proxy_1
34743b207365        juniper/nita-webapp:21.7-1    "./build-and-test-we…"   4 months ago        Up 47 minutes             8000/tcp                                      nitawebapp_webapp_1
cfdc45177801        mariadb:10.4.12               "docker-entrypoint.s…"   4 months ago        Up 47 minutes             3306/tcp                                      nitawebapp_db_1
922a4eb21e05        juniper/nita-jenkins:21.7-1   "/sbin/tini -- /usr/…"   4 months ago        Up 47 minutes (healthy)   8080/tcp, 50000/tcp, 0.0.0.0:8443->8443/tcp   nitajenkins_jenkins_1
$
```
Here you can see the two persistent NITA containers (Jenkins and the Webapp) plus containers for the Nginx webserver and the Maria SQL database. 

The trouble is that the ``docker`` client has a lot of options (type ``docker help`` to see what options are available) and this can make it complicated to use. Therefore we have provided a number of shortcuts for the most useful options with the ``nita-cmd`` command, as outlined below. 

## The ``nita-cmd`` Command

### ``nita-cmd containers``

You can use the ``nita-cmd containers`` command to get information about the customised containers used by NITA. The following options are supported:

| Command | Description |
|---|---|
|``nita-cmd containers ls`` | List all running NITA containers |
|``nita-cmd containers versions`` | Show the version numbers of running NITA containers |

If you read the nita-cmd documentation you will see that it is in fact just a wrapper for other shell scripts. When you run the ``nita-cmd containers ls`` command, it is actually running the ``docker ps`` command and filtering the output. For example, to see what containers are currently running on the NITA host, do this:

```shell
$ nita-cmd containers ls
CONTAINER ID        IMAGE                         CREATED             STATUS                    PORTS                                         NAMES
34743b207365        juniper/nita-webapp:21.7-1    4 months ago        Up 43 minutes             8000/tcp                                      nitawebapp_webapp_1
922a4eb21e05        juniper/nita-jenkins:21.7-1   4 months ago        Up 43 minutes (healthy)   8080/tcp, 50000/tcp, 0.0.0.0:8443->8443/tcp   nitajenkins_jenkins_1
$
```
Here you can see the two persistent containers (Jenkins and Webapp) running. This command shows you some useful information, such as the image name and the container ID (that will be useful later, if you want to access them directly with ``docker``). If you need to find which versions of NITA container you have running, do the following:

```shell
$ nita-cmd containers versions
"/nitawebapp_webapp_1 juniper/nita-webapp:21.7-1"
"/nitajenkins_jenkins_1 juniper/nita-jenkins:21.7-1"
```

### Other ``nita-cmd`` options

To see what IP addresses have been assigned to the containers (on the internal Docker network), do this:

```shell
$ nita-cmd ips
"/nitawebapp_webapp_1 172.21.0.5"
"/nitajenkins_jenkins_1 172.21.0.4"
```

To see the runtime status of containers, use ``nita-cmd stats`` like this:

```shell
$ nita-cmd stats
CONTAINER ID        NAME                    CPU %               MEM USAGE / LIMIT     MEM %               NET I/O             BLOCK I/O           PIDS
34743b207365        nitawebapp_webapp_1     5.85%               88.74MiB / 3.853GiB   2.25%               50.8kB / 25.8kB     44.9MB / 0B         4
922a4eb21e05        nitajenkins_jenkins_1   0.08%               670.4MiB / 3.853GiB   16.99%              3.09MB / 52.8kB     154MB / 6.94MB      45
$
```

## Accessing a Container's Shell

### With ``nita-cmd``

You can log into a NITA container by providing the ``cli`` argument to the appropriate ``nita-cmd`` command. 

| Command | Description |
|---|---|
| ``nita-cmd ansible cli 21.7`` | Start the Ansible container and log into its shell |
| ``nita-cmd jenkins cli [ jenkins \| root ]`` | Log into the container shell as either the jenkins or root user |
| ``nita-cmd robot cli 21.7`` | Start the robot container and log into its shell |
| ``nita-cmd webapp cli`` | Log into the webapp container shell |

Note that because the Ansible and Robot containers are ephemeral, when you ``exit`` from the container's shell, the container itself will be stopped.

### With ``docker``

NITA also uses some standard "vanilla" containers for the Maria database and the Nginx webserver and because these containers are not tagged as NITA (as they are not customised), they do not appear in the output of the ``nita-cmd containers ls`` command. They are however visible with the ``docker ps`` command, and you should use this to find a container's unique container identifier if you want to access its shell.

For example, if you want to log into the Maria DB container, first run ``docker ps`` to find the container ID and then ``docker exec``, like this:

```shell
$ docker ps
CONTAINER ID        IMAGE                         COMMAND                  CREATED             STATUS                 PORTS                                         NAMES
906f4235bd96        nginx:1.17.9                  "nginx -g 'daemon of…"   4 months ago        Up 7 hours             80/tcp, 0.0.0.0:443->443/tcp                  nitawebapp_proxy_1
34743b207365        juniper/nita-webapp:21.7-1    "./build-and-test-we…"   4 months ago        Up 7 hours             8000/tcp                                      nitawebapp_webapp_1
cfdc45177801        mariadb:10.4.12               "docker-entrypoint.s…"   4 months ago        Up 7 hours             3306/tcp                                      nitawebapp_db_1
922a4eb21e05        juniper/nita-jenkins:21.7-1   "/sbin/tini -- /usr/…"   4 months ago        Up 7 hours (healthy)   8080/tcp, 50000/tcp, 0.0.0.0:8443->8443/tcp   nitajenkins_jenkins_1
$ docker exec -ti cfdc45177801 /bin/bash
root@cfdc45177801:/#
```

The ``docker exec -ti`` command allows you to open an interactive session on the terminal in a running container. In the example above, you are running bash as the login shell to access the Maria DB container that is running.

## Ephemeral Containers

NITA uses two Docker containers for Ansible and Robot that are only started and stopped when needed (usually under the control of Jenkins). These containers are called ephemeral containers because of this behaviour. It is important to be aware that any information used by these containers during their execution is only temporary and is lost (or more accurately "reset") when they are stopped.

With that said, you can start and run these containers (outside of the control of Jenkins) either by using the ``nita-cmd`` command as shown above, or by using the ``docker run`` command. In fact, the command ``nita-cmd ansible cli 21.7`` is actually just a wrapper for ``docker run`` like this:

``docker run -ti -u root -v /var/nita_project:/project:rw -v /var/nita_configs:/var/tmp/build:rw juniper/nita-ansible:21.7-1 /bin/bash``

This command will use the Ansible 21.7-1 Docker image to run a new instance of the container, if one is not already running. It will then open an interactive terminal in the container by running the bash shell. Note that this command mounts several volumes (using ``-v [host-dir:container-dir:access]``) which you should not change. Also note that only one instance of the Ansible and Robot ephemeral containers can be running at any one time - so if you run a new instance by using ``docker run``, be aware that a Jenkins job may fail if it also then tries to run its own instance. Capisce?

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

Note that NITA creates two jobs in Jenkins, "network_template_mgr" and "network_type_validator" which are the workflows behind adding new projects and networks, so please do not delete or edit them.

## MariaDB Container

It is also worth mentioning the MariaDB container here, because we can't think of where else to mention it. Because it is a standard Docker container it does not appear in the output of ``nita-cmd containers ls`` even though it is continually running, so you will have to use ``docker ps`` to find it's Container ID, that you can then execute a shell in. Something like this:

```shell
$ docker ps | grep maria
cfdc45177801        mariadb:10.4.12               "docker-entrypoint.s…"   4 months ago        Up 2 hours             3306/tcp                                      nitawebapp_db_1
$ docker exec -ti cfdc45177801 /bin/bash
root@cfdc45177801:/# exit
exit
$ 
```
You might want to access the MariaDB container to run some SQL queries on the database, for example if you were troubleshooting a problem or running a report. You can access the database once you have logged into the MariaDB container by running the ``mysql`` command (the default user credentials are root/root) , like this:

```shell
root@cfdc45177801:/# mysql -u root -p
Enter password:
Welcome to the MariaDB monitor.  Commands end with ; or \g.
Your MariaDB connection id is 15
Server version: 10.4.12-MariaDB-1:10.4.12+maria~bionic mariadb.org binary distribution

Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

MariaDB [(none)]> use Sites;
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A

Database changed
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

MariaDB [Sites]> quit
Bye
root@cfdc45177801:/# exit
$
```

From here, you can run all kinds of SQL statements and queries... see the MariaDB Knowledge Base on [SQL Statements](https://mariadb.com/kb/en/sql-statements/) for more details. Note that we don't advise you to alter either the database or table structures used by NITA, but read-only queries should be safe enough.

# VERSION

This document is relevant for NITA version 21.7.

# SEE ALSO

``nita-cmd``
