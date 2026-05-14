#!/usr/bin/env bash
# .github/scripts/setup-configmaps.sh
#
# Generates the self-signed certificates and Kubernetes ConfigMaps required
# by the proxy (nginx) and jenkins deployments before the pods start.
#
# This mirrors the certificate-generation section of install.sh so that the
# same manifests used in production can be applied unchanged on a Kind cluster.

set -euo pipefail

KEYPASS="${KEYPASS:-nita123}"
GITHUB_ORG="${GITHUB_ORG:-Juniper}"
TMPDIR=$(mktemp -d)

PROXY_DIR="${TMPDIR}/proxy"
CERTS_DIR="${PROXY_DIR}/certificates"
JENKINS_DIR="${TMPDIR}/jenkins"

cleanup() { rm -rf "${TMPDIR}"; }
trap cleanup EXIT

mkdir -p "${CERTS_DIR}" "${JENKINS_DIR}"

# ---------------------------------------------------------------------------
# nginx: config + self-signed certificate
# ---------------------------------------------------------------------------
echo "--- Downloading nginx.conf from nita-webapp repo ---"
curl -fsSL \
  "https://raw.githubusercontent.com/${GITHUB_ORG}/nita-webapp/main/nginx/nginx.conf" \
  -o "${PROXY_DIR}/nginx.conf"

echo "--- Generating nginx self-signed certificate (mirrors install.sh) ---"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "${CERTS_DIR}/nginx-certificate-key.key" \
  -out    "${CERTS_DIR}/nginx-certificate.crt" \
  -subj   "/CN=nita-proxy/O=nita-test"

# ---------------------------------------------------------------------------
# Jenkins: JKS keystore -> PKCS12 -> PEM certificate
# ---------------------------------------------------------------------------
echo "--- Generating Jenkins keystore (mirrors install.sh) ---"
keytool -genkey -keyalg RSA -alias selfsigned \
  -keystore  "${JENKINS_DIR}/jenkins_keystore.jks" \
  -keypass   "${KEYPASS}" \
  -keysize   4096 \
  -dname     "cn=jenkins, ou=, o=, l=, st=, c=" \
  -storepass "${KEYPASS}"

keytool -importkeystore \
  -srckeystore   "${JENKINS_DIR}/jenkins_keystore.jks" \
  -destkeystore  "${JENKINS_DIR}/jenkins.p12" \
  -deststoretype PKCS12 \
  -deststorepass "${KEYPASS}" \
  -srcstorepass  "${KEYPASS}"

echo "--- Extracting Jenkins certificate from keystore ---"
openssl pkcs12 \
  -in       "${JENKINS_DIR}/jenkins.p12" \
  -nokeys \
  -out      "${JENKINS_DIR}/jenkins.crt" \
  -password pass:"${KEYPASS}"

# ---------------------------------------------------------------------------
# Create the four ConfigMaps the proxy and jenkins deployments reference
# ---------------------------------------------------------------------------
echo "--- Creating Kubernetes ConfigMaps in namespace nita ---"

kubectl create cm proxy-config-cm \
  --from-file="${PROXY_DIR}/nginx.conf" \
  --namespace nita

kubectl create cm proxy-cert-cm \
  --from-file="${CERTS_DIR}/" \
  --namespace nita

kubectl create cm jenkins-crt \
  --from-file="${JENKINS_DIR}/jenkins.crt" \
  --namespace nita

kubectl create cm jenkins-keystore \
  --from-file="${JENKINS_DIR}/jenkins_keystore.jks" \
  --namespace nita

echo "--- ConfigMaps ready ---"
kubectl get cm -n nita
