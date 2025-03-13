# Working with Certificates

## Kubernetes Certificates

The [Kubernetes documentation](https://kubernetes.io/docs/setup/best-practices/certificates/) says "If you install Kubernetes with `kubeadm`, the certificates that your cluster requires are automatically generated."  This is the method that we use in the NITA install script (the openssl commands are for nginx and Jenkins) and so by default, the certificates for the Kubernetes cluster will last for one year before they need to be renewed. Fortunately it is a simple process to renew these certificates.

To see when your Kubernetes certificates will expire, run this command:

```
$ sudo kubeadm certs check-expiration
```

If they expire soon, or have already expired, you can renew them for another year by running the following commands:

```
$ sudo kubeadm certs renew all
$ sudo systemctl restart kubelet
```

:warning: Be aware that the 1-year duration for Kubernetes certificates seems to be hardcoded in the `kubeadm` command, so you will need to remember to renew them on an annual basis.

## Zscaler, Certificates and K8S

If you are running NITA in an environment where there is a zero-trust cybersecurity solution in play, such as from Zscaler, then depending upon how it has been configured, you may find that it blocks some external sites on the Internet. This may cause problems for NITA during the installation process, for example if it is unable to download container or pod images. For example, during a fresh NITA install, the ``kubeadm init...`` command may fail to download images for the pods, with an error like this:

```[ERROR ImagePull]: failed to pull image.... tls: failed to verify certificate: x509: certificate signed by unknown authority```

You can verify this simply by using ``wget`` to try and download the same URL, and you will see something like this:

```
$ wget https://europe-west2-docker.pkg.dev/v2/k8s-artifacts-prod/images/coredns/coredns/manifests/v1.10.1
--2024-11-07 09:33:12--  https://europe-west2-docker.pkg.dev/v2/k8s-artifacts-prod/images/coredns/coredns/manifests/v1.10.1
Resolving europe-west2-docker.pkg.dev (europe-west2-docker.pkg.dev)... 142.250.27.82
Connecting to europe-west2-docker.pkg.dev (europe-west2-docker.pkg.dev)|142.250.27.82|:443... connected.
ERROR: cannot verify europe-west2-docker.pkg.dev's certificate, issued by ‘CN=Zscaler Intermediate Root CA (zscalertwo.net) (t)\\ ,OU=Zscaler Inc.,O=Zscaler Inc.,ST=California,C=US’:
  Unable to locally verify the issuer's authority.
To connect to europe-west2-docker.pkg.dev insecurely, use `--no-check-certificate'.
```

This is because in the network, Zscaler is changing the certificates after it has inspected traffic (i.e. acting as a "man-in-the-middle"). The correct solution to fix this is to load the Zscaler certificates into the NITA system as a trusted Certificate Authority (see this [Zscaler article](https://help.zscaler.com/zia/adding-custom-certificate-application-specific-trust-store) for details). Follow these steps:

## Step 1 - Get the certs

Read the K8S error message to see where the image pull is failing. In this example, it is failing to pull docker images from the URL ``https://europe-west2-docker.pkg.dev``. You can get all of the certificates in the chain with this command:
```
$ openssl s_client -connect europe-west2-docker.pkg.dev:443 -showcerts > Zscaler.pem
```
You will need to press ``<CTRL>+C`` to return to the shell's prompt. Now you can do a quick test to verify that you have the correct certificates by specifying them to ``wget`` as an argument, like this:
```
$ wget --ca-certificate=Zscaler.pem https://europe-west2-docker.pkg.dev/v2/k8s-artifacts-prod/images/coredns/coredns/manifests/v1.10.1
--2024-11-07 09:40:44--  https://europe-west2-docker.pkg.dev/v2/k8s-artifacts-prod/images/coredns/coredns/manifests/v1.10.1
Resolving europe-west2-docker.pkg.dev (europe-west2-docker.pkg.dev)... 142.250.27.82
Connecting to europe-west2-docker.pkg.dev (europe-west2-docker.pkg.dev)|142.250.27.82|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: 2005 (2.0K) [application/vnd.docker.distribution.manifest.list.v2+json]
Saving to: ‘v1.10.1’
v1.10.1                         100%[====================================================>]   1.96K  --.-KB/s    in 0s
2024-11-07 09:40:44 (336 MB/s) - ‘v1.10.1’ saved [2005/2005]
```

If everything worked as expected, it will have downloaded the file and you can proceed to the next step. If not, go back and check that you downloaded the correct certificates from the correct URL.

## Step 2 - Install New Certificates

Now you need to split the PEM file that you downloaded into separate individual PEM files, one for each certificate. For example, assuming that there are 3 certificates, start by making 3 copies of that file. Then edit each one and remove the lines outside of the ``--- BEGIN CERTIFICATE ---`` and ``--- END CERTIFICATE ---`` sections of each certificate, so that there is one certificate per file.

Kubernetes will store certificates under the directory ``/usr/local/share/ca-certificates`` but you should also find out where openssl stores them, so that you can install the new certificates there too. Do that by running this command:

```
$ openssl version -d
OPENSSLDIR: "/usr/lib/ssl"
```

There will be a ``certs`` directory under that (probably also linked to from ``/etc/ssl/certs``).

After breaking the certificates down into their own individual files as described above, copy the files over to the appropriate directories. For Ubuntu, it is:

```
$ sudo cp -v Zscaler[0-2].pem /usr/local/share/ca-certificates
'Zscaler1.pem' -> '/usr/local/share/ca-certificates/Zscaler0.pem'
'Zscaler2.pem' -> '/usr/local/share/ca-certificates/Zscaler1.pem'
'Zscaler3.pem' -> '/usr/local/share/ca-certificates/Zscaler2.pem'
$ sudo cp -v Zscaler*.pem /usr/lib/ssl/certs
'Zscaler0.pem' -> '/usr/lib/ssl/certs/Zscaler0.pem'
'Zscaler1.pem' -> '/usr/lib/ssl/certs/Zscaler1.pem'
'Zscaler2.pem' -> '/usr/lib/ssl/certs/Zscaler2.pem'
```

For AlmaLinux, the destination is different:

```
$ sudo cp -v Zscaler[0-2].pem /etc/pki/ca-trust/source/anchors
```

Make sure that the files are world-readable (``chmod 644 <cert file>``) and that there is exactly one certificate per file. Now reload the certificates. For Ubuntu, that is:

```
$ sudo update-ca-certificates --fresh
Clearing symlinks in /etc/ssl/certs...
done.
Updating certificates in /etc/ssl/certs...
rehash: warning: skipping ca-certificates.crt,it does not contain exactly one certificate or CRL
146 added, 0 removed; done.
Running hooks in /etc/ca-certificates/update.d...
done.
```

For AlmaLinux, it will be:

```
$ sudo update-ca-trust
```

Once you have done this, running ``wget`` again without specifying the certificate as an argument should work just fine:

```
$ wget https://europe-west2-docker.pkg.dev/v2/k8s-artifacts-prod/images/coredns/coredns/manifests/v1.10.1
--2024-11-07 09:56:10--  https://europe-west2-docker.pkg.dev/v2/k8s-artifacts-prod/images/coredns/coredns/manifests/v1.10.1
Resolving europe-west2-docker.pkg.dev (europe-west2-docker.pkg.dev)... 142.250.27.82
Connecting to europe-west2-docker.pkg.dev (europe-west2-docker.pkg.dev)|142.250.27.82|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: 2005 (2.0K) [application/vnd.docker.distribution.manifest.list.v2+json]
Saving to: ‘v1.10.1’
v1.10.1                         100%[====================================================>]   1.96K  --.-KB/s    in 0s
2024-11-07 09:56:11 (585 MB/s) - ‘v1.10.1’ saved [2005/2005]
```

:warning: Note that **a reboot is recommended** before you resume the NITA installation.

Et voila! If it works, you have all of the certificates that you need for Kubernetes to download the images that it needs to initialise its pods. And you can continue with your installation of NITA!

## Notes on Installing NITA

If you started to install NITA before you had the correct certificates, the Kubernetes installation will fail at the ``kubeadm init`` line (in the "Initialise Kubernetes cluster" section), because it will be unable to download images for its pods. You will need to quit out of the installation here and perform the steps above, and then follow them up with a reboot or these commands:

```
$ sudo kubeadm reset
$ systemctl restart containerd.service
```

You can then restart the installation at the ``Initialise Kubernetes cluster`` section.
