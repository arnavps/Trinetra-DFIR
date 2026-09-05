"""
Unit tests for YOLOv8n object detector, model_registry checksum verification, and read-only advisory lane.
Note: Test frames use synthetic numpy arrays for offline CPU-only testing.
"""

import hashlib
import json
import os
import sqlite3
import tempfile
import pytest
import numpy as np

from app.engine7_case_db import db, models
from app.engine8_ai import model_registry, detector


def test_model_registry_checksum_refusal(tmp_path):
    """
    Asserts model_registry refuses to load an ONNX model whose file checksum does not match models/manifest.json.
    """
    fake_model_file = tmp_path / "yolov8n.onnx"
    fake_model_file.write_bytes(b"corrupted or tampered onnx model binary content")

    # verify_model_checksum should return False for tampered file
    assert not model_registry.verify_model_checksum("yolov8n.onnx", str(fake_model_file))

    # load_onnx_session should raise RuntimeError due to checksum failure
    with pytest.raises(RuntimeError, match="Checksum verification failed"):
        model_registry.load_onnx_session("yolov8n.onnx", custom_path=str(fake_model_file))


def test_model_registry_unregistered_model(tmp_path):
    """
    Asserts model_registry raises ValueError if model is not registered in models/manifest.json.
    """
    fake_model_file = tmp_path / "unknown_model.onnx"
    fake_model_file.write_bytes(b"dummy binary data")

    with pytest.raises(ValueError, match="not registered"):
        model_registry.verify_model_checksum("unknown_model.onnx", str(fake_model_file))


def test_detector_run_and_read_only_advisory_lane(tmp_path):
    """
    Tests YOLOv8 detector processing test frames and persisting annotations.
    Assures original extracted_files table and file hashes are 100% untouched.
    """
    db_file = os.path.join(tmp_path, "case_test.db")
    db.init_db(db_file)

    # Insert a dummy case and extracted_file into engine7_case_db
    conn = sqlite3.connect(db_file)
    with conn:
        conn.execute(
            "INSERT INTO cases (case_id, name, created_at) VALUES ('case1', 'Test Case', '2026-09-04T12:00:00');"
        )
        conn.execute(
            """
            INSERT INTO extracted_files (file_id, case_id, channel_id, start_timestamp, end_timestamp, size_bytes, file_hash, extraction_type)
            VALUES ('file1', 'case1', 1, '2026-09-04T12:00:00', '2026-09-04T12:01:00', 1024, 'abc123hash', 'parsed');
            """
        )
    conn.close()

    # Generate synthetic frames (RGB numpy arrays)
    frames = [
        np.zeros((100, 100, 3), dtype=np.uint8),
        np.ones((100, 100, 3), dtype=np.uint8) * 128,
    ]
    timestamps = ["2026-09-04T12:00:05", "2026-09-04T12:00:10"]

    det_engine = detector.YOLOv8Detector()
    det_ids = detector.run_detection_on_clip(
        db_path=db_file,
        file_id="file1",
        frames=frames,
        timestamps=timestamps,
        detector=det_engine,
    )

    assert len(det_ids) > 0, "Detections should have been inserted"

    # Verify annotation table records
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM detections WHERE file_id = 'file1';")
    rows = cur.fetchall()
    assert len(rows) == len(det_ids)
    assert rows[0]["file_id"] == "file1"
    assert rows[0]["class_name"] in ("person", "car")

    # READ-ONLY ADVISORY LANE INVARIANT: Assert extracted_files table remains completely unchanged
    cur.execute("SELECT file_hash, extraction_type FROM extracted_files WHERE file_id = 'file1';")
    ef_row = cur.fetchone()
    assert ef_row["file_hash"] == "abc123hash"
    assert ef_row["extraction_type"] == "parsed"

    conn.close()
