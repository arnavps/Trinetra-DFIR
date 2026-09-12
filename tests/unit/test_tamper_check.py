"""Unit tests for engine8_ai/tamper_check.py anti-splice & QP discontinuity detection."""

import numpy as np
from app.engine8_ai.tamper_check import analyze_tamper_and_discontinuities
from app.engine7_case_db.db import init_db
from app.engine7_case_db.audit_log import verify_audit_chain


def test_tamper_check_detects_duplicate_gop_frame(tmp_path):
    db_file = str(tmp_path / "test_case.db")
    init_db(db_file)

    # Generate sample frames
    f1 = np.full((100, 100, 3), 10, dtype=np.uint8)
    f2 = np.full((100, 100, 3), 50, dtype=np.uint8)
    f3 = np.full((100, 100, 3), 10, dtype=np.uint8)  # Duplicate of f1 inserted to simulate splicing

    frames = [f1, f2, f3]
    res = analyze_tamper_and_discontinuities(frames, db_path=db_file, case_id="CASE-TAMPER-TEST")

    assert res["is_tampered"] is True
    assert len(res["duplicate_frame_pairs"]) == 1
    assert res["duplicate_frame_pairs"][0] == (0, 2)
    assert verify_audit_chain(db_file, "CASE-TAMPER-TEST") is True


def test_tamper_check_detects_qp_discontinuity(tmp_path):
    db_file = str(tmp_path / "test_case.db")
    init_db(db_file)

    f1 = np.full((100, 100, 3), 10, dtype=np.uint8)
    f2 = np.full((100, 100, 3), 50, dtype=np.uint8)

    qp_values = [20, 22, 45]  # QP jump of 23 > threshold 15
    res = analyze_tamper_and_discontinuities([f1, f2, f1], qp_values=qp_values, qp_threshold=15, db_path=db_file, case_id="CASE-QP-TEST")

    assert res["is_tampered"] is True
    assert len(res["qp_discontinuities"]) == 1
    assert res["qp_discontinuities"][0]["qp_delta"] == 23
