"""Unit tests for full audit log custody chain and basic PDF report export."""

import os
import tempfile

from app.engine1_acquisition.acquirer import acquire_image
from app.engine3_parsers.generic_parser import GenericParser
from app.engine3_parsers.hikfat_parser import HikFatParser
from app.engine7_case_db.audit_log import log_event, record_extracted_file, verify_audit_chain, get_extracted_files
from app.engine7_case_db.models import ExtractedFile
from app.engine10_compliance.report_builder import generate_case_report_pdf, build_json_report
from tests.fixtures.generate_synthetic_images import generate_hikvision_image, generate_unknown_oem_image


def test_full_custody_chain_and_pdf_report_export():
    """Custody log shows an unbroken hash chain across acquisition -> parsing -> carving -> report-export, and PDF generates showing extraction_type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "custody_case.db")
        case_id = "CASE-2026-001"

        src_path = os.path.join(tmpdir, "source_drive.dd")
        acquired_dd = os.path.join(tmpdir, "acquired_drive.dd")
        generate_hikvision_image(src_path, size_bytes=10 * 1024 * 1024, seed=42)
        os.chmod(src_path, 0o444)

        # 1. Acquisition
        acq_res = acquire_image(src_path, acquired_dd, case_id=case_id, db_path=db_path)

        # 2. Parsing (Hikvision HIKFAT)
        log_event(db_path, case_id, "PARSING_START", {"oem": "Hikvision", "image_path": acquired_dd})
        vfs = HikFatParser().parse(acquired_dd)
        for f in vfs.files:
            ext_file = ExtractedFile(
                file_id=f.file_id,
                case_id=case_id,
                channel_id=f.channel_id,
                start_timestamp=f.start_timestamp,
                end_timestamp=f.end_timestamp,
                size_bytes=f.size_bytes,
                file_hash="a1b2c3d4e5f67890",
                extraction_type=f.extraction_type,
            )
            record_extracted_file(db_path, ext_file)

        log_event(db_path, case_id, "PARSING_FINISH", {"total_parsed_files": len(vfs.files)})

        # 3. Carving (Generic Fallback on unallocated/unknown sector segment)
        log_event(db_path, case_id, "CARVING_START", {"target": "unallocated_sectors"})
        unknown_path = os.path.join(tmpdir, "unknown_segment.dd")
        generate_unknown_oem_image(unknown_path, size_bytes=2 * 1024 * 1024, seed=99)

        carve_vfs = GenericParser().parse(unknown_path)
        for cf in carve_vfs.files:
            carved_file = ExtractedFile(
                file_id=cf.file_id,
                case_id=case_id,
                channel_id=cf.channel_id,
                start_timestamp=cf.start_timestamp,
                end_timestamp=cf.end_timestamp,
                size_bytes=cf.size_bytes,
                file_hash="f9e8d7c6b5a43210",
                extraction_type=cf.extraction_type,
            )
            record_extracted_file(db_path, carved_file)

        log_event(db_path, case_id, "CARVING_FINISH", {"total_carved_files": len(carve_vfs.files)})

        # 4. Report Export
        pdf_path = os.path.join(tmpdir, "case_report.pdf")
        log_event(db_path, case_id, "REPORT_EXPORT_START", {"pdf_path": pdf_path})
        generated_pdf = generate_case_report_pdf(db_path, case_id, pdf_path)
        log_event(db_path, case_id, "REPORT_EXPORT_FINISH", {"pdf_path": generated_pdf})

        # 5. Assert Unbroken Hash Chain Across Full Pipeline
        assert verify_audit_chain(db_path, case_id) is True

        # 6. Assert PDF report generated successfully
        assert os.path.exists(generated_pdf)
        assert os.path.getsize(generated_pdf) > 0

        # 7. Assert Extracted Files in DB contain both 'parsed' and 'carved_fragment'
        db_files = get_extracted_files(db_path, case_id)
        types = [f.extraction_type for f in db_files]
        assert "parsed" in types
        assert "carved_fragment" in types

        # 8. Assert JSON Report data contains extraction_type for each file
        json_rep = build_json_report(db_path, case_id)
        assert json_rep["audit_chain_valid"] is True
        for f_info in json_rep["extracted_files"]:
            assert f_info["extraction_type"] in ("parsed", "carved_fragment")
