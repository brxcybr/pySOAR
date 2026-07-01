#!/usr/bin/env bash
# Generate self-signed CA and server certificates for lab pfSense/MISP TLS testing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CERT_DIR="${CERT_DIR:-$ROOT/certs}"
DAYS="${CERT_DAYS:-3650}"
CN="${CERT_CN:-pysoar.lab.local}"

mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

if [[ -f CA.crt && -f api_user.crt ]]; then
  echo "Certificates already exist in $CERT_DIR (delete to regenerate)."
  exit 0
fi

echo "Generating lab CA and certificates in $CERT_DIR"

openssl genrsa -out CA.key 4096
openssl req -x509 -new -nodes -key CA.key -sha256 -days "$DAYS" \
  -out CA.crt -subj "/CN=PySOAR Lab CA"

openssl genrsa -out api_user.key 2048
openssl req -new -key api_user.key -out api_user.csr \
  -subj "/CN=$CN"
openssl x509 -req -in api_user.csr -CA CA.crt -CAkey CA.key -CAcreateserial \
  -out api_user.crt -days "$DAYS" -sha256

openssl genrsa -out misp_server.key 2048
openssl req -new -key misp_server.key -out misp_server.csr \
  -subj "/CN=misp.$CN"
openssl x509 -req -in misp_server.csr -CA CA.crt -CAkey CA.key -CAcreateserial \
  -out misp_server.crt -days "$DAYS" -sha256

chmod 600 *.key 2>/dev/null || true
echo "Generated: CA.crt, api_user.crt/key, misp_server.crt/key"
