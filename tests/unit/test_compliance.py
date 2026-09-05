"""
Unit tests for compliance mapping (ISO/IEC 27037) and BSA Sec 63 draft certificates.
Legal Invariant: Never claims admissibility or self-certification.
"""

import pytest
from app.engine10_compliance import iso27037_mapper, bsa_sec63, report_builder


def test_iso27037_event_mapping():
    """
    Tests mapping audit log entries into the 4 ISO/IEC 27037 digital evidence phases.
    """
    audit_entries = [
        {"event_type": "case_create", "timestamp": "2026-09-04 10:00:00"},
        {"event_type": "acquisition_start", "timestamp": "2026-09-04 10:01:00"},
        {"event_type": "parse_hikfat", "timestamp": "2026-09-04 10:05:00"},
        {"event_type": "audit_chain_verify", "timestamp": "2026-09-04 10:10:00"},
    ]

    mapped = iso27037_mapper.map_case_to_iso27037(audit_entries)

    assert "Identification" in mapped
    assert "Acquisition" in mapped
    assert "Collection" in mapped
    assert "Preservation" in mapped

    assert len(mapped["Identification"]) == 1
    assert len(mapped["Acquisition"]) == 1
    assert len(mapped["Collection"]) == 1
    assert len(mapped["Preservation"]) == 1


def test_bsa_sec63_cert_draft_disclaimers():
    """
    Tests BSA Section 63 Part A & B certificate draft generation, verifying
    mandatory non-self-certifying disclaimers are attached.
    """
    case_info = {"case_id": "test_case_63", "investigator": "Officer Sharma", "created_at": "2026-09-04"}
    extracted_files = [
        {"file_id": "f1", "channel_id": 1, "file_hash": "sha256abc123", "extraction_type": "parsed"}
    ]
    audit_log = [{"event_type": "case_create", "timestamp": "2026-09-04"}]

    drafts = bsa_sec63.generate_bsa_sec63_cert_draft(case_info, extracted_files, audit_log)

    assert "part_a" in drafts
    assert "part_b" in drafts
    assert "disclaimer" in drafts

    disclaimer = bsa_sec63.SECTION_63_DISCLAIMER
    assert "Expert-ready technical draft" in disclaimer
    assert "not self-certifying" in disclaimer

    assert disclaimer in drafts["part_a"]
    assert disclaimer in drafts["part_b"]

    # Verify no claim of self-certification exists
    full_text = drafts["part_a"] + drafts["part_b"]
    assert "self-certifying" in full_text.lower()
    assert "court-admissible" not in full_text.lower()
