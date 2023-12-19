import json
from typing import Tuple
from cpu_attestation import perform_cpu_attestation
from gpu_attestation import perform_gpu_attestation
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives import hashes
import os
import sys
import hashlib
import time

def pad_to_64_bytes(data: bytes) -> bytes:
    """Pad data to 64 bytes"""
    assert len(data) <= 64
    return data + b"\x00" * (64 - len(data))

# filename: sha256 hash
DO_CHECK_EXTERNAL_FILES = False
EXTERNAL_FILES_JSON_PATH = "/home/guest/nvtrust-private/guest_app/data/external_files.json"
EXTERNAL_FILES_MOUNT_PATH = "/mnt/exttmpfs"

def check_external_files():
    if len(EXTERNAL_FILES_MOUNT_PATH) == 0:
        return

    now = time.perf_counter()
    external_files = {}
    with open(EXTERNAL_FILES_JSON_PATH, "r") as f:
        external_files = json.load(f)

    for filename, sha256sum in external_files.items():
        if not os.path.isfile(os.path.join(EXTERNAL_FILES_MOUNT_PATH, filename)):
            print("ERROR: Missing external file: {}".format(filename))
            sys.exit(1)
        with open(os.path.join(EXTERNAL_FILES_MOUNT_PATH, filename), "rb") as f:
            # hash file without reading it into memory (it might be a big file!)
            file_hash = hashlib.sha256()
            while True:
                data = f.read(1048576)
                if not data:
                    break
                file_hash.update(data)
            if file_hash.hexdigest() != sha256sum:
                print(f"ERROR: External file {filename} has wrong hash")
                os.system('shutdown now')
                sys.exit(1)
            else:
                print(f"External file {filename} has correct hash {sha256sum}")
    print(f"Checked external files in {time.perf_counter() - now:.2f}s")

DOMAIN = "enclave.blyss.dev"
CERTS_DIR = "/etc/letsencrypt/live"
ATT_DIR = "/var/www/html"
ATT_NAME = "attestation.json"

def attest_tls():
    if DO_CHECK_EXTERNAL_FILES:
        check_external_files()

    pem_cert_path = f"{CERTS_DIR}/{DOMAIN}/cert.pem"
    pem_cert_bytes = open(pem_cert_path, "rb").read()
    cert = load_pem_x509_certificate(pem_cert_bytes)
    cert_fingerprint = cert.fingerprint(hashes.SHA256())
    padded_cert_fingerprint = pad_to_64_bytes(cert_fingerprint).hex()
    print("cert_fingerprint:", cert_fingerprint.hex())

    cpu_attestation_json = perform_cpu_attestation(padded_cert_fingerprint)
    gpu_attestation_json = perform_gpu_attestation()

    complete_attestation = {
        "cert_sha256_fingerprint": cert_fingerprint.hex(),
        "cpu_attestation": json.loads(cpu_attestation_json),
        "gpu_attestation": json.loads(gpu_attestation_json),
    }

    print()
    print()
    print()
    print(json.dumps(complete_attestation))

    fh = open(f"{ATT_DIR}/{ATT_NAME}", 'w')
    fh.write(json.dumps(complete_attestation))
    fh.close()

    # print("init model")
    # model, tokenizer = init_model()
    # sample_problem = "def return1():\n"
    # print("generate one completion")
    # completion = generate_one_completion(model, tokenizer, sample_problem)
    # print("problem:", sample_problem)
    # print()
    # print("completion:", completion)

    # while True:
    #     print("Enter a problem:")
    #     problem = input(">>> ")
    #     completion = generate_one_completion(model, tokenizer, problem)
    #     print("completion:", completion)


if __name__ == "__main__":
    attest_tls()
