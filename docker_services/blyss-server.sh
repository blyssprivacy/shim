#!/bin/bash

USE_TEST_CERT=""
if cat /proc/cmdline | grep -q 'blyss_use_test_cert'; then
  echo "Using test certs"
  USE_TEST_CERT="--test-cert"
fi

# check attestation
cd /app/guest_tools/gpu_verifiers/local_gpu_verifier && /usr/bin/python3 -m verifier.cc_admin --allow_hold_cert

DOMAIN="enclave.blyss.dev"
if cat /proc/cmdline | grep -q 'blyss_disable_server'; then
  echo "Skipping cert issuance, generating a self-signed cert instead"

  mkdir -p /etc/letsencrypt/live/enclave.blyss.dev/

  openssl req -x509 -out /etc/letsencrypt/live/$DOMAIN/cert.pem -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
  -newkey rsa:2048 -nodes -sha256 \
  -subj "/CN=$DOMAIN" -extensions EXT -config <( \
   printf "[dn]\nCN=$DOMAIN\n[req]\ndistinguished_name = dn\n[EXT]\nsubjectAltName=DNS:$DOMAIN\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth")
  
  cp /etc/letsencrypt/live/$DOMAIN/cert.pem /etc/letsencrypt/live/$DOMAIN/fullchain.pem
else
  # issue cert
  /usr/bin/certbot certonly $USE_TEST_CERT --agree-tos -n -m support@blyss.dev --standalone -d $DOMAIN
fi

# produce full attestation at /var/www/html/attestation.json
cd /app/guest_app/guest_app && /usr/bin/python3 /app/guest_app/guest_app/main.py

# run nginx
/usr/sbin/nginx -g "daemon off;"