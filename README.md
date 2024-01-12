# Blyss Confidential AI Shim

The Blyss Confidential AI Shim is a Docker service that verifies GPU attestations, requests certificates from Let's Encrypt, and proxies requests to an LLM.

For more details, see [this launch post](https://blog.blyss.dev/launching-blyss-confidential-ai) and [this technical deep-dive](https://blog.blyss.dev/confidential-ai-from-gpu-enclaves/).

The shim runs from inside the secure VM, and proceeds as follows:
- At startup, the shim requests attestations from the CPU and
GPU, checks the GPU attestation, and outputs a resulting attestation.json file
to local storage. If the GPU attestation was successful, this image will mark
the GPU as "initialized" (trusted), avoiding later "system not yet
initialized" errors. If not, subsequent access to the GPU will fail.
- The shim generates a private key, and then requests a TLS certificate from Let's Encrypt.
- Finally, the shim starts an HTTPS server with NGINX. 
The server terminates TLS connections using the certificate,
forwarding the requests to the downstream service on port 8080. 
It also serves the
attestation.json file at `/.well-known/appspecific/dev.blyss.enclave/attestation.json`.