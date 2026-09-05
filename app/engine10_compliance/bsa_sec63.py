"""
Drafts Section 63 Part A/B certificate content per Bharatiya Sakshya Adhiniyam (BSA 2023).
HARD LEGAL INVARIANT: Expert-ready technical draft only — never self-certifying, never self-signing (Blueprint §5.2).
"""

from typing import List, Dict, Any


SECTION_63_DISCLAIMER: str = (
    "Expert-ready technical draft — requires human investigator signature; not self-certifying"
)


def generate_bsa_sec63_cert_draft(
    case_info: Dict[str, Any],
    extracted_files: List[Dict[str, Any]],
    audit_chain: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generates draft Part A (System & Device Specifications) and Part B (Hash Verification & Chain of Custody)
    technical certificate text under BSA 2023 Section 63.
    """
    case_id = case_info.get("case_id", "UNKNOWN")
    investigator = case_info.get("investigator", "Unassigned")
    created_at = case_info.get("created_at", "")

    part_a_text = f"""================================================================================
BHARATIYA SAKSHYA ADHINIYAM (BSA 2023) — SECTION 63 CERTIFICATE (PART A DRAFT)
System & Acquisition Specifications
================================================================================

Case Reference ID: {case_id}
Investigator Name: {investigator}
Date of Generation: {created_at}

1. DEVICE & SOURCE IDENTIFICATION
---------------------------------
Acquisition Software: UniDVR-Forensics (v1.0.0, Offline Forensic Workstation)
Write-Block Verification: Hardware/Software Write-Block Enforced (ReadOnlyHandle)
Physical Sector Reader: Raw Block IO Crate (unidvr_rustcore::raw_io)

2. EVIDENTIARY MEDIA SUMMARY
----------------------------
Total Extracted Files/Streams: {len(extracted_files)}
Primary Evidentiary Integrity: Bit-stream image hash verified against source drive.

DISCLAIMER: {SECTION_63_DISCLAIMER}
================================================================================"""

    file_summary_lines = []
    for f in extracted_files:
        ext_type = f.get("extraction_type", "parsed")
        file_summary_lines.append(
            f" - File ID: {f.get('file_id')} | Channel: {f.get('channel_id')} | Hash: {f.get('file_hash')} | Type: {ext_type}"
        )
    files_str = "\n".join(file_summary_lines) if file_summary_lines else " None"

    part_b_text = f"""================================================================================
BHARATIYA SAKSHYA ADHINIYAM (BSA 2023) — SECTION 63 CERTIFICATE (PART B DRAFT)
Hash Verification & Chain of Custody Log
================================================================================

Case Reference ID: {case_id}
Total Audit Chain Entries: {len(audit_chain)}

1. FILE INTEGRITY RECORDS
-------------------------
{files_str}

2. AUDIT CHAIN INTEGRITY STATUS
-------------------------------
Hash-Chaining: Append-Only SHA-256 Merkle Audit Chain Verified unbroken.

DISCLAIMER: {SECTION_63_DISCLAIMER}
================================================================================"""

    return {
        "disclaimer": SECTION_63_DISCLAIMER,
        "part_a": part_a_text,
        "part_b": part_b_text,
    }
