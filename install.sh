#!/bin/bash

# @(#) install.sh - NITA installation script

# Written by us, so that you don't have to

# ------------------------------------------------------------------------------
# Define functions and variables

ME="${0##*/}"						# This scripts name
HOST=`uname -n`
bold=$(tput bold)					# For echo emphasis
normal=$(tput sgr0)

# Set env vars or take them from the calling shell

NITAROOT=${NITAROOT:=/opt}				# Where to install NITA
BINDIR=${BINDIR:=/usr/local/bin}			# Where to put binaries
BASH_COMPLETION=${BASH_COMPLETION:="/etc/bash_completion.d"}

K8SROOT=${K8SROOT:=$NITAROOT/nita/k8s}
PROXY=${PROXY:=$K8SROOT/proxy}
CERTS=${CERTS:=$PROXY/certificates}
JENKINS=${JENKINS:=$K8SROOT/jenkins}
KEYPASS=${KEYPASS:="nita123"}

KUBEROOT=${KUBEROOT:=/etc/kubernetes}
KUBECONFIG=${KUBECONFIG:=$KUBEROOT/admin.conf}

export NITAROOT KUBEROOT K8SROOT PROXY CERTS JENKINS KEYPASS KUBECONFIG

Question () {

        # Ask a yes/no/quit question. Default answer is "No"

        echo -n "$1 (y|n|q)? [n] "

        read ANSWER
        ANSWER=${ANSWER:="n"}

        [ "X$ANSWER" = "Xy" ] || [ "X$ANSWER" = "XY" ] && {

                return 0
        }

        [ "X$ANSWER" = "Xq" ] || [ "X$ANSWER" = "XQ" ] && {
                # rm -f $ERRORS
                echo "Goodbye!"
                exit 0
        }

        return 1
}

Debug() {

	# Execute debug commands if DEBUG is set in the shell

        [ ${DEBUG} ] && {
                echo "${ME}: DEBUG: $*" >&2
                eval "$*" >&2
        }

        return $?
}

# ------------------------------------------------------------------------------
# Main part of script

echo "${ME}: NITA install script."

[ "X$EUID" != "X0" ] && {

	# Check that our effective user is root

	echo "Error: To install system software this script must be run as root or \"sudo -E\""
	exit 1
}

Debug "echo $NITAROOT $KUBEROOT $K8SROOT $PROXY $CERTS $JENKINS $KEYPASS $KUBECONFIG"

# ------------------------------------------------------------------------------

Question "Install system dependencies" && {

	# Update system packages and install our dependencies

	apt-get update
	apt install -y ca-certificates curl gnupg lsb-release
 	mkdir -p /usr/share/keyrings
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

	echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list

	apt-get update
	apt-get install -y containerd.io
	apt-get install -y curl gnupg2 software-properties-common apt-transport-https
	apt-get install -y git
	apt-get install openjdk-19-jre-headless
	apt-get install -y socat
 	apt-get install -y jq
  	apt-get install -y unzip

	mkdir -p /etc/containerd/

	containerd config default | tee /etc/containerd/config.toml >/dev/null 2>&1

	sed -i 's/SystemdCgroup \= false/SystemdCgroup \= true/g' /etc/containerd/config.toml

	systemctl restart containerd
	systemctl enable containerd

}

# ------------------------------------------------------------------------------

Question "Install Kubernetes" && {

	# Disable use of swap space

	swapoff -a
	sed -i '/swap/ s/^\(.*\)$/#\1/g' /etc/fstab

	[ ! -d ${KUBEROOT} ] && mkdir -p ${KUBEROOT}
	
	echo "${ME}: Adding k8s to sysctl.d"

	tee /etc/sysctl.d/kubernetes.conf <<-EOT
	net.bridge.bridge-nf-call-ip6tables = 1
	net.bridge.bridge-nf-call-iptables = 1
	net.ipv4.ip_forward = 1
	EOT

	echo "${ME}: Adding overlay network and bridge netfilter"

	modprobe overlay
	modprobe br_netfilter

	tee /etc/modules-load.d/k8s.conf <<-EOT
	overlay
	br_netfilter
	EOT

	sysctl --system >>/dev/null 2>&1

	if [ ! -x "$(command -v kubectl)" ]; then

		echo "${ME}: Couldn't find \"kubectl\" in your path, so installing it"
  		mkdir -p /etc/apt/keyrings
		curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
		echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list

		apt update
		apt install -y kubelet kubeadm kubectl
		apt-mark hold kubelet kubeadm kubectl
	else
		echo "${ME}: \"kubectl\" is already installed on this machine"
	fi

}

# ------------------------------------------------------------------------------

Question "Initialise Kubernetes cluster" && {

	kubeadm init --control-plane-endpoint="localhost" --ignore-preflight-errors=NumCPU
 
	# And export config for now, before we run kubectl...

	export KUBECONFIG=${KUBEROOT}/admin.conf
	echo "${ME}: Warning: Make sure KUBECONFIG is always set in your shell." 
	echo "${ME}: Warning: If Kubernetes fails, that is probably why."

	# Some status information on the cluster

	Debug "kubectl cluster-info"
	Debug "kubectl version --client"
	Debug "kubectl get ns"

	systemctl enable kubelet.service

	Debug "ufw status"

	kubectl taint nodes --all node-role.kubernetes.io/master-
	kubectl taint nodes --all  node-role.kubernetes.io/control-plane-
	kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.0/manifests/calico.yaml

}

# ------------------------------------------------------------------------------

Question "Install NITA repositories" && {

	mkdir -p ${BINDIR}

	NITA_REPOS="nita nita-ansible nita-jenkins nita-robot nita-webapp"

	for REPO in ${NITA_REPOS}; do
 
		# Note: git won't clone into an existing directory anyway
  		# but we check anway

                if [ ! -d ${NITAROOT}/${REPO} ]; then

                        echo "${ME}: Cloning fresh repository: ${REPO}"

                        git clone https://github.com/Juniper/${REPO}.git ${NITAROOT}/${REPO}

                        # Make symbolic links for nita cli scripts...

                        find ${NITAROOT}/${REPO}/cli_scripts -type f -name "nita-cmd*" -exec ln -s {} ${BINDIR} \;
                else
                        echo "${ME}: Warning: Directory already exists: \"${NITAROOT}/${REPO}\". Skipping."
                fi

 	done

	echo "${ME}: Executing NITA post-install scripts"

        NITACMD="${NITAROOT}/nita-webapp/nita-cmd"

        [ -d ${NITACMD} ] && {

                # Set up nita-cmd

                install -m 755 ${NITACMD}/cli_runner ${BINDIR}/nita-cmd
                install -m 644 ${NITACMD}/bash_completion.d/cli_runner_completions ${BASH_COMPLETION}/cli_runner_completions
                install -m 644 ${NITACMD}/bash_completion.d/nita-cmd ${BASH_COMPLETION}/nita-cmd

        }

	cd  ${K8SROOT}
	bash apply-k8s.sh

	mkdir -p ${NITAROOT}/nita/k8s/proxy
 	wget --inet4-only https://raw.githubusercontent.com/Juniper/nita-webapp/main/nginx/nginx.conf -O ${PROXY}/nginx.conf
	ln -s ${NITAROOT}/nita/k8s/proxy ${PROXY}/nginx.conf

	Debug "kubectl get nodes -o wide"
	Debug "kubectl get pods -n nita"

	mkdir -p ${CERTS}
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ${CERTS}/nginx-certificate-key.key -out ${CERTS}/nginx-certificate.crt

	echo "${ME}: Certificates created"

	kubectl create cm proxy-config-cm --from-file=${PROXY}/nginx.conf --namespace nita
	kubectl create cm proxy-cert-cm --from-file=${CERTS}/ --namespace nita

	mkdir -p ${JENKINS}

	keytool -genkey -keyalg RSA -alias selfsigned -keystore ${JENKINS}/jenkins_keystore.jks -keypass ${KEYPASS} -keysize 4096 -dname "cn=jenkins, ou=, o=, l=, st=, c=" -storepass ${KEYPASS} -srckeypass ${KEYPASS}

	keytool -importkeystore -srckeystore ${JENKINS}/jenkins_keystore.jks -destkeystore ${JENKINS}/jenkins.p12 -deststoretype PKCS12 -deststorepass ${KEYPASS}  -srcstorepass ${KEYPASS}

	echo "${ME}: Converting keystore to certificate"

	openssl pkcs12 -in ${JENKINS}/jenkins.p12 -nokeys -out ${JENKINS}/jenkins.crt -password pass:${KEYPASS}

	kubectl create cm jenkins-crt --from-file=${JENKINS}/jenkins.crt --namespace nita
	kubectl create cm jenkins-keystore --from-file=${JENKINS}/jenkins_keystore.jks --namespace nita

	echo "${ME}: Please wait ${bold}5-10 minutes${normal} for the Kubernetes pods to initialise"

	Debug "kubectl get cm"
	Debug "kubectl describe cm"
	Debug "kubectl get ns nita"
}

Question "Do you want to set up K8S config for a local user" && {

	VALID_USER=1

	# Create a local copy of the config file

	while [ ${VALID_USER} -ne 0 ]
	do
        	echo -n "Enter a valid local user to own the K8S config: "
        	read OWNER
        	id "${OWNER}" >/dev/null 2>&1
        	VALID_USER=$?
	done

	# Copy the K8S admin file to the local user and set ownership etc.

	OWNER_HOME=`egrep "^${OWNER}" /etc/passwd | awk -F: '{print $6}'`
	echo "${ME}: OK, creating ${OWNER_HOME}/.kube"
	mkdir -p ${OWNER_HOME}/.kube
	cp -i ${KUBEROOT}/admin.conf ${OWNER_HOME}/.kube/config
	chown -R $(id -u ${OWNER}):$(id -g ${OWNER}) ${OWNER_HOME}/.kube/
	echo "export KUBECONFIG=${HOME}/.kube/config" >> ${OWNER_HOME}/.bashrc

	echo "${ME}: Now source your bashrc file to set KUBECONFIG in your shell"

}

Debug "ls -al ${NITAROOT}"

echo "${ME}: NITA installation has finished."
echo ""
echo "${ME}: You can access the NITA webapp at https://${HOST}:443"
echo "${ME}: You can access the Jenkins UI at https://${HOST}:8443"
