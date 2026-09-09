"""Unit test for PySide6 MainWindow UI navigation and engine toolbar actions."""

import os
import pytest
from PySide6.QtWidgets import QApplication

from app.engine9_ui.main_window import MainWindow
from tests.fixtures.generate_synthetic_images import generate_hikvision_image


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_main_window_navigation_and_views(qapp):
    window = MainWindow()
    assert window.nav_list.count() == 6
    assert window.stack.count() == 6

    # Switch views via nav sidebar
    window.nav_list.setCurrentRow(1)
    assert window.stack.currentIndex() == 1

    window.nav_list.setCurrentRow(3)
    assert window.stack.currentIndex() == 3

    window.nav_list.setCurrentRow(4)
    assert window.stack.currentIndex() == 4


def test_main_window_synthetic_load(qapp, tmp_path):
    img_path = str(tmp_path / "hik_test.dd")
    generate_hikvision_image(img_path, size_bytes=5 * 1024 * 1024)

    window = MainWindow()
    window.load_image(img_path, case_id="CASE-UNIT-TEST")

    assert window.current_image_path == img_path
    assert window.current_vfs is not None
    assert window.current_vfs.oem == "Hikvision"
    assert len(window.current_vfs.files) == 3
