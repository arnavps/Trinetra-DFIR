"""
Unit tests for Remuxer import boundary check, derivative clip export, independent hashing,
and mandatory convenience copy labeling.
"""

import os
import glob
import sqlite3
import pytest

from app.engine7_case_db import db
from app.engine9_ui import export_module


def test_remuxer_single_caller_import_boundary():
    """
    Architecture Invariant Test: Asserts that remuxer.py's ONLY caller in the entire
    app codebase is engine9_ui/export_module.py.
    """
    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app"))
    python_files = glob.glob(os.path.join(app_root, "**", "*.py"), recursive=True)

    remuxer_import_sites = []

    for file_path in python_files:
        # Ignore remuxer.py itself
        if os.path.basename(file_path) == "remuxer.py":
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if "import remuxer" in content or "from app.engine5_playback.remuxer" in content:
                rel_path = os.path.relpath(file_path, app_root)
                remuxer_import_sites.append(rel_path)

    assert len(remuxer_import_sites) == 1, (
        f"ARCHITECTURE VIOLATION: remuxer.py must be imported ONLY by export_module.py. "
        f"Found import sites: {remuxer_import_sites}"
    )
    assert "export_module.py" in remuxer_import_sites[0], (
        f"Expected single import site in export_module.py, found {remuxer_import_sites[0]}"
    )


def test_export_module_derivative_clip(tmp_path):
    """
    Tests investigator-triggered derivative clip export:
    - Generates independent SHA-256 hash.
    - Writes non-evidentiary derivative_export audit_log entry.
    - Attaches CONVENIENCE_COPY_LABEL.
    """
    db_file = os.path.join(tmp_path, "case_export_test.db")
    db.init_db(db_file)

    conn = sqlite3.connect(db_file)
    with conn:
        conn.execute("INSERT INTO cases (case_id, name, created_at) VALUES ('c1', 'Export Case', '2026-09-04T12:00:00');")
    conn.close()

    input_raw = os.path.join(tmp_path, "sample_stream.raw")
    with open(input_raw, "wb") as f:
        f.write(b"RAW_ELEMENTARY_STREAM_BYTES_FOR_DERIVATIVE_EXPORT_TEST")

    output_mp4 = os.path.join(tmp_path, "exported_clip.mp4")

    res = export_module.export_derivative_clip(
        db_path=db_file,
        case_id="c1",
        input_raw_path=input_raw,
        output_export_path=output_mp4,
    )

    assert os.path.exists(output_mp4)
    assert "export_hash" in res
    assert res["label"] == export_module.CONVENIENCE_COPY_LABEL
    assert "convenience copy" in res["label"]

    # Verify audit_log entry
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_log WHERE event_type = 'derivative_export';")
    rows = cur.fetchall()

    assert len(rows) == 1
    assert rows[0]["case_id"] == "c1"
    assert "convenience copy" in rows[0]["details"]
    conn.close()
