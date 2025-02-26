# Creating a Custom Container for NITA

## Introduction

Here is a brief introduction to the world of containers, and how NITA uses them...

- **NITA runs applications inside containers, which are deployed inside Kubernetes pods.**
- Although many people have heard of Docker containers before, it is important to note that NITA containers are executed inside the `containerd` (pronounced "Container D") runtime environment, which is simpler and more effecient than Docker. Docker however does provide some useful tools for managing containers, most of which NITA does not need, but as you will see below, we will use some of Docker's tools to build our own custom container before importing it into the world of containerd.
- Every time NITA starts a container, it will do so from an original pre-built image. This means that every time a container is instantiated, it will be exactly the same as the original parent. This is a great, but it also means that you should not edit a running container and expect your changes to persist or be inherited by future generations. The correct way to make changes to a container (i.e. to customize it) is to change the parent and then start a new container.
- We will use Docker's build tools to customise a new container image, and the way that we do that is by specifying how the image is built by editting its Dockerfile.

This example below will walk through how to customize the NITA Jenkins container, but the process is the same for any other container.
Now, let's begin.

## Installing the Docker tools

If you don't already have the Docker Community Edition installed, you will need to install it in order to get the tools necessary. This example is for AlmaLinux:

```
$ sudo dnf install -y docker-ce
$ sudo usermod -aG docker <username>
$ sudo service docker restart
```

## Customizing the Jenkins Container

In this example, we'll create a custom Jenkins container so that we can take advantage of the AI integration available [described here](https://github.com/Juniper/nita/blob/main/examples/chatgpt/README.md). Start by removing the original [Dockerfile](https://github.com/Juniper/nita-jenkins/blob/main/Dockerfile) that ships with NITA and replacing it with your own one:

```
$ cd /opt/nita-jenkins
$ sudo mv Dockerfile Dockerfile-
$ sudo wget https://github.com/Juniper/nita/raw/refs/heads/main/examples/chatgpt/robot.jar
$ sudo wget https://raw.githubusercontent.com/Juniper/nita/refs/heads/main/examples/chatgpt/Dockerfile
```
Now change the tag number in the `build_container.sh` script. The  tag follows the `-t` argument to the `docker build` command. Each image needs its own unique tag. Make sure that whenever you build an image, if you want a new version you will have to remember to do this. For example, edit the script and change the tag to `25.01-01`, change the line to this:

```
docker build --build-arg KUBECTL_ARCH=${KUBECTL_ARCH} -t juniper/nita-jenkins:25.01-1 .
```

:warning:The dot at the end of the line is important, don't delete it!

Once you have changed (or replaced) the Dockerfile and editted the tag, you can build a new container image thus:

```
$ sudo ./build_container.sh
```

This will take a few minutes, but once it has completed you can check to see that Docker has the new image, like this:

```
$ docker image ls
REPOSITORY             TAG       IMAGE ID       CREATED         SIZE
juniper/nita-jenkins   25.01-1   79300ab8d042   8 minutes ago   1.69GB
```
The next step is to get this image from Docker into the `containerd` environment. We do that in two steps, the first is to save the Docker image as a tar file, and the next is to import that file into the `containerd` environment:

```
$ docker save juniper/nita-jenkins:25.01-1 > nita-jenkins:25.01-1.tar
$ sudo ctr -n=k8s.io image import nita-jenkins:25.01-1.tar
```

Now we need to tell Kubernetes to use this new image when it starts a pod, rather than the one it is currently using. Kubernetes pods are configured first before they are executed, in a similar way to how containers are built before they are run. NITA stores all of its Kubernetes configuration files in the directory `/opt/nita/k8s`, so you will need to go there to make your change:

```
$ cd /opt/nita/k8s
$ sudo vi jenkins-deployment.yaml
```
For Jenkins, we want to change the tag number that applies to the container image that is deployed in the pod. Look for the `image:` line, and change it from:

```
  image: juniper/nita-jenkins:23.12-1
```
to:
```
  image: juniper/nita-jenkins:25.01-1
```

:warning:Note that on some systems, tab is not permitted in the Kubernetes YAML file, so make sure that you use spaces instead.

Finally, we must tell Kubernetes to start a new pod which includes that image (note: `sudo` may be optional, depending upon if you have installed `kubectl` for your user to run it, or just `root`):

```
$ sudo kubectl delete deployment jenkins -n nita
$ sudo kubectl apply -f /opt/nita/k8s/jenkins-deployment.yaml
$ sudo systemctl restart kubelet
```
:exclamation: If you find that Kubernetes is still using the previous cached image, you can restart it like this:

```
$ sudo kubectl rollout restart deployment/jenkins -n nita
```
