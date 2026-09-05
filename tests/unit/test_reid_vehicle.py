"""
Unit tests for FastReID Vehicle Re-ID (VeRi-776) and mandatory INVESTIGATIVE_LEAD_LABEL tagging.
"""

import os
import sqlite3
import pytest
import numpy as np

from app.engine7_case_db import db, models
from app.engine8_ai import detector, reid_vehicle
from app.engine9_ui.views import suspect_journey_view


def test_vehicle_reid_pipeline_and_journey_cross_reference(tmp_path):
    """
    Tests Vehicle Re-ID embedding persistence with mandatory INVESTIGATIVE_LEAD_LABEL
    and cross-camera journey matching between two channels.
    """
    db_file = os.path.join(tmp_path, "case_v_reid_test.db")
    db.init_db(db_file)

    conn = sqlite3.connect(db_file)
    with conn:
        conn.execute("INSERT INTO cases (case_id, name, created_at) VALUES ('c1', 'VeRi Case', '2026-09-04T12:00:00');")
        conn.execute(
            """
            INSERT INTO extracted_files (file_id, case_id, channel_id, start_timestamp, end_timestamp, size_bytes, file_hash, extraction_type)
            VALUES ('file_ch1', 'c1', 1, '2026-09-04T12:00:00', '2026-09-04T12:05:00', 1024, 'vhash1', 'parsed');
            """
        )
        conn.execute(
            """
            INSERT INTO extracted_files (file_id, case_id, channel_id, start_timestamp, end_timestamp, size_bytes, file_hash, extraction_type)
            VALUES ('file_ch2', 'c1', 2, '2026-09-04T12:05:00', '2026-09-04T12:10:00', 1024, 'vhash2', 'parsed');
            """
        )
    conn.close()

    # Create vehicle detections in file_ch1 and file_ch2
    det_engine = detector.YOLOv8Detector()
    frames = [np.ones((100, 100, 3), dtype=np.uint8) * 150]
    
    detector.run_detection_on_clip(db_file, "file_ch1", frames, ["2026-09-04 12:01:00"], detector=det_engine)
    detector.run_detection_on_clip(db_file, "file_ch2", frames, ["2026-09-04 12:06:00"], detector=det_engine)

    # Run Vehicle Re-ID
    v_reid_engine = reid_vehicle.VehicleReID()
    reid_ch1 = reid_vehicle.run_reid_on_vehicles(db_file, "file_ch1", frames=frames, reid_engine=v_reid_engine)
    reid_ch2 = reid_vehicle.run_reid_on_vehicles(db_file, "file_ch2", frames=frames, reid_engine=v_reid_engine)

    assert len(reid_ch1) > 0
    assert len(reid_ch2) > 0

    # Verify INVESTIGATIVE_LEAD_LABEL in DB
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM vehicle_reid_embeddings;")
    v_rows = cur.fetchall()
    for row in v_rows:
        assert row["label"] == models.INVESTIGATIVE_LEAD_LABEL
    conn.close()

    # Test Suspect Journey View cross-reference helper
    matches = suspect_journey_view.cross_reference_reid(db_file, source_channel=1, target_channel=2, threshold=0.1)
    assert len(matches) > 0
    assert matches[0]["label"] == models.INVESTIGATIVE_LEAD_LABEL
