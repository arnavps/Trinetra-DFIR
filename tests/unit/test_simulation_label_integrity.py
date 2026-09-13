"""
Acceptance Test 3: Simulation-Label Integrity Test.
Directly inserts one real-flagged (is_simulated=0) and one simulated-flagged (is_simulated=1)
detection record into the case DB, loads Page 8 (AI Analytics & Triage), and asserts:
1. The two records render with visibly different, correctly-mapped verification chips.
2. The real-flagged record renders with 'VERIFIED' and emerald/green styling.
3. The simulated-flagged record renders with 'SIMULATED' and amber/yellow styling.
"""

import json
import sqlite3
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.engine7_case_db import db
from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.pages.page8_ai_triage import Page8AiTriage


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_simulation_label_integrity_page8(qapp, tmp_path):
    # 1. Initialize test database
    db_file = str(tmp_path / "sim_label_test.db")
    db.init_db(db_file)

    # 2. Insert case, file, and two detections (1 real, 1 simulated) directly
    conn = sqlite3.connect(db_file)
    with conn:
        conn.execute(
            "INSERT INTO cases (case_id, name, created_at) VALUES ('CASE-SIM-TEST', 'Sim Integrity Case', '2026-09-13T10:00:00');"
        )
        conn.execute(
            """INSERT INTO extracted_files 
               (file_id, case_id, channel_id, start_timestamp, end_timestamp, size_bytes, file_hash, extraction_type)
               VALUES ('CLIP_TEST_01', 'CASE-SIM-TEST', 1, '2026-09-13T10:00:00', '2026-09-13T10:05:00', 1048576, 'hash_test_123', 'parsed');"""
        )

        # Record 1: REAL (is_simulated = 0)
        conn.execute(
            """INSERT INTO detections 
               (detection_id, file_id, timestamp, frame_index, class_name, confidence, bbox_json, is_simulated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            ("DET-001-REAL", "CLIP_TEST_01", "2026-09-13T10:01:00", 12, "person", 0.96, json.dumps([50, 40, 180, 280]), 0)
        )

        # Record 2: SIMULATED (is_simulated = 1)
        conn.execute(
            """INSERT INTO detections 
               (detection_id, file_id, timestamp, frame_index, class_name, confidence, bbox_json, is_simulated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            ("DET-002-SIM", "CLIP_TEST_01", "2026-09-13T10:02:00", 45, "car", 0.82, json.dumps([200, 100, 450, 320]), 1)
        )
    conn.close()

    # 3. Create CaseSession pointing to the test case
    session = CaseSession()
    session.create_case(case_id="CASE-SIM-TEST", name="Sim Integrity Case", db_path=db_file)

    # 4. Instantiate Page 8 and load detections from DB
    page8 = Page8AiTriage(session)
    page8.load_from_db(db_file)

    # 5. Assert two rows loaded into Detection table
    assert page8.table_det.rowCount() == 2

    # Row 0: Real Detection
    row0_class = page8.table_det.item(0, 1).text()
    row0_chip = page8.table_det.item(0, 4)
    assert row0_class == "person"
    assert "VERIFIED" in row0_chip.text()
    assert "SIMULATED" not in row0_chip.text()
    assert row0_chip.foreground().color() == Qt.GlobalColor.green

    # Row 1: Simulated Detection
    row1_class = page8.table_det.item(1, 1).text()
    row1_chip = page8.table_det.item(1, 4)
    assert row1_class == "car"
    assert "SIMULATED" in row1_chip.text()
    assert "VERIFIED" not in row1_chip.text()
    assert row1_chip.foreground().color() == Qt.GlobalColor.yellow

    # 6. Verify visible distinction survives: chip text and colors differ
    assert row0_chip.text() != row1_chip.text()
    assert row0_chip.foreground().color() != row1_chip.foreground().color()
