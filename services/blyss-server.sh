#!/bin/bash

if cat /proc/cmdline | grep -q 'blyss_disable_server'; then
  echo "Skipping server setup"
  exit 1
fi

USE_TEST_CERT=""
if cat /proc/cmdline | grep -q 'blyss_use_test_cert'; then
  echo "Using test certs"
  USE_TEST_CERT="--test-cert"
fi

# to reset if inadvertently saved:
rm /var/www/html/attestation.json
/usr/bin/certbot delete -n --cert-name enclave.blyss.dev

# generates a keypair and fetches a cert via LE 
/usr/bin/certbot certonly $USE_TEST_CERT --agree-tos -n -m support@blyss.dev --standalone -d enclave.blyss.dev

# run the GPU attestation
cd /home/guest/nvtrust-private/guest_tools/gpu_verifiers/local_gpu_verifier && /usr/bin/python3 -m verifier.cc_admin --allow_hold_cert


# run the CPU + GPU attestations
/usr/bin/python3 /home/guest/nvtrust-private/guest_app/guest_app/main.py

# restart NGINX to use new cert from LE
systemctl restart nginx

# run the chat server
/home/guest/llama.cpp/server -m /home/guest/llama.cpp/models/phind-codellama-34b-v2.Q6_K.gguf -ngl 99999 --path /home/guest/nvtrust-private/chat_server