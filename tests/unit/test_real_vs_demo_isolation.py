import os
import sqlite3
import pytest
from PySide6.QtWidgets import QApplication

from app.engine9_ui.main_window import MainWindow
from tests.fixtures.generate_synthetic_images import generate_hikvision_image, generate_dahua_image


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_real_evidence_isolation_and_no_demo_in_main_window(qapp, tmp_path):
    """
    Master Prompt 3 Verification:
    Verifies that MainWindow:
    1. Starts with NO demo case, NO hardcoded fake data, and session.has_case is False.
    2. Contains no synthetic demo buttons in the UI.
    3. Creating and loading real evidence creates genuine distinct cases and hashes.
    4. Real DB contains 0 pre-seeded triage detections.
    """
    window = MainWindow()
    window.show()

    # 1. Check initial state: No case loaded, empty state across the workstation
    assert window.session.has_case is False
    assert window.session.has_evidence is False
    assert "NO CASE LOADED" in window.top_ribbon.lbl_case.text().upper()

    # Verify no demo item exists in the sidebar navigation or window
    assert window.nav_list.count() == 10
    for i in range(window.nav_list.count()):
        item_text = window.nav_list.item(i).text()
        assert "Demo" not in item_text
        assert "Synthetic" not in item_text

    # Verify evidence tree displays honest empty state before case
    assert window.evidence_tree.topLevelItemCount() == 1
    root_item = window.evidence_tree.topLevelItem(0)
    assert "No case loaded" in root_item.text(0)

    # 2. Test Case Creation and Evidence Intake via Session
    img1_path = str(tmp_path / "evidence1.dd")
    generate_hikvision_image(img1_path, size_bytes=2 * 1024 * 1024, seed=101)

    case_dir1 = str(tmp_path / "case_intake_01")
    db_path1 = os.path.join(case_dir1, "case.db")

    case_id_1 = window.session.create_case("CASE-2026-INTAKE-01", "Real Case 1", "Investigator Alpha", db_path=db_path1)
    assert window.session.has_case is True
    assert "CASE-2026-INTAKE-01" in window.top_ribbon.lbl_case.text()

    # 3. Assert DB starts with exactly 0 detections (no mock data seeded)
    conn = sqlite3.connect(db_path1)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM detections;")
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT count(*) FROM face_detections;")
    assert cur.fetchone()[0] == 0
    conn.close()
