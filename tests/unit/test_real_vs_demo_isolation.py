import os
import sqlite3
import tempfile
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


def test_real_vs_demo_complete_isolation(qapp, tmp_path):
    """
    P0 Regression Guard:
    Verifies that load_real_evidence() NEVER seeds demo or mock data,
    computes genuine distinct hashes for distinct files, updates UI telemetry
    with real values, and visibly isolates real evidence from demo cases.
    """
    # 1. Create two genuinely distinct synthetic .dd forensic images
    img1_path = str(tmp_path / "evidence_hikvision.dd")
    img2_path = str(tmp_path / "evidence_dahua.dd")

    generate_hikvision_image(img1_path, size_bytes=2 * 1024 * 1024, seed=101)
    generate_dahua_image(img2_path, size_bytes=2 * 1024 * 1024, seed=202)

    # Verify underlying bytes actually differ
    with open(img1_path, "rb") as f1, open(img2_path, "rb") as f2:
        assert f1.read(4096) != f2.read(4096)

    window = MainWindow()
    window.show()

    # 2. Check initial state (loads synthetic demo on startup)
    assert window.is_demo_case is True
    assert window.current_case_id.startswith("DEMO-")
    assert "[DEMO / SYNTHETIC DATA]" in window.windowTitle()
    assert not window.status_ribbon.badge_demo.isHidden()
    assert not window.view_dashboard.demo_badge.isHidden()

    # Confirm demo DB contains the fixed demo dataset (DET-001, REID-001, FACE-001)
    demo_conn = sqlite3.connect(window.current_db_path)
    cur = demo_conn.cursor()
    cur.execute("SELECT detection_id FROM detections;")
    demo_det_ids = [r[0] for r in cur.fetchall()]
    assert "DET-001" in demo_det_ids
    demo_conn.close()

    demo_hash = "7f83b1657b98f2b3a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a9c8"

    # 3. Load Real Evidence 1 (Hikvision)
    window.load_real_evidence(img1_path)

    assert window.is_demo_case is False
    assert not window.current_case_id.startswith("DEMO-")
    assert "[DEMO / SYNTHETIC DATA]" not in window.windowTitle()
    assert window.status_ribbon.badge_demo.isHidden()
    assert window.view_dashboard.demo_badge.isHidden()
    assert window.current_vfs.oem == "Hikvision"

    # Retrieve real computed hash from DB audit log
    conn1 = sqlite3.connect(window.current_db_path)
    cur1 = conn1.cursor()
    cur1.execute("SELECT details FROM audit_log WHERE event_type = 'HASH_VERIFY';")
    import json
    hash_details1 = json.loads(cur1.fetchone()[0])
    hash1 = hash_details1["sha256"]

    # Assert real DB starts empty of any pre-seeded triage detections
    cur1.execute("SELECT detection_id FROM detections;")
    real_dets_1 = [r[0] for r in cur1.fetchall()]
    assert len(real_dets_1) == 0
    assert "DET-001" not in real_dets_1

    cur1.execute("SELECT face_id FROM face_detections;")
    assert len(cur1.fetchall()) == 0

    cur1.execute("SELECT reid_id FROM person_reid_embeddings;")
    assert len(cur1.fetchall()) == 0
    conn1.close()

    # 4. Load Real Evidence 2 (Dahua)
    window.load_real_evidence(img2_path)

    assert window.is_demo_case is False
    assert not window.current_case_id.startswith("DEMO-")
    assert "[DEMO / SYNTHETIC DATA]" not in window.windowTitle()
    assert window.status_ribbon.badge_demo.isHidden()
    assert window.view_dashboard.demo_badge.isHidden()
    assert window.current_vfs.oem == "Dahua"

    conn2 = sqlite3.connect(window.current_db_path)
    cur2 = conn2.cursor()
    cur2.execute("SELECT details FROM audit_log WHERE event_type = 'HASH_VERIFY';")
    hash_details2 = json.loads(cur2.fetchone()[0])
    hash2 = hash_details2["sha256"]

    cur2.execute("SELECT detection_id FROM detections;")
    real_dets_2 = [r[0] for r in cur2.fetchall()]
    assert len(real_dets_2) == 0
    assert "DET-001" not in real_dets_2
    conn2.close()

    # 5. Core Litmus Invariant: Hashes must differ from each other and from the demo hash
    assert hash1 != hash2, f"Expected distinct hashes for distinct files, got {hash1}"
    assert hash1 != demo_hash, f"Hash 1 collided with fixed demo literal {demo_hash}"
    assert hash2 != demo_hash, f"Hash 2 collided with fixed demo literal {demo_hash}"

    # 6. Re-load synthetic demo and verify that demo badges and DEMO- prefix reappear
    window.load_synthetic_demo_case()
    assert window.is_demo_case is True
    assert window.current_case_id.startswith("DEMO-")
    assert "[DEMO / SYNTHETIC DATA]" in window.windowTitle()
    assert not window.status_ribbon.badge_demo.isHidden()
    assert not window.view_dashboard.demo_badge.isHidden()

    demo_conn2 = sqlite3.connect(window.current_db_path)
    cur2 = demo_conn2.cursor()
    cur2.execute("SELECT detection_id FROM detections;")
    demo_dets_reloaded = [r[0] for r in cur2.fetchall()]
    assert "DET-001" in demo_dets_reloaded
    demo_conn2.close()
