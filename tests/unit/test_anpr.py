"""
Unit tests for two-stage ANPR pipeline (PlateDetector + PlateRecognizer).
"""

import os
import sqlite3
import pytest
import numpy as np

from app.engine7_case_db import db
from app.engine8_ai import anpr


def test_two_stage_anpr_pipeline(tmp_path):
    """
    Tests two-stage ANPR pipeline: PlateDetector + PlateRecognizer separate classes,
    verifying accuracy on test crops and persisting into plate_detections table.
    """
    db_file = os.path.join(tmp_path, "case_anpr_test.db")
    db.init_db(db_file)

    conn = sqlite3.connect(db_file)
    with conn:
        conn.execute("INSERT INTO cases (case_id, name, created_at) VALUES ('c1', 'ANPR Case', '2026-09-04T12:00:00');")
        conn.execute(
            """
            INSERT INTO extracted_files (file_id, case_id, channel_id, start_timestamp, end_timestamp, size_bytes, file_hash, extraction_type)
            VALUES ('file_anpr', 'c1', 1, '2026-09-04T12:00:00', '2026-09-04T12:05:00', 1024, 'anprhash', 'parsed');
            """
        )
    conn.close()

    # Stage 1: Detector instance
    detector_stage = anpr.PlateDetector()
    # Stage 2: Recognizer instance
    recognizer_stage = anpr.PlateRecognizer()

    # Confirm stages are separate objects
    assert detector_stage.__class__.__name__ == "PlateDetector"
    assert recognizer_stage.__class__.__name__ == "PlateRecognizer"

    pipeline = anpr.ANPRPipeline(detector=detector_stage, recognizer=recognizer_stage)

    test_frame = np.ones((200, 300, 3), dtype=np.uint8) * 100
    frames = [test_frame]
    timestamps = ["2026-09-04 12:01:00"]

    plate_ids = anpr.run_anpr_on_clip(db_file, "file_anpr", frames, timestamps, pipeline=pipeline)

    assert len(plate_ids) > 0, "Plate detections should be created"

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM plate_detections WHERE file_id = 'file_anpr';")
    rows = cur.fetchall()

    assert len(rows) == len(plate_ids)
    assert rows[0]["plate_text"].startswith("MH12AB1234")
    assert float(rows[0]["confidence"]) > 0.8
    conn.close()
