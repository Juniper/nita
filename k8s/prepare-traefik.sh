#!/usr/bin/env bash
set -euo pipefail

: "${CERTS:?CERTS must name the proxy certificate directory}"
cd "$(dirname "$0")"

bash ./prepare-proxy-certificate.sh
kubectl create secret tls nita-traefik-tls -n nita \
    --cert="${CERTS}/nginx-certificate.crt" \
    --key="${CERTS}/nginx-certificate-key.key" \
    --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap nita-traefik-config -n nita \
    --from-file=traefik.yaml=traefik/traefik.yaml \
    --from-file=routes.yaml=traefik/routes.yaml \
    --dry-run=client -o yaml | kubectl apply -f -
for plugin in bodylimit identityguard; do
    kubectl create configmap "nita-traefik-${plugin}" -n nita \
        --from-file=".traefik.yml=traefik/${plugin}/.traefik.yml" \
        --from-file="go.mod=traefik/${plugin}/go.mod" \
        --from-file="${plugin}.go=traefik/${plugin}/${plugin}.go" \
        --dry-run=client -o yaml | kubectl apply -f -
done
