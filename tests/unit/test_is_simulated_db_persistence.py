import sqlite3
import tempfile
import os
import pytest
from app.engine7_case_db.db import init_db
from app.engine9_ui.views.search_panel import query_annotations


def test_is_simulated_db_persistence_and_query():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_case.db")
        init_db(db_path)

        conn = sqlite3.connect(db_path)
        with conn:
            conn.execute(
                "INSERT INTO cases (case_id, name, created_at) VALUES ('TEST-CASE-01', 'Test Case', '2026-09-12 12:00:00');"
            )
            conn.execute(
                """
                INSERT INTO extracted_files (file_id, case_id, channel_id, start_timestamp, end_timestamp, size_bytes, file_hash, extraction_type)
                VALUES ('FILE_01', 'TEST-CASE-01', 1, '2026-09-12 12:00:00', '2026-09-12 12:10:00', 1024, 'hash1', 'ALLOCATED');
                """
            )
            # Insert real detection (is_simulated=0) and simulated detection (is_simulated=1)
            conn.execute(
                """
                INSERT INTO detections (detection_id, file_id, timestamp, frame_index, class_name, confidence, bbox_json, is_simulated)
                VALUES 
                ('DET-REAL', 'FILE_01', '2026-09-12 12:01:00', 10, 'person', 0.95, '[10, 10, 50, 50]', 0),
                ('DET-SIM',  'FILE_01', '2026-09-12 12:02:00', 20, 'car', 0.88, '[20, 20, 60, 60]', 1);
                """
            )
            # Insert real face (is_simulated=0) and simulated face (is_simulated=1)
            conn.execute(
                """
                INSERT INTO face_detections (face_id, file_id, timestamp, frame_index, confidence, bbox_json, landmarks_json, is_simulated)
                VALUES 
                ('FACE-REAL', 'FILE_01', '2026-09-12 12:03:00', 30, 0.92, '[5, 5, 25, 25]', '[]', 0),
                ('FACE-SIM',  'FILE_01', '2026-09-12 12:04:00', 40, 0.85, '[15, 15, 35, 35]', '[]', 1);
                """
            )
        conn.close()

        results = query_annotations(db_path, class_filter="all")
        by_id = {r["id"]: r for r in results}

        assert "DET-REAL" in by_id
        assert "DET-SIM" in by_id
        assert "FACE-REAL" in by_id
        assert "FACE-SIM" in by_id

        # Crucial: verify that the real detection has is_simulated=False, and simulated has is_simulated=True
        assert by_id["DET-REAL"]["is_simulated"] is False
        assert by_id["DET-SIM"]["is_simulated"] is True

        assert by_id["FACE-REAL"]["is_simulated"] is False
        assert by_id["FACE-SIM"]["is_simulated"] is True
