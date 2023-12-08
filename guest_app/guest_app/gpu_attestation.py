from nv_attestation_sdk import attestation
from cryptography.x509 import Certificate
from cryptography.hazmat.primitives.serialization import Encoding

import logging
import json
import traceback

from typing import Any, cast, Optional

from verifier.attestation import AttestationReport
from verifier.attestation.spdm_msrt_resp_msg import MeasurementRecord, OpaqueData
from verifier.cc_admin import create_jwt_token
from verifier.rim import RIM
from verifier.nvml import (
    NvmlHandler,
    NvmlHandlerTest,
)
from verifier.verifier import Verifier
from verifier.config import (
    BaseSettings,
    HopperSettings,
    event_log,
    info_log,
    __author__,
    __copyright__,
    __version__,
)
from verifier.exceptions import (
    Error,
    RIMFetchError,
    NoGpuFoundError,
    UnsupportedGpuArchitectureError,
    CertChainVerificationFailureError,
    AttestationReportVerificationError,
    RIMVerificationFailureError,
    UnknownGpuArchitectureError,
)
from verifier.exceptions.utils import is_non_fatal_issue
from verifier.cc_admin_utils import CcAdminUtils
from nv_attestation_sdk.attestation import VerifierFields

# ignore on-hold certs (for the "early access" period)
BaseSettings.allow_hold_cert = True

def serialize_measurement_record(measurement_record: MeasurementRecord) -> dict:
    return {
        "measurements": cast(list[Optional[str]], measurement_record.get_measurements())
    }


def serialize_opaque_data(opaque_data: OpaqueData) -> dict:
    data = cast(dict, opaque_data.OpaqueDataField)
    return {"opaque_data": data}


def serialize_attestation_report(attestation_report: AttestationReport) -> dict:
    req = attestation_report.get_request_message()
    resp = attestation_report.get_response_message()

    return {
        "request": {
            "spdm_version": cast(bytes, req.get_spdm_version()).hex(),
            "request_response_code": cast(bytes, req.get_request_response_code()).hex(),
            "param1": cast(bytes, req.get_param1()).hex(),
            "param2": cast(bytes, req.get_param2()).hex(),
            "nonce": cast(bytes, req.get_nonce()).hex(),
            "slot_id_param": cast(bytes, req.get_slot_id_param()).hex(),
        },
        "response": {
            "spdm_version": cast(bytes, resp.get_spdm_version()).hex(),
            "request_response_code": cast(
                bytes, resp.get_request_response_code()
            ).hex(),
            "param1": cast(bytes, resp.get_param1()).hex(),
            "param2": cast(bytes, resp.get_param2()).hex(),
            "number_of_blocks": resp.get_number_of_blocks(),
            "measurement_record_length": resp.get_measurement_record_length(),
            "measurement_record": serialize_measurement_record(
                cast(MeasurementRecord, resp.get_measurement_record())
            ),
            "nonce": cast(bytes, resp.get_nonce()).hex(),
            "opaque_data_length": resp.get_opaque_data_length(),
            "opaque_data": serialize_opaque_data(
                cast(OpaqueData, resp.get_opaque_data())
            ),
            "signature": cast(bytes, resp.get_signature()).hex(),
        },
    }


def custom_cc_admin_attest(arguments_as_dictionary):
    """Custom version of `verifier.cc_admin.attest` to perform GPU Attestation, and return the actual
    underlying attestation report and certificate chain.

    Args:
        arguments_as_dictionary (dict): the dictionary object containing attestation options.

    Returns:
        A tuple containing the attestation result (boolean), attestation claims (dict), and
        a complete, JSON-serializable attestation report with certificate chain data (dict).
    """
    overall_status = False
    verified_claims = {}
    report = {}
    settings = None
    gpu_info_obj = None
    try:
        if arguments_as_dictionary["verbose"]:
            info_log.setLevel(logging.DEBUG)

        if arguments_as_dictionary["test_no_gpu"]:
            event_log.info("Running in test_no_gpu mode.")
            number_of_available_gpus = NvmlHandlerTest.get_number_of_gpus()
        else:
            event_log.debug("Initializing the nvml library")
            NvmlHandler.init_nvml()

            if not NvmlHandler.is_cc_enabled():
                err_msg = (
                    "The confidential compute feature is disabled !!\nQuitting now."
                )
                raise Error(err_msg)

            if NvmlHandler.is_cc_dev_mode():
                info_log.info("The system is running in CC DevTools mode !!")
            number_of_available_gpus = NvmlHandler.get_number_of_gpus()

        if number_of_available_gpus == 0:
            err_msg = "No GPU found"
            info_log.critical(err_msg)
            raise NoGpuFoundError(err_msg)

        BaseSettings.mark_gpu_as_available()

        info_log.info(f"Number of GPUs available : {number_of_available_gpus}")

        report["gpus"] = []

        for i in range(number_of_available_gpus):
            info_log.info("-----------------------------------")
            info_log.info(f"Fetching GPU {i} information from GPU driver.")
            nonce_for_attestation_report = CcAdminUtils.generate_nonce(
                BaseSettings.SIZE_OF_NONCE_IN_BYTES
            )

            if arguments_as_dictionary["test_no_gpu"]:
                nonce_for_attestation_report = BaseSettings.NONCE
                gpu_info_obj = NvmlHandlerTest(settings=BaseSettings)
            else:
                gpu_info_obj = NvmlHandler(
                    index=i, nonce=nonce_for_attestation_report, settings=BaseSettings
                )

            if gpu_info_obj.get_gpu_architecture() == "HOPPER":
                event_log.debug(f"The architecture of the GPU with index {i} is HOPPER")
                settings = HopperSettings()

                if (
                    arguments_as_dictionary["driver_rim"] is None
                    and not arguments_as_dictionary["test_no_gpu"]
                ):
                    raise RIMFetchError("Driver RIM file path not provided!!")

                HopperSettings.set_driver_rim_path(
                    arguments_as_dictionary["driver_rim"]
                )
                HopperSettings.set_vbios_rim_path(arguments_as_dictionary["vbios_rim"])

                if arguments_as_dictionary["test_no_gpu"]:
                    HopperSettings.set_driver_rim_path(
                        HopperSettings.TEST_NO_GPU_DRIVER_RIM_PATH
                    )
                    HopperSettings.set_vbios_rim_path(
                        HopperSettings.TEST_NO_GPU_VBIOS_RIM_PATH
                    )
            else:
                err_msg = "Unknown GPU architecture."
                event_log.error(err_msg)
                raise UnknownGpuArchitectureError(err_msg)

            event_log.debug("GPU info fetched successfully.")
            settings.mark_gpu_info_fetched()

            info_log.info(f"VERIFYING GPU : {i}")

            if gpu_info_obj.get_gpu_architecture() != settings.GpuArch:
                err_msg = "\tGPU architecture is not supported."
                event_log.error(err_msg)
                raise UnsupportedGpuArchitectureError(err_msg)

            event_log.debug("\tGPU architecture is correct.")
            settings.mark_gpu_arch_is_correct()

            driver_version = gpu_info_obj.get_driver_version()
            vbios_version = gpu_info_obj.get_vbios_version()
            vbios_version = vbios_version.lower()

            info_log.info(f"\tDriver version fetched : {driver_version}")
            info_log.info(f"\tVBIOS version fetched : {vbios_version}")

            event_log.debug(f"GPU info fetched : \n\t\t{vars(gpu_info_obj)}")

            info_log.info("\tValidating GPU certificate chains.")
            gpu_attestation_cert_chain = gpu_info_obj.get_attestation_cert_chain()

            for certificate in gpu_attestation_cert_chain:
                cert = certificate.to_cryptography()
                issuer = cert.issuer.public_bytes()
                subject = cert.subject.public_bytes()

                if issuer == subject:
                    event_log.debug("Root certificate is a available.")
                    settings.mark_root_cert_available()

            gpu_leaf_cert = gpu_attestation_cert_chain[0]
            event_log.debug("\t\tverifying attestation certificate chain.")
            cert_verification_status = CcAdminUtils.verify_certificate_chain(
                gpu_attestation_cert_chain,
                settings,
                BaseSettings.Certificate_Chain_Verification_Mode.GPU_ATTESTATION,
            )

            if not cert_verification_status:
                err_msg = (
                    "\t\tGPU attestation report certificate chain validation failed."
                )
                event_log.error(err_msg)
                raise CertChainVerificationFailureError(err_msg)
            else:
                settings.mark_gpu_cert_chain_verified()
                info_log.info(
                    "\t\tGPU attestation report certificate chain validation successful."
                )

            cert_chain_revocation_status = (
                CcAdminUtils.ocsp_certificate_chain_validation(
                    gpu_attestation_cert_chain,
                    settings,
                    BaseSettings.Certificate_Chain_Verification_Mode.GPU_ATTESTATION,
                )
            )

            if not cert_chain_revocation_status:
                err_msg = "\t\tGPU attestation report certificate chain revocation validation failed."
                event_log.error(err_msg)
                raise CertChainVerificationFailureError(err_msg)

            settings.mark_gpu_cert_check_complete()

            info_log.info("\tAuthenticating attestation report")
            attestation_report_data = gpu_info_obj.get_attestation_report()
            attestation_report_obj = AttestationReport(
                attestation_report_data, settings
            )
            attestation_report_obj.print_obj(info_log)
            settings.mark_attestation_report_parsed()
            attestation_report_verification_status = (
                CcAdminUtils.verify_attestation_report(
                    attestation_report_obj=attestation_report_obj,
                    gpu_leaf_certificate=gpu_leaf_cert,
                    nonce=nonce_for_attestation_report,
                    driver_version=driver_version,
                    vbios_version=vbios_version,
                    settings=settings,
                )
            )
            if attestation_report_verification_status:
                settings.mark_attestation_report_verified()
                info_log.info("\t\tAttestation report verification successful.")
            else:
                err_msg = "\t\tAttestation report verification failed."
                event_log.error(err_msg)
                raise AttestationReportVerificationError(err_msg)

            # performing the schema validation and signature verification if the driver RIM.
            info_log.info("\tAuthenticating the RIMs.")
            info_log.info("\t\tAuthenticating Driver RIM")
            driver_rim = RIM(
                settings.DRIVER_RIM_PATH, rim_name="driver", settings=settings
            )
            driver_rim_verification_status = driver_rim.verify(
                version=driver_version, settings=settings
            )

            if driver_rim_verification_status:
                settings.mark_driver_rim_signature_verified()
                info_log.info("\t\t\tDriver RIM verification successful")
            else:
                event_log.error("\t\t\tDriver RIM verification failed.")
                raise RIMVerificationFailureError(
                    "\t\t\tDriver RIM verification failed.\n\t\t\tQuitting now."
                )

            # performing the schema validation and signature verification if the vbios RIM.
            info_log.info("\t\tAuthenticating VBIOS RIM.")
            vbios_rim_path = settings.VBIOS_RIM_PATH

            if (
                arguments_as_dictionary["vbios_rim"] is None
                and not arguments_as_dictionary["test_no_gpu"]
            ):
                vbios_rim_path = CcAdminUtils.get_vbios_rim_path(
                    settings, attestation_report_obj
                )

            vbios_rim = RIM(vbios_rim_path, rim_name="vbios", settings=settings)
            vbios_rim_verification_status = vbios_rim.verify(
                version=vbios_version, settings=settings
            )

            if vbios_rim_verification_status:
                settings.mark_vbios_rim_signature_verified()
                info_log.info("\t\t\tVBIOS RIM verification successful")
            else:
                event_log.error("\t\tVBIOS RIM verification failed.")
                raise RIMVerificationFailureError(
                    "\t\tVBIOS RIM verification failed.\n\tQuitting now."
                )

            verifier_obj = Verifier(
                attestation_report_obj, driver_rim, vbios_rim, settings=settings
            )
            verifier_obj.verify(settings)

            driver_rim_file_contents = ""
            with open(settings.DRIVER_RIM_PATH) as f:
                driver_rim_file_contents = f.read()
            vbios_rim_file_contents = ""
            with open(vbios_rim_path) as f:
                vbios_rim_file_contents = f.read()

            report["gpus"].append(
                {
                    "gpu_idx": i,
                    "nonce": nonce_for_attestation_report,
                    "gpu_attestation_cert_chain": gpu_attestation_cert_chain,
                    "attestation_report_obj": serialize_attestation_report(
                        attestation_report_obj
                    ),
                    "driver_rim": driver_rim_file_contents,
                    "vbios_rim": vbios_rim_file_contents,
                    "gpu_info_obj": {
                        "architecture": gpu_info_obj.get_gpu_architecture(),
                        "uuid": gpu_info_obj.get_uuid(),
                        "driver_version": gpu_info_obj.get_driver_version(),
                        "vbios_version": gpu_info_obj.get_vbios_version(),
                    },
                }
            )

            # Checking the attestation status.
            if settings.check_status():
                if (
                    not arguments_as_dictionary["user_mode"]
                    and not arguments_as_dictionary["test_no_gpu"]
                ):
                    info_log.info("\tSetting the GPU Ready State to READY.")
                    NvmlHandler.set_gpu_ready_state(True)

                info_log.info(f"\tGPU {i} verified successfully.")

            elif arguments_as_dictionary["test_no_gpu"]:
                pass
            else:
                if (
                    not NvmlHandler.is_cc_dev_mode()
                    and not arguments_as_dictionary["user_mode"]
                ):
                    info_log.info("\tSetting the GPU Ready State to NOT READY.")
                    NvmlHandler.set_gpu_ready_state(False)
                elif (
                    NvmlHandler.is_cc_dev_mode()
                    and not arguments_as_dictionary["user_mode"]
                ):
                    info_log.info(
                        "\tSetting the GPU Ready State to READY as the system is in DEV mode."
                    )
                    NvmlHandler.set_gpu_ready_state(True)

                info_log.info(f"The verification of GPU {i} resulted in failure.")

            if i == 0:
                overall_status = settings.check_status()
            else:
                overall_status = overall_status and settings.check_status()

    except Exception as error:
        info_log.error(error)
        print(traceback.format_exc())

        if arguments_as_dictionary["test_no_gpu"]:
            raise error

        if is_non_fatal_issue(error):
            # Do not retry
            # retry(error, arguments_as_dictionary["user_mode"])
            raise error

        else:
            gpu_state = False
            ready_str = 'NOT READY'
            if NvmlHandler.is_cc_dev_mode():
                info_log.info('\tGPU is running in DevTools mode!!')
                gpu_state = True
                ready_str = 'READY'
            if not arguments_as_dictionary["user_mode"]:
                if NvmlHandler.get_gpu_ready_state() != gpu_state:
                    info_log.info(f'\tSetting the GPU Ready State to {ready_str}')
                    NvmlHandler.set_gpu_ready_state(gpu_state)
                else:
                    info_log.info(f'\tGPU Ready state is already {ready_str}')


    finally:
        event_log.debug("-----------------------------------")
        if overall_status:
            info_log.info(f"\tGPU Attested Successfully")
        else:
            info_log.info(f"\tGPU Attestation failed")

        # check status and update the claims list in the finally block such that
        # un-checked claims will be false in case of exceptions

        if gpu_info_obj is not None:
            assert settings is not None
            settings.check_status()
            verified_claims = settings.claims
            verified_claims["x-nv-gpu-uuid"] = gpu_info_obj.get_uuid()
        else:
            verified_claims = {}
        formatted_claims_str = json.dumps(verified_claims, indent=2)
        event_log.debug(f"\tGPU Verified claims list : {formatted_claims_str}")
        event_log.debug("-----------------------------------")
        jwt_claims = create_jwt_token(verified_claims)
        return overall_status, jwt_claims, report


def custom_fetch_full_gpu_attestation():
    params = {
        "verbose": False,
        "test_no_gpu": False,
        "driver_rim": "/usr/share/nvidia/rim/RIM_GH100PROD.swidtag",
        "vbios_rim": None,
        "user_mode": True,
    }
    attestation_result, jwt_token, attestation_report = custom_cc_admin_attest(params)
    return attestation_result, jwt_token, attestation_report


def custom_serializer(x: Any):
    if isinstance(x, Certificate):
        return x.public_bytes(Encoding.PEM).decode("utf-8")
    elif isinstance(x, bytes):
        return x.hex()
    else:
        raise TypeError(f"Object of type {type(x)} is not JSON serializable")


def perform_gpu_attestation() -> str:
    client = attestation.Attestation()
    client.set_name("MainNode")

    client.add_verifier(attestation.Devices.GPU, attestation.Environment.LOCAL, "", "")
    attestation_results_policy = """\
    {
    "version": "1.0",
        "authorization-rules": {
            "x-nv-gpu-available": true,
            "x-nv-gpu-attestation-report-available": true,
            "x-nv-gpu-info-fetched": true,
            "x-nv-gpu-arch-check": true,
            "x-nv-gpu-root-cert-available": true,
            "x-nv-gpu-cert-chain-verified": true,
            "x-nv-gpu-ocsp-cert-chain-verified": true,
            "x-nv-gpu-ocsp-signature-verified": true,
            "x-nv-gpu-cert-ocsp-nonce-match": true,
            "x-nv-gpu-cert-check-complete": true,
            "x-nv-gpu-measurement-available": true,
            "x-nv-gpu-attestation-report-parsed": true,
            "x-nv-gpu-nonce-match": true,
            "x-nv-gpu-attestation-report-driver-version-match": true,
            "x-nv-gpu-attestation-report-vbios-version-match": true,
            "x-nv-gpu-attestation-report-verified": true,
            "x-nv-gpu-driver-rim-schema-fetched": true,
            "x-nv-gpu-driver-rim-schema-validated": true,
            "x-nv-gpu-driver-rim-cert-extracted": true,
            "x-nv-gpu-driver-rim-signature-verified": true,
            "x-nv-gpu-driver-rim-driver-measurements-available": true,
            "x-nv-gpu-driver-vbios-rim-fetched": true,
            "x-nv-gpu-vbios-rim-schema-validated": true,
            "x-nv-gpu-vbios-rim-cert-extracted": true,
            "x-nv-gpu-vbios-rim-signature-verified": true,
            "x-nv-gpu-vbios-rim-driver-measurements-available": true,
            "x-nv-gpu-vbios-index-no-conflict": true,
            "x-nv-gpu-measurements-match": true
        }
    }
    """

    attestation_result, token, full_report = custom_fetch_full_gpu_attestation()

    assert attestation_result == True

    print("Got token:", token)

    client._verifiers[0][VerifierFields.JWT_TOKEN] = token
    eat_token = client._create_EAT()

    assert attestation.Attestation.validate_token(
        attestation_results_policy, x=eat_token
    )

    return json.dumps(full_report, indent=2, default=custom_serializer)
