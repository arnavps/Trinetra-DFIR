"""
Unit tests for SCRFD face detection, Person Re-ID, and search filter query functionality.
Note: Test frames use synthetic numpy arrays for offline CPU-only testing.
"""

import json
import os
import sqlite3
import pytest
import numpy as np

from app.engine7_case_db import db, models
from app.engine8_ai import face, reid_person, detector
from app.engine9_ui.views import search_panel


def test_face_detection_and_reid_pipeline(tmp_path):
    """
    Tests face detection, Person Re-ID embedding generation, mandatory INVESTIGATIVE_LEAD_LABEL,
    and annotation search query filtering.
    """
    db_file = os.path.join(tmp_path, "case_face_test.db")
    db.init_db(db_file)

    # Insert case and extracted file
    conn = sqlite3.connect(db_file)
    with conn:
        conn.execute(
            "INSERT INTO cases (case_id, name, created_at) VALUES ('c1', 'Face Case', '2026-09-04T10:00:00');"
        )
        conn.execute(
            """
            INSERT INTO extracted_files (file_id, case_id, channel_id, start_timestamp, end_timestamp, size_bytes, file_hash, extraction_type)
            VALUES ('file1', 'c1', 2, '2026-09-04T10:00:00', '2026-09-04T10:05:00', 2048, 'facehash123', 'parsed');
            """
        )
    conn.close()

    # Synthetic frames
    frames = [np.ones((120, 160, 3), dtype=np.uint8) * 200]
    timestamps = ["2026-09-04T10:01:00"]

    # 1. Object Detections (Person & Car)
    det_engine = detector.YOLOv8Detector()
    detector.run_detection_on_clip(db_file, "file1", frames, timestamps, detector=det_engine)

    # 2. Face Detections
    face_engine = face.SCRFDFaceDetector()
    face_ids = face.run_face_detection_on_clip(db_file, "file1", frames, timestamps, detector=face_engine)
    assert len(face_ids) > 0, "Face detection should produce face records"

    # 3. Person Re-ID
    reid_engine = reid_person.PersonReID()
    reid_ids = reid_person.run_reid_on_detections(db_file, "file1", frames=frames, reid_engine=reid_engine)
    assert len(reid_ids) > 0, "Re-ID should generate embedding records for person detections"

    # Verify Re-ID label invariant in DB
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM person_reid_embeddings WHERE file_id = 'file1';")
    reid_rows = cur.fetchall()
    assert len(reid_rows) == len(reid_ids)
    for r_row in reid_rows:
        assert models.INVESTIGATIVE_LEAD_LABEL in r_row["label"], (
            f"Expected label containing '{models.INVESTIGATIVE_LEAD_LABEL}', got '{r_row['label']}'"
        )
    conn.close()

    # 4. Search Filter UI Query Verification
    # Search by class='Person'
    person_results = search_panel.query_annotations(db_file, class_filter="Person")
    assert len(person_results) > 0
    assert all(r["class_name"] == "person" for r in person_results)

    # Search by class='Face'
    face_results = search_panel.query_annotations(db_file, class_filter="Face")
    assert len(face_results) > 0
    assert all(r["class_name"] == "face" for r in face_results)

    # Search by Channel ID = 2
    ch2_results = search_panel.query_annotations(db_file, channel_filter=2)
    assert len(ch2_results) > 0
    assert all(r["channel_id"] == 2 for r in ch2_results)

    # Search by Channel ID = 99 (should yield empty)
    ch99_results = search_panel.query_annotations(db_file, channel_filter=99)
    assert len(ch99_results) == 0
