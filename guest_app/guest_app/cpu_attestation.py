import json
import subprocess

CPU_ATTESTATION_BIN = "/home/guest/.cargo/bin/sev_attest_tool"
CPU_ATTESTATION_ARG = "generate-attestation"


class AttestationError(Exception):
    """An exception raised when the system is unable to perform attestation."""

    pass


def perform_cpu_attestation(associated_data: str) -> str:
    """Performs CPU attestation and returns the result as a string.

    Raises:
        RuntimeError: If the attestation binary fails to run.
        AttestationError: If the system is unable to perform attestation.

    Returns:
        str: The attestation result as a JSON string.
    """

    # Run the attestation binary.
    try:
        result = subprocess.run(
            [CPU_ATTESTATION_BIN, CPU_ATTESTATION_ARG, associated_data],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"CPU attestation binary failed with error code {e.returncode}.\n"
            f"Stdout: {e.stdout}\n"
            f"Stderr: {e.stderr}"
        )

    # Ensure that the attestation succeeded.
    if result.returncode != 0:
        raise AttestationError(
            f"CPU attestation failed with error code {result.returncode}.\n"
            f"Stdout: {result.stdout}\n"
            f"Stderr: {result.stderr}"
        )

    # Return the result as a string.
    return result.stdout.decode("utf-8")
