"""
Acceptance Test 2: Empty-State Coverage Test.
Asserts that every page (1 through 10) renders an explicit, honest Empty State
when its upstream step has not yet been executed, with no fake or placeholder data.
"""

import pytest
from PySide6.QtWidgets import QApplication

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
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


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_empty_state_coverage_all_pages(qapp):
    session = CaseSession()

    # --- Page 1: Intake ---
    p1 = Page1Intake(session)
    # Evidence path empty, acquire disabled
    assert p1.txt_file_path.text() == ""
    assert p1.btn_acquire.isEnabled() is False
    assert p1.session.write_block_verified is None
    assert "Case DB: Not yet created" in p1.lbl_case_status.text()
    assert "Write-block status not yet verified" in p1.wb_banner.text()

    # --- Page 2: Acquisition ---
    p2 = Page2Acquisition(session)
    assert not p2.empty_widget.isHidden()
    assert p2.content_widget.isHidden()
    assert "No Acquisition Run Yet" in p2.empty_widget.lbl_title.text()
    assert p2.val_md5.text() == ""
    assert p2.val_sha256.text() == ""

    # --- Page 3: OEM Detection ---
    p3 = Page3OemDetect(session)
    assert not p3.empty_widget.isHidden()
    assert p3.content_widget.isHidden()
    assert "No Evidence Available" in p3.empty_widget.lbl_title.text()

    # --- Page 4: Explorer ---
    p4 = Page4Explorer(session)
    assert not p4.empty_widget.isHidden()
    assert p4.content_widget.isHidden()
    assert "No Filesystem Parsed" in p4.empty_widget.lbl_title.text()

    # --- Page 5: Carver ---
    p5 = Page5Carver(session)
    assert not p5.empty_widget.isHidden()
    assert p5.content_widget.isHidden()
    assert ("No Evidence Loaded" in p5.empty_widget.lbl_title.text() or "No Carving Scan" in p5.empty_widget.lbl_title.text())
    assert p5.table.rowCount() == 0

    # --- Page 6: Playback ---
    p6 = Page6Playback(session)
    assert not p6.empty_widget.isHidden()
    assert p6.content_widget.isHidden()
    assert "No Video Clip Selected" in p6.empty_widget.lbl_title.text()

    # --- Page 7: Timeline ---
    p7 = Page7Timeline(session)
    assert not p7.empty_widget.isHidden()
    assert p7.content_widget.isHidden()
    assert "No Video Footage Selected" in p7.empty_widget.lbl_title.text()

    # --- Page 8: AI Analytics ---
    p8 = Page8AiTriage(session)
    # Each sub-tab must have 0 rows in un-triggered state
    assert p8.table_det.rowCount() == 0
    assert p8.table_faces.rowCount() == 0
    assert p8.table_reid.rowCount() == 0
    assert p8.table_anpr.rowCount() == 0
    assert p8.table_search.rowCount() == 0

    # --- Page 9: Audit Log ---
    p9 = Page9AuditLog(session)
    assert not p9.empty_widget.isHidden()
    assert p9.content_widget.isHidden()
    assert "No Active Case Database" in p9.empty_widget.lbl_title.text()

    # --- Page 10: Reporting ---
    p10 = Page10Reporting(session)
    assert not p10.empty_widget.isHidden()
    assert p10.content_widget.isHidden()
    assert "No Case Active for Reporting" in p10.empty_widget.lbl_title.text()
