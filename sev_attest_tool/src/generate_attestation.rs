use sev::firmware::guest::*;

/// Performs an AMD-SEV attestation and returns the report
/// as a JSON string.
pub fn generate_attestation_report(data_to_attach: Option<String>) -> String {
    // This is the data we are attaching to the attestation request.
    // It is typically a public key that we want to prove was generated
    // in the enclave.
    let unique_data: [u8; 64] = data_to_attach.map_or([7; 64], |s| {
        hex::decode(s)
            .expect("data_to_attach was not a valid hex string")
            .try_into()
            .expect("data_to_attach was not 64 bytes")
    });

    // Open a connection to the firmware and request a standard attestation report
    let mut fw: Firmware = Firmware::open().expect("could not open /dev/sev-guest");
    let attestation_report = fw
        .get_report(None, Some(unique_data), None)
        .expect("could not generate attestation");

    // Serialize the report to JSON
    let report_json = serde_json::to_string(&attestation_report)
        .expect("could not serialize attestation to JSON");

    report_json
}
