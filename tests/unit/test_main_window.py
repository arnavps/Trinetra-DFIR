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
    assert window.nav_list.count() == 10
    assert window.stack.count() == 10

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
