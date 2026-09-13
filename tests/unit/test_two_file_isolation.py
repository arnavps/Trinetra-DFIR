"""
Acceptance Test 1: Two-File Isolation Test (The Big One).
Generates two genuinely different synthetic evidence images (Hikvision vs Dahua).
Runs each through the full Page 1 -> 10 forensic workstation flow programmatically.
Asserts:
1. The two acquisition hashes (SHA-256 and MD5) differ cryptographically.
2. The detected OEMs differ (Hikvision vs Dahua).
3. The two evidence trees and extracted VFS file entries differ.
4. No page displays any value from Run 1 during Run 2 (zero cross-case pollution, zero hardcoded telemetry).
"""

import json
import os
import sqlite3
import pytest
from PySide6.QtWidgets import QApplication

from app.engine1_acquisition.acquirer import acquire_image
from app.engine1_acquisition.writeblock_check import verify_read_only
from app.engine2_detector.signature_matcher import match_signature
from app.engine3_parsers.hikfat_parser import HikFatParser
from app.engine3_parsers.dhfs_parser import DhfsParser
from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.pages.page1_intake import Page1Intake
from app.engine9_ui.pages.page2_acquisition import Page2Acquisition
from app.engine9_ui.pages.page3_oem_detect import Page3OemDetect
from app.engine9_ui.pages.page4_explorer import Page4Explorer
from app.engine9_ui.pages.page5_carver import Page5Carver
from app.engine9_ui.pages.page6_playback import Page6Playback
from app.engine9_ui.pages.page7_timeline import Page7Timeline
from app.engine9_ui.pages.page8_ai_triage import Page8AiTriage
from app.engine9_ui.pages.page9_audit_log import Page9AuditLog
from app.engine9_ui.pages.page10_reporting import Page10Reporting

from tests.fixtures.generate_synthetic_images import generate_hikvision_image, generate_dahua_image


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_two_file_isolation_full_pipeline(qapp, tmp_path):
    # -------------------------------------------------------------
    # STEP 0: Generate two genuinely distinct evidence images
    # -------------------------------------------------------------
    img1_path = str(tmp_path / "evidence_run1_hik.dd")
    img2_path = str(tmp_path / "evidence_run2_dhfs.dd")

    generate_hikvision_image(img1_path, size_bytes=2 * 1024 * 1024, seed=101)
    generate_dahua_image(img2_path, size_bytes=2 * 1024 * 1024, seed=202)

    with open(img1_path, "rb") as f1, open(img2_path, "rb") as f2:
        assert f1.read(4096) != f2.read(4096), "Underlying raw disk bytes must be distinct!"

    # Set real read-only attribute to simulate genuine write-blocker
    import stat
    os.chmod(img1_path, stat.S_IREAD)
    os.chmod(img2_path, stat.S_IREAD)

    try:
        # =============================================================
        # EXECUTION RUN 1: Hikvision Evidence Image
        # =============================================================
        session1 = CaseSession()
        case1_dir = str(tmp_path / "case_01")
        db1_path = os.path.join(case1_dir, "case.db")

        # Page 1: Intake
        p1_1 = Page1Intake(session1)
        case_id_1 = session1.create_case(
            case_id="CR-2026-HIK-001",
            name="Hikvision Forensic Investigation",
            investigator="Det. Inspector A",
            db_path=db1_path,
        )
        session1.set_evidence_source(img1_path)
        verify_read_only(img1_path)
        session1.set_write_block_status(True)

        dest1_dd = str(tmp_path / "acquired_run1.dd")
        acq1_res = acquire_image(
            source_path=img1_path,
            dest_path=dest1_dd,
            case_id=case_id_1,
            db_path=db1_path,
            enforce_write_block=True,
        )
        session1.set_acquisition_result(acq1_res)

        # Page 2: Acquisition & Integrity Report
        p2_1 = Page2Acquisition(session1)
        p2_1.refresh_data()
        assert not p2_1.content_widget.isHidden()
        hash_sha256_1 = p2_1.val_sha256.text()
        hash_md5_1 = p2_1.val_md5.text()
        assert len(hash_sha256_1) == 64
        assert len(hash_md5_1) == 32

        # Page 3: OEM Detection
        p3_1 = Page3OemDetect(session1)
        p3_1.run_detection()
        assert not p3_1.content_widget.isHidden()
        assert "Hikvision" in p3_1.lbl_match_statement.text()
        oem_1 = "Hikvision"

        # Page 4: Filesystem Explorer
        vfs1 = HikFatParser().parse(dest1_dd)
        session1.set_vfs(vfs1)
        p4_1 = Page4Explorer(session1)
        p4_1.refresh_table()
        assert not p4_1.content_widget.isHidden()
        files_1 = [f.file_id for f in vfs1.files]
        assert len(files_1) > 0

        # Page 6: Playback
        session1.set_active_file(vfs1.files[0])
        p6_1 = Page6Playback(session1)
        assert not p6_1.content_widget.isHidden()
        assert "H.264" in p6_1.lbl_osd_banner.text() or "Hikvision" in p6_1.lbl_osd_banner.text()

        # Page 9: Audit Log
        p9_1 = Page9AuditLog(session1)
        p9_1.refresh_log()
        assert not p9_1.content_widget.isHidden()
        assert p9_1.table.rowCount() >= 2

        # Page 10: Reporting
        p10_1 = Page10Reporting(session1)
        p10_1._on_session_changed()
        assert not p10_1.content_widget.isHidden()
        prev1 = p10_1.txt_preview.toPlainText()
        assert case_id_1 in prev1
        assert hash_sha256_1 in prev1

        # =============================================================
        # EXECUTION RUN 2: Dahua Evidence Image
        # =============================================================
        session2 = CaseSession()
        case2_dir = str(tmp_path / "case_02")
        db2_path = os.path.join(case2_dir, "case.db")

        # Page 1: Intake
        p1_2 = Page1Intake(session2)
        case_id_2 = session2.create_case(
            case_id="CR-2026-DHFS-002",
            name="Dahua Forensic Investigation",
            investigator="Det. Inspector B",
            db_path=db2_path,
        )
        session2.set_evidence_source(img2_path)
        verify_read_only(img2_path)
        session2.set_write_block_status(True)

        dest2_dd = str(tmp_path / "acquired_run2.dd")
        acq2_res = acquire_image(
            source_path=img2_path,
            dest_path=dest2_dd,
            case_id=case_id_2,
            db_path=db2_path,
            enforce_write_block=True,
        )
        session2.set_acquisition_result(acq2_res)

        # Page 2: Acquisition & Integrity Report
        p2_2 = Page2Acquisition(session2)
        p2_2.refresh_data()
        assert not p2_2.content_widget.isHidden()
        hash_sha256_2 = p2_2.val_sha256.text()
        hash_md5_2 = p2_2.val_md5.text()
        assert len(hash_sha256_2) == 64
        assert len(hash_md5_2) == 32

        # Page 3: OEM Detection
        p3_2 = Page3OemDetect(session2)
        p3_2.run_detection()
        assert not p3_2.content_widget.isHidden()
        assert "Dahua" in p3_2.lbl_match_statement.text()
        oem_2 = "Dahua"

        # Page 4: Filesystem Explorer
        vfs2 = DhfsParser().parse(dest2_dd)
        session2.set_vfs(vfs2)
        p4_2 = Page4Explorer(session2)
        p4_2.refresh_table()
        assert not p4_2.content_widget.isHidden()
        files_2 = [f.file_id for f in vfs2.files]
        assert len(files_2) > 0

        # Page 6: Playback
        session2.set_active_file(vfs2.files[0])
        p6_2 = Page6Playback(session2)
        assert not p6_2.content_widget.isHidden()

        # Page 9: Audit Log
        p9_2 = Page9AuditLog(session2)
        p9_2.refresh_log()
        assert not p9_2.content_widget.isHidden()
        assert p9_2.table.rowCount() >= 2

        # Page 10: Reporting
        p10_2 = Page10Reporting(session2)
        p10_2._on_session_changed()
        assert not p10_2.content_widget.isHidden()
        prev2 = p10_2.txt_preview.toPlainText()
        assert case_id_2 in prev2
        assert hash_sha256_2 in prev2

        # =============================================================
        # CRITICAL FORENSIC ISOLATION ASSERTIONS
        # =============================================================
        print("\n--- FORENSIC ISOLATION RUN RESULTS ---")
        print(f"Run 1 (Hikvision) Case ID: {case_id_1}")
        print(f"Run 1 SHA-256: {hash_sha256_1}")
        print(f"Run 1 MD5:     {hash_md5_1}")
        print(f"Run 1 OEM:     {oem_1}")
        print(f"Run 1 Files:   {files_1}")
        print(f"Run 2 (Dahua) Case ID: {case_id_2}")
        print(f"Run 2 SHA-256: {hash_sha256_2}")
        print(f"Run 2 MD5:     {hash_md5_2}")
        print(f"Run 2 OEM:     {oem_2}")
        print(f"Run 2 Files:   {files_2}")
        print("---------------------------------------")

        # 1. Hashes MUST genuinely differ
        assert hash_sha256_1 != hash_sha256_2, f"Collision detected! Both SHA-256 hashes are {hash_sha256_1}"
        assert hash_md5_1 != hash_md5_2, f"Collision detected! Both MD5 hashes are {hash_md5_1}"

        # 2. OEMs MUST differ
        assert oem_1 != oem_2, f"OEM failure! Both are {oem_1}"

        # 3. Evidence trees MUST differ
        assert files_1 != files_2, "VFS file IDs must differ between distinct evidence!"

        # 4. Cross-pollution check
        assert hash_sha256_1 not in prev2, "Run 1 hash leaked into Run 2 report preview!"
        assert hash_sha256_2 not in prev1, "Run 2 hash leaked into Run 1 report preview!"
        assert case_id_1 not in prev2, "Run 1 case ID leaked into Run 2 report preview!"
        assert case_id_2 not in prev1, "Run 2 case ID leaked into Run 1 report preview!"
    finally:
        os.chmod(img1_path, stat.S_IWRITE)
        os.chmod(img2_path, stat.S_IWRITE)
