# Blyss Shim Dockerfile

# This Docker image contains the CPU and GPU attestation process and TLS
# termination service. At runtime, it requests attestations from the CPU and
# GPU, checks the GPU attestation, and outputs a resulting attestation.json file
# to local storage. If the GPU attestation was successful, this image will mark
# the GPU as "initialized" (trusted), avoiding later "system not yet
# initialized" errors.
#
# It then requests a TLS certificate from Let's Encrypt, and starts an HTTPS
# server with NGINX. The server terminates TLS connections using the certificate,
# forwarding the requests to the downstream service on port 8080. It also serves the
# attestation.json file at the well-known URL.
#
# It also checks the GPU attestation; if successful, this image will mark the
# GPU as "initialized" (trusted), avoiding later "system not yet initialized"
# errors.

# Build sev_attest_tool
FROM rust:1.74.0 as builder
WORKDIR /app
COPY sev_attest_tool .
RUN cargo install --path .

# Build the TLS termination service
FROM ubuntu:latest
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y python3 certbot python3-certbot-nginx nginx python3-pip \
  && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip

COPY guest_tools /app/guest_tools/
COPY guest_app /app/guest_app/
COPY docker_services /app/services/
RUN cd /app/guest_tools/gpu_verifiers/local_gpu_verifier && pip3 install . 
RUN cd /app/guest_tools/attestation_sdk && pip3 install . 
COPY driver_rims/RIM_GH100PROD.swidtag /usr/share/nvidia/rim/RIM_GH100PROD.swidtag
COPY docker_services/ffdhe2048.txt /etc/ssl/ffdhe2048
COPY --from=builder /usr/local/cargo/bin/sev_attest_tool /usr/local/bin/sev_attest_tool
COPY --from=builder /usr/local/cargo/bin/sev_attest_tool /home/guest/.cargo/bin/sev_attest_tool

RUN rm /etc/nginx/sites-enabled/default
RUN cp /app/services/blyss-server-nginx.conf /etc/nginx/sites-available/enclave.blyss.dev
RUN ln -s /etc/nginx/sites-available/enclave.blyss.dev /etc/nginx/sites-enabled/

CMD ["/app/services/blyss-server.sh"]

