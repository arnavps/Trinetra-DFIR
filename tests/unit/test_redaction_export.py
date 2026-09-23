"""Unit tests for Redaction on Export (Section 3.1 & Section 5)."""

import os
import sqlite3
import pytest

from app.engine7_case_db.db import init_db
from app.engine7_case_db.audit_log import get_db_connection
from app.engine9_ui.export_module import export_redacted_clip, CONVENIENCE_COPY_LABEL


@pytest.fixture
def temp_case_env(tmp_path):
    db_path = str(tmp_path / "case.db")
    init_db(db_path)
    case_id = "CASE-REDACTION-TEST-001"

    # Create dummy raw elementary stream file (synthetic primary evidence mock)
    raw_path = str(tmp_path / "stream_01.h264")
    with open(raw_path, "wb") as f:
        f.write(b"\x00\x00\x00\x01\x67" + b"A" * 1024)

    return {"db_path": db_path, "case_id": case_id, "raw_path": raw_path, "tmp_path": tmp_path}


def test_redaction_boundary_and_audit_logging(temp_case_env):
    db_path = temp_case_env["db_path"]
    case_id = temp_case_env["case_id"]
    raw_path = temp_case_env["raw_path"]
    out_mp4 = str(temp_case_env["tmp_path"] / "derivative_redacted.mp4")

    # Read original primary bytes before export
    with open(raw_path, "rb") as f:
        original_primary_bytes = f.read()

    redaction_boxes = [[10, 10, 50, 50], [100, 100, 200, 200]]

    # Execute redacted export
    result = export_redacted_clip(
        db_path=db_path,
        case_id=case_id,
        input_raw_path=raw_path,
        output_export_path=out_mp4,
        redaction_boxes=redaction_boxes,
        is_simulated_warning=True,
    )

    # 1. Primary evidentiary file must remain strictly untouched
    with open(raw_path, "rb") as f:
        current_primary_bytes = f.read()
    assert current_primary_bytes == original_primary_bytes, "Primary evidence file was modified!"

    # 2. Derivative redacted file exists and is separate
    assert os.path.exists(out_mp4)
    assert result["export_path"] == out_mp4
    assert result["label"] == CONVENIENCE_COPY_LABEL
    assert result["box_count"] == 2
    assert len(result["export_hash"]) == 64

    # 3. Audit trail records EXPORT_REDACTED distinct event
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT event_type, details FROM audit_log WHERE event_type = 'EXPORT_REDACTED'")
    row = cur.fetchone()
    conn.close()

    assert row is not None, "EXPORT_REDACTED event was not logged to audit log!"
    assert "simulated_warning" in row[1]
    assert "box_count" in row[1]
