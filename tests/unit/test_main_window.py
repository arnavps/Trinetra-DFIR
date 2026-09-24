"""Unit test for PySide6 MainWindow UI navigation, 10-page workstation, and CaseSession integration."""

import os
import pytest
from PySide6.QtWidgets import QApplication

from app.engine9_ui.main_window import MainWindow
from tests.fixtures.generate_synthetic_images import generate_hikvision_image
from app.engine3_parsers.hikfat_parser import HikFatParser


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_main_window_navigation_and_views(qapp):
    window = MainWindow()
    assert window.nav_list.count() == 12
    assert window.stack.count() == 12

    # Initial empty state check
    assert window.session.has_case is False
    assert window.evidence_tree.topLevelItemCount() == 1
    assert "No case loaded" in window.evidence_tree.topLevelItem(0).text(0)

    # Switch views via nav sidebar
    window.nav_list.setCurrentRow(1)
    assert window.stack.currentIndex() == 1

    window.nav_list.setCurrentRow(3)
    assert window.stack.currentIndex() == 3

    window.go_to_page(5)
    assert window.stack.currentIndex() == 4

    window.go_to_page(8)
    assert window.stack.currentIndex() == 7


def test_main_window_real_case_integration(qapp, tmp_path):
    img_path = str(tmp_path / "hik_test.dd")
    generate_hikvision_image(img_path, size_bytes=5 * 1024 * 1024)

    window = MainWindow()
    case_db_path = str(tmp_path / "test_case.db")

    # Create real case in session
    window.session.create_case(
        case_id="CR-UNIT-2026",
        case_name="Integration Test Case",
        investigator="Agent Tester",
        db_path=case_db_path,
    )
    assert window.session.has_case is True
    assert window.session.case_id == "CR-UNIT-2026"

    # Set real evidence source
    window.session.set_evidence_source(img_path)

    # Parse real VFS
    parser = HikFatParser()
    vfs = parser.parse(img_path)
    window.session.set_vfs(vfs)

    # Assert tree updated with real channels
    assert window.session.virtual_file_system is not None
    assert window.session.virtual_file_system.oem == "Hikvision"
    assert len(window.session.virtual_file_system.files) == 3

    assert window.evidence_tree.topLevelItemCount() == 1
    root_item = window.evidence_tree.topLevelItem(0)
    assert "Case: CR-UNIT-2026" in root_item.text(0)


def test_bottom_proof_of_life_panel_resizability_and_tabs(qapp):
    from PySide6.QtCore import Qt

    window = MainWindow()
    window.resize(1400, 900)
    window.show()
    qapp.processEvents()

    assert hasattr(window, "content_v_splitter")
    assert window.content_v_splitter.orientation() == Qt.Orientation.Vertical
    assert window.content_v_splitter.count() == 2
    assert window.content_v_splitter.widget(0) is window.main_splitter
    assert window.content_v_splitter.widget(1) is window.jobs_panel

    # Check JobsPanel tabs and log table
    assert hasattr(window.jobs_panel, "tabs")
    assert window.jobs_panel.tabs.count() == 2
    assert "Jobs" in window.jobs_panel.tabs.tabText(0)
    assert "Proof-of-Life" in window.jobs_panel.tabs.tabText(1)
    assert hasattr(window.jobs_panel, "log_table")

    # Initially collapsed
    assert window.jobs_panel._is_expanded is False
    assert window.jobs_panel.queue_frame.isHidden()

    # Simulate event logged -> updates ticker and appends to proof-of-life stream
    window.session.log_engine_event("INTEGRITY_CHECK", "Verification hash matches SHA256")
    qapp.processEvents()
    assert "INTEGRITY_CHECK" in window.jobs_panel.lbl_ticker.text()
    assert window.jobs_panel.log_table.rowCount() == 1
    assert "INTEGRITY_CHECK" in window.jobs_panel.log_table.item(0, 1).text()
    assert "Verification hash matches" in window.jobs_panel.log_table.item(0, 2).text()

    # Toggle expand via button
    window.jobs_panel.btn_toggle.click()
    assert window.jobs_panel._is_expanded is True
    assert not window.jobs_panel.queue_frame.isHidden()

    # Toggle collapse via button
    window.jobs_panel.btn_toggle.click()
    assert window.jobs_panel._is_expanded is False
    assert window.jobs_panel.queue_frame.isHidden()

    # Moving splitter up expands the panel automatically
    window.content_v_splitter.setSizes([600, 250])
    window._on_content_splitter_moved(600, 1)
    assert window.jobs_panel._is_expanded is True
    assert not window.jobs_panel.queue_frame.isHidden()

    # Clear log button
    window.jobs_panel.btn_clear_log.click()
    assert window.jobs_panel.log_table.rowCount() == 0

    window.close()


def test_jobs_panel_expansion_on_laptop_screen_resolutions(qapp):
    window = MainWindow()
    # Test typical laptop / constrained height (700px)
    window.resize(1280, 700)
    window.show()
    qapp.processEvents()

    # Expand via toggle button
    window.jobs_panel.btn_toggle.click()
    qapp.processEvents()

    # Must expand to readable workstation height (>= 180px), never squished to 64px sliver
    assert window.jobs_panel._is_expanded is True
    assert window.jobs_panel.height() >= 180
    assert window.jobs_panel.log_table.height() >= 80

    # User can drag splitter higher (e.g. 320px)
    window.content_v_splitter.setSizes([window.content_v_splitter.height() - 320, 320])
    window._on_content_splitter_moved(window.content_v_splitter.height() - 320, 1)
    qapp.processEvents()
    assert window.jobs_panel.height() >= 300

    # Toggle collapse
    window.jobs_panel.btn_toggle.click()
    qapp.processEvents()
    assert window.jobs_panel._is_expanded is False
    assert window.jobs_panel.height() <= 50

    window.close()

