use openssl::x509::X509;
use sev::{
    certs::snp::{ca, Certificate, Chain, Verifiable},
    firmware::{guest::AttestationReport, host::TcbVersion},
};

pub const GENOA_PEM: &'static [u8] = include_bytes!("../data/Genoa.pem");
pub const SEV_PROD_NAME: &str = "Genoa";

pub const KDS_CERT_SITE: &str = "https://kdsintf.amd.com";
pub const KDS_VCEK: &str = "/vcek/v1";
pub const _KDS_CERT_CHAIN: &str = "cert_chain";

/// Converts a byte slice into a hex string
pub fn bytes_to_hex(buf: &[u8]) -> String {
    let mut hexstr = String::new();
    for &b in buf {
        hexstr.push_str(&format!("{:02x}", b));
    }
    hexstr
}

/// Requests the main AMD SEV-SNP certificate chain.
///
/// This is the chain of certificates up to the AMD Root Key (ARK).
/// The order is (chip) -> (vcek) -> (ask) -> (ark).
/// These may be used to verify the downloaded VCEK is authentic.
pub fn get_cert_chain(sev_prod_name: &str) -> ca::Chain {
    // The chain can be retrieved at "https://kdsintf.amd.com/vcek/v1/{SEV_PROD_NAME}/cert_chain"
    // let url = format!("{KDS_CERT_SITE}{KDS_VCEK}/{sev_prod_name}/{KDS_CERT_CHAIN}");
    // let pem = reqwest::blocking::get(&url).unwrap().bytes().unwrap().to_vec();

    if sev_prod_name != SEV_PROD_NAME {
        panic!("Only Genoa is supported at this time");
    }

    let chain = X509::stack_from_pem(&GENOA_PEM).unwrap();

    // Create a certificate chain with the ARK and ASK
    let (ark, ask) = (&chain[1].to_pem().unwrap(), &chain[0].to_pem().unwrap());
    let cert_chain = ca::Chain::from_pem(ark, ask).unwrap();

    cert_chain
}

/// Requests the VCEK for the specified chip and TCP.
///
/// The VCEK is the "Versioned Chip Endorsement Key" for a particular chip and TCB.
/// It is used to verify the authenticity of the attestation report.
///
/// The VCEK is retrieved from the AMD Key Distribution Service (KDS),
/// and generated on the first request to the service. The returned certificate is
/// valid for 7 years from issuance.
///
/// This function returns the VCEK as a DER-encoded X509 certificate.
pub fn request_vcek(chip_id: [u8; 64], reported_tcb: TcbVersion, sev_prod_name: &str) -> Vec<u8> {
    let hw_id = bytes_to_hex(&chip_id);
    let url = format!(
    "{KDS_CERT_SITE}{KDS_VCEK}/{sev_prod_name}/{hw_id}?blSPL={:02}&teeSPL={:02}&snpSPL={:02}&ucodeSPL={:02}",
        reported_tcb.bootloader,
        reported_tcb.tee,
        reported_tcb.snp,
        reported_tcb.microcode,
        );
    println!("Requesting VCEK from: {url}\n");
    let rsp_bytes = reqwest::blocking::get(&url)
        .unwrap()
        .bytes()
        .unwrap()
        .to_vec();
    rsp_bytes
}

pub fn verify_attestation_report(path: &str, fail_on_purpose: bool, vcek_path: Option<&str>) {
    // Read the report from the file
    let report_json_str = std::fs::read_to_string(path).unwrap();

    // Deserialize the report
    let mut report: AttestationReport = serde_json::from_str(&report_json_str).unwrap();
    if fail_on_purpose {
        report.measurement[0] = report.measurement[0].wrapping_add(1);
    }

    // Extract info from report
    let chip_id = report.chip_id;
    let reported_tcb = report.reported_tcb;

    // Get the VCEK
    let vcek_bytes = vcek_path
        .map(|path| std::fs::read(path).unwrap())
        .unwrap_or_else(|| request_vcek(chip_id, reported_tcb, SEV_PROD_NAME));
    let vcek = Certificate::from_der(&vcek_bytes).unwrap().into();

    // Get the ARK and ASK certificates
    let cert_chain = get_cert_chain(SEV_PROD_NAME);

    // Create the full certificate chain
    let full_cert_chain = Chain {
        ca: cert_chain,
        vcek,
    };

    // Verify the full certificate chain (VCEK -> ASK -> ARK), and then
    // check that the attestation report is signed by the VCEK.
    let verification_result = (&full_cert_chain, &report).verify();

    match verification_result {
        Ok(_) => println!("RESULT: PASS\nVerification successful!"),
        Err(e) => println!("RESULT: FAIL\nVerification failed: {}", e),
    }
}

#[cfg(test)]
mod test {
    use super::*;

    const SAMPLE_ATTESTATION: &'static str = include_str!("../data/sample_attestation_report.json");
    const SAMPLE_VCEK: &'static [u8] = include_bytes!("../data/sample_vcek.crt");

    #[test]
    fn test_bytes_to_hex() {
        assert_eq!(bytes_to_hex(&[0x01, 0x02, 0x03]), "010203");
    }

    #[test]
    fn test_sample_attestation_verifies() {
        let report: AttestationReport = serde_json::from_str(SAMPLE_ATTESTATION).unwrap();
        let vcek = Certificate::from_der(SAMPLE_VCEK).unwrap().into();
        let cert_chain = get_cert_chain(SEV_PROD_NAME);
        let full_cert_chain = Chain {
            ca: cert_chain,
            vcek,
        };

        let verification_result = (&full_cert_chain, &report).verify();
        assert!(verification_result.is_ok());
    }

    #[test]
    fn test_tampered_sample_attestation_fails_verification() {
        let mut report: AttestationReport = serde_json::from_str(SAMPLE_ATTESTATION).unwrap();
        report.measurement[0] = report.measurement[0].wrapping_add(1);

        let vcek = Certificate::from_der(SAMPLE_VCEK).unwrap().into();
        let cert_chain = get_cert_chain(SEV_PROD_NAME);
        let full_cert_chain = Chain {
            ca: cert_chain,
            vcek,
        };

        let verification_result = (&full_cert_chain, &report).verify();
        assert!(verification_result.is_err());
    }
}
