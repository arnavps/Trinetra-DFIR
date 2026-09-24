"""
Unit tests for compliance mapping (ISO/IEC 27037) and BSA Sec 63 draft certificates.
Legal Invariant: Never claims admissibility or self-certification.
Acceptance Criteria:
- Full 14-section technical report rendering with real data
- Live chain-integrity re-run verifying FAIL on tampered chain
- Summary report scope isolating sections 1-5 with summary notice
- Report self-integrity SHA-256 companion file and audit event
- Vocabulary cleanliness: zero hits for forbidden terms outside statutory disclaimers
"""

import hashlib
import json
import os
import sqlite3
import pytest
from pypdf import PdfReader

from app.engine10_compliance import iso27037_mapper, bsa_sec63, report_builder
from app.engine7_case_db.db import init_db, get_db_connection
from app.engine7_case_db.audit_log import log_event, record_extracted_file
from app.engine7_case_db.models import ExtractedFile, INVESTIGATIVE_LEAD_LABEL


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

    full_text = drafts["part_a"] + drafts["part_b"]
    assert "self-certifying" in full_text.lower()
    assert "court-admissible" not in full_text.lower()


@pytest.fixture
def populated_case_db(tmp_path):
    """Creates a real case SQLite database populated with real multi-subsystem records."""
    db_path = str(tmp_path / "test_case.db")
    case_id = "CR-2026-0042"
    init_db(db_path)

    conn = get_db_connection(db_path)
    with conn:
        conn.execute(
            "INSERT INTO cases (case_id, name, investigator, created_at) VALUES (?, ?, ?, ?)",
            (case_id, "State vs Cyber Intruder", "Det. A. Roy", "2026-09-24T10:00:00Z")
        )
    conn.close()

    # 1. Parsed file & Carved fragment
    f_parsed = ExtractedFile(
        file_id="CH01_VIDEO_0001.mp4",
        case_id=case_id,
        channel_id=1,
        start_timestamp="2026-09-24 10:05:00",
        end_timestamp="2026-09-24 10:15:00",
        size_bytes=5242880,
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        extraction_type="parsed",
        storage_path="Sectors 2048-12288"
    )
    record_extracted_file(db_path, f_parsed)

    f_carved = ExtractedFile(
        file_id="CARVED_FRAG_0001",
        case_id=case_id,
        channel_id=1,
        start_timestamp="Heuristic Recovery",
        end_timestamp="Unallocated Space",
        size_bytes=65536,
        file_hash="87298379be27038bbde33f26047ebcc89389e782f9d863f66c9ff99a9a5f7823",
        extraction_type="carved_fragment",
        storage_path="Unallocated Sectors 45000-45128"
    )
    record_extracted_file(db_path, f_carved)

    # 2. Audit log sequence
    log_event(db_path, case_id, "CASE_INTAKE", {"source": "hik_nvr_disk.dd", "write_block": True})
    log_event(db_path, case_id, "OEM_DETECT", {"oem": "Hikvision", "fs": "HIKFAT"})
    log_event(db_path, case_id, "PARSE_COMPLETE", {"files_indexed": 1})
    log_event(db_path, case_id, "CARVER_SCAN_COMPLETE", {"fragments_recovered": 1})
    log_event(db_path, case_id, "TAMPER_CHECK_RUN", {"total_frames": 40, "anomalies_list": []})

    # 3. AI Detections: 1 Verified, 1 Simulated
    conn = get_db_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO detections (detection_id, file_id, timestamp, frame_index, class_name, confidence, bbox_json, is_simulated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("DET-001", "CH01_VIDEO_0001.mp4", "2026-09-24 10:06:12", 30, "person", 0.94, "[10, 20, 80, 150]", 0)
        )
        conn.execute(
            """
            INSERT INTO detections (detection_id, file_id, timestamp, frame_index, class_name, confidence, bbox_json, is_simulated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("DET-002", "CH01_VIDEO_0001.mp4", "2026-09-24 10:08:45", 150, "vehicle", 0.81, "[100, 200, 250, 320]", 1)
        )
        # 4. Bookmark
        conn.execute(
            """
            INSERT INTO bookmarks (id, case_id, reference, note, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("BM-001", case_id, "CH01_VIDEO_0001.mp4 @ 10:06:12", "Subject observed entering restricted bay.", "Det. A. Roy", "2026-09-24T10:20:00Z")
        )
    conn.close()

    return db_path, case_id


def test_full_technical_report_14_sections(populated_case_db, tmp_path):
    """
    Generates Full Technical Report against real case data.
    Verifies all 14 sections render, sections 9a/9b and 10 never cross-contaminate.
    """
    db_path, case_id = populated_case_db
    pdf_out = str(tmp_path / "Full_Report.pdf")

    report_builder.generate_case_report_pdf(db_path, case_id, pdf_out, mode="full")
    assert os.path.exists(pdf_out)

    reader = PdfReader(pdf_out)
    num_pages = len(reader.pages)
    assert num_pages >= 10, f"Full report should span multiple pages, got {num_pages}"

    full_text = "\n".join(p.extract_text() for p in reader.pages)
    norm_text = " ".join(full_text.split())

    # Check all 14 sections
    required_sections = [
        "FULL TECHNICAL FORENSIC REPORT",
        "TABLE OF CONTENTS",
        "SECTION 2: EXECUTIVE SUMMARY",
        "SECTION 3: CASE & PARTY DETAILS",
        "SECTION 4: EVIDENCE INVENTORY",
        "SECTION 5: ACQUISITION & INTEGRITY SUMMARY",
        "SECTION 6: ISO/IEC 27037 ACTIVITY MAPPING",
        "SECTION 7: CHAIN OF CUSTODY AUDIT LOG",
        "SECTION 8: TIMELINE RECONSTRUCTION",
        "SECTION 9: AI-ASSISTED TRIAGE FINDINGS",
        "SECTION 10: INVESTIGATOR FINDINGS & MANUAL BOOKMARKS",
        "SECTION 11: RECOVERED & CARVED EVIDENCE SUMMARY",
        "SECTION 12: VIDEO TAMPER & ANTI-SPLICING INTEGRITY RESULTS",
        "SECTION 13: METHODOLOGY & REPRODUCIBILITY STATEMENT",
        "SECTION 14: APPENDICES & TECHNICAL GLOSSARY",
    ]
    for sec in required_sections:
        assert sec in norm_text, f"Missing section heading in full report: '{sec}'"

    # Verify real data renders
    assert "CH01_VIDEO_0001.mp4" in norm_text
    assert "CARVED_FRAG_0001" in norm_text
    assert "State vs Cyber Intruder" in norm_text
    assert "Det. A. Roy" in norm_text
    assert "Subject observed entering restricted bay." in norm_text

    # Verify AI 9a vs 9b isolation
    assert "9a. Verified Findings" in norm_text
    assert "9b. Simulated Findings" in norm_text
    assert "The following results were produced by a model running in simulated mode" in norm_text
    assert INVESTIGATIVE_LEAD_LABEL in norm_text

    # Section 10 human-authored isolation: verify bookmarks note is present
    assert "Subject observed entering restricted bay." in norm_text
    assert "BM-001" in norm_text

    # Chain of custody status: PASS
    assert "LIVE CRYPTOGRAPHIC CHAIN INTEGRITY: PASS" in norm_text


def test_live_chain_breakage_detection(populated_case_db, tmp_path):
    """
    Deliberately breaks audit chain in DB, generates report,
    and asserts report shows FAIL with specific broken entry cited.
    """
    db_path, case_id = populated_case_db

    # Deliberately tamper with entry #3
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("UPDATE audit_log SET details = '{\"tampered\": true}' WHERE entry_id = 3")
    conn.close()

    pdf_out = str(tmp_path / "Tampered_Report.pdf")
    report_builder.generate_case_report_pdf(db_path, case_id, pdf_out, mode="full")

    reader = PdfReader(pdf_out)
    full_text = "\n".join(p.extract_text() for p in reader.pages)
    norm_text = " ".join(full_text.split())

    assert "LIVE CRYPTOGRAPHIC CHAIN INTEGRITY: FAIL" in norm_text
    assert "entry #3" in norm_text.lower() or "entry # 3" in norm_text.lower() or "#3" in norm_text


def test_summary_report_scope(populated_case_db, tmp_path):
    """
    Generates Summary Report mode.
    Confirms it never includes AI findings, chain-of-custody, or methodology sections,
    and carries the mandatory summary request notice.
    """
    db_path, case_id = populated_case_db
    pdf_out = str(tmp_path / "Summary_Report.pdf")

    report_builder.generate_case_report_pdf(db_path, case_id, pdf_out, mode="summary")
    assert os.path.exists(pdf_out)

    reader = PdfReader(pdf_out)
    full_text = "\n".join(p.extract_text() for p in reader.pages)
    norm_text = " ".join(full_text.split())

    # Present sections
    assert "EXECUTIVE SUMMARY FORENSIC REPORT" in norm_text
    assert "SECTION 2: EXECUTIVE SUMMARY" in norm_text
    assert "SECTION 3: CASE & PARTY DETAILS" in norm_text
    assert "SECTION 4: EVIDENCE INVENTORY" in norm_text
    assert "SECTION 5: ACQUISITION & INTEGRITY SUMMARY" in norm_text

    # Mandatory summary notice
    assert "Request the Full Technical Report for chain-of-custody, AI findings, and methodology detail" in norm_text

    # Omitted sections
    assert "SECTION 6: ISO/IEC 27037 ACTIVITY MAPPING" not in norm_text
    assert "SECTION 7: CHAIN OF CUSTODY AUDIT LOG" not in norm_text
    assert "SECTION 9: AI-ASSISTED TRIAGE FINDINGS" not in norm_text
    assert "SECTION 10: INVESTIGATOR FINDINGS" not in norm_text
    assert "SECTION 13: METHODOLOGY" not in norm_text


def test_report_self_integrity_hash(populated_case_db, tmp_path):
    """
    Confirms generated PDF's companion .sha256 file and logged audit event
    match an independent SHA-256 calculation of the file on disk.
    """
    db_path, case_id = populated_case_db
    pdf_out = str(tmp_path / "Integrity_Test.pdf")

    report_builder.generate_case_report_pdf(db_path, case_id, pdf_out, mode="full")

    # 1. Independent calculation
    hasher = hashlib.sha256()
    with open(pdf_out, "rb") as f:
        hasher.update(f.read())
    expected_hash = hasher.hexdigest()

    # 2. Companion file
    companion_path = f"{pdf_out}.sha256"
    assert os.path.exists(companion_path)
    with open(companion_path, "r", encoding="utf-8") as f:
        companion_content = f.read().strip()
    assert companion_content.startswith(expected_hash)

    # 3. Logged event in DB
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT details FROM audit_log WHERE event_type = 'REPORT_GENERATED'")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    details = json.loads(row["details"]) if isinstance(row["details"], str) else row["details"]
    assert details["sha256_hash"] == expected_hash


def test_legal_vocabulary_cleanliness(populated_case_db, tmp_path):
    """
    Greps full generated report text for forbidden positive claims:
    'admissible', 'certified', 'guarantee'.
    Must return zero hits outside the explicit statutory signature and disclaimer text.
    """
    db_path, case_id = populated_case_db
    pdf_out = str(tmp_path / "Vocab_Test.pdf")

    report_builder.generate_case_report_pdf(db_path, case_id, pdf_out, mode="full")
    reader = PdfReader(pdf_out)
    full_text = "\n".join(p.extract_text() for p in reader.pages)

    # Remove authorized disclaimer and signature phrases before scanning
    allowed_phrases = [
        "not self-certifying",
        "certification by the signing expert; this software does not self-certify",
        "does not self-certify compliance or admissibility",
        "does not self-certify",
    ]
    cleaned_text = full_text
    for phrase in allowed_phrases:
        cleaned_text = cleaned_text.replace(phrase, " ")

    cleaned_lower = cleaned_text.lower()

    # Zero hits for forbidden terms
    assert "admissible" not in cleaned_lower, "Found forbidden term 'admissible' in report text!"
    assert "certified" not in cleaned_lower, "Found forbidden term 'certified' in report text!"
    assert "guarantee" not in cleaned_lower, "Found forbidden term 'guarantee' in report text!"
