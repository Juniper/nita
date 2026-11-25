#!/usr/bin/env bash

set -euo pipefail
umask 077

: "${CERTS:?CERTS must name the proxy certificate directory}"

cert="${CERTS}/nginx-certificate.crt"
key="${CERTS}/nginx-certificate-key.key"
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/nita-proxy-certificate.XXXXXX")
trap 'rm -rf -- "$tmpdir"' EXIT

if ! kubectl get deployment proxy -n nita --ignore-not-found -o json >"$tmpdir/deployment.json"; then
    echo "Error: unable to inspect the existing proxy deployment." >&2
    exit 1
fi
active_resource=""
if [ -s "$tmpdir/deployment.json" ]; then
    if ! active_resource=$(python3 - "$tmpdir/deployment.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    deployment = json.load(source)
containers = deployment["spec"]["template"]["spec"]["containers"]
proxy = next(container for container in containers if container["name"] == "proxy")
print("secret" if "traefik" in proxy["image"].lower() else "configmap")
PY
    ); then
        echo "Error: unable to identify the active proxy certificate source." >&2
        exit 1
    fi
fi

validate_pair() {
    local cert_file=$1 key_file=$2 cert_public key_public
    if ! openssl x509 -in "$cert_file" -noout -checkend 0 >/dev/null 2>&1 ||
       ! openssl pkey -in "$key_file" -check -noout >/dev/null 2>&1; then
        return 1
    fi
    cert_public=$(openssl x509 -in "$cert_file" -pubkey -noout |
        openssl pkey -pubin -outform DER | openssl dgst -sha256) || return 1
    key_public=$(openssl pkey -in "$key_file" -pubout -outform DER |
        openssl dgst -sha256) || return 1
    [ "$cert_public" = "$key_public" ]
}

if [ -f "$cert" ] && [ -f "$key" ]; then
    if ! validate_pair "$cert" "$key"; then
        echo "Error: existing proxy certificate and key in $CERTS are invalid, expired, or do not match." >&2
        exit 1
    fi
    if [ -n "$active_resource" ]; then
        resource=$active_resource
        if [ "$resource" = secret ]; then name=nita-traefik-tls; else name=proxy-cert-cm; fi
        if ! kubectl get "$resource" "$name" -n nita --ignore-not-found -o json >"$tmpdir/active.json"; then
            echo "Error: unable to inspect the active proxy certificate." >&2
            exit 1
        fi
        if [ -s "$tmpdir/active.json" ]; then
            if ! python3 - "$tmpdir/active.json" "$resource" "$tmpdir/active.crt" <<'PY'
import base64
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    data = json.load(source)["data"]
cert = base64.b64decode(data["tls.crt"], validate=True) if sys.argv[2] == "secret" else data["nginx-certificate.crt"].encode()
with open(sys.argv[3], "wb") as target:
    target.write(cert)
PY
            then
                echo "Error: unable to read the active proxy certificate." >&2
                exit 1
            fi
            local_fingerprint=$(openssl x509 -in "$cert" -noout -fingerprint -sha256) || exit 1
            active_fingerprint=$(openssl x509 -in "$tmpdir/active.crt" -noout -fingerprint -sha256) || exit 1
            if [ "$local_fingerprint" != "$active_fingerprint" ]; then
                echo "Error: certificate in $CERTS differs from the active proxy certificate; restore the active pair before migration." >&2
                exit 1
            fi
        else
            echo "Error: active proxy certificate resource $name is missing." >&2
            exit 1
        fi
    fi
    echo "Using existing proxy certificate in $CERTS."
    exit 0
fi

if [ "$active_resource" != configmap ] && ! kubectl get secret nita-traefik-tls -n nita --ignore-not-found -o json >"$tmpdir/secret.json"; then
    echo "Error: unable to inspect the existing Traefik TLS Secret." >&2
    exit 1
fi
if [ "$active_resource" != configmap ] && [ -s "$tmpdir/secret.json" ]; then
    if ! python3 - "$tmpdir/secret.json" "$tmpdir/cert" "$tmpdir/key" <<'PY'
import base64
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    data = json.load(source)["data"]
for name, path in (("tls.crt", sys.argv[2]), ("tls.key", sys.argv[3])):
    with open(path, "wb") as target:
        target.write(base64.b64decode(data[name], validate=True))
PY
    then
        echo "Error: existing Traefik TLS Secret does not contain a usable certificate and key." >&2
        exit 1
    fi
    if ! validate_pair "$tmpdir/cert" "$tmpdir/key"; then
        echo "Error: existing Traefik TLS Secret contains an invalid, expired, or mismatched pair." >&2
        exit 1
    fi
    mkdir -p "$CERTS"
    install -m 644 "$tmpdir/cert" "$cert"
    install -m 600 "$tmpdir/key" "$key"
    echo "Restored the existing proxy certificate from nita-traefik-tls."
    exit 0
fi
if [ "$active_resource" = secret ]; then
    echo "Error: active Traefik TLS Secret is missing; restore it before continuing." >&2
    exit 1
fi

if ! kubectl get configmap proxy-cert-cm -n nita --ignore-not-found -o json >"$tmpdir/configmap.json"; then
    echo "Error: unable to inspect the existing proxy certificate ConfigMap." >&2
    exit 1
fi

if [ -s "$tmpdir/configmap.json" ]; then
    if ! python3 - "$tmpdir/configmap.json" "$tmpdir/cert" "$tmpdir/key" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    data = json.load(source)["data"]
with open(sys.argv[2], "w", encoding="utf-8") as cert:
    cert.write(data["nginx-certificate.crt"])
with open(sys.argv[3], "w", encoding="utf-8") as key:
    key.write(data["nginx-certificate-key.key"])
PY
    then
        echo "Error: existing proxy certificate ConfigMap does not contain a usable certificate and key." >&2
        exit 1
    fi
    if ! validate_pair "$tmpdir/cert" "$tmpdir/key"; then
        echo "Error: existing proxy certificate ConfigMap contains an invalid, expired, or mismatched pair." >&2
        exit 1
    fi
    mkdir -p "$CERTS"
    install -m 644 "$tmpdir/cert" "$cert"
    install -m 600 "$tmpdir/key" "$key"
    echo "Restored the existing proxy certificate from proxy-cert-cm."
    exit 0
fi

if [ -n "$active_resource" ] || [ -e "$cert" ] || [ -e "$key" ]; then
    echo "Error: existing proxy certificate or key is missing; restore the pair before continuing." >&2
    exit 1
fi

echo "Generating a self-signed proxy certificate."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$tmpdir/key" -out "$tmpdir/cert"
if ! validate_pair "$tmpdir/cert" "$tmpdir/key"; then
    echo "Error: generated proxy certificate and key are invalid." >&2
    exit 1
fi
mkdir -p "$CERTS"
install -m 644 "$tmpdir/cert" "$cert"
install -m 600 "$tmpdir/key" "$key"
