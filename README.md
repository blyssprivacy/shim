# Confidential Connector

The confidential connector uses new NVIDIA H100 hardware enclave technology
to establish an *end-to-end* secure tunnel between users and the GPU,
available publicly from `enclave.blyss.dev`.
The connector code (this repo), and associated services,
are open source, so that anyone can verify our claims.

The connector is part of the Blyss Confidential AI service, the first verifiably confidential LLM API endpoint.
Our goal is to make it impossible for interactions with LLMs to be monitored by anyone, 
including us, and to make that claim publicly verifiable. 

Details on our security model and roots of trust are available in our [deep dive](https://blog.blyss.dev/confidential-ai-from-gpu-enclaves/).

> [!NOTE]  
> The underlying NVIDIA Confidential Computing technology in the H100 is currently considered 'Early Access'. 

## Connector Responsibilities

The connector is run inside a CPU confidential VM, and is responsible for:

1. Requesting attestations from the CPU and GPU.
2. Requesting a TLS certificate for `enclave.blyss.dev` from Let's Encrypt.
3. Performing TLS termination, forwarding traffic to a local OpenAI-compatible chat completions service running on port 8000.
4. The connector also serves a full attestation document, which
proves that it is running in an authentic NVIDIA GPU, at 
`/.well-known/appspecific/dev.blyss.enclave.attestation/attestation.json`.

## Build

The connector can be built with:
```
docker build -t connector .
```

The public build of the connector is available as [`blintzbase/shim`](https://hub.docker.com/r/blintzbase/shim).