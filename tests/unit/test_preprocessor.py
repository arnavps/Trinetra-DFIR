"""
Unit tests for BitstreamPreprocessor SmartCodec GOP normalization and audit logging.
"""

import os
import sqlite3
import pytest

from app.engine7_case_db import db
from app.engine5_playback import bitstream_preprocessor


def test_bitstream_preprocessor_smartcodec_normalization(tmp_path):
    """
    Tests detecting non-standard SmartCodec reference GOP markers, normalizing stream,
    and persisting audit_log normalization entry.
    """
    db_file = os.path.join(tmp_path, "case_prep_test.db")
    db.init_db(db_file)

    conn = sqlite3.connect(db_file)
    with conn:
        conn.execute("INSERT INTO cases (case_id, name, created_at) VALUES ('c1', 'Prep Case', '2026-09-04T12:00:00');")
    conn.close()

    preprocessor = bitstream_preprocessor.BitstreamPreprocessor()

    # Synthetic non-standard SmartCodec GOP bitstream payload
    raw_smartcodec_bytes = b"\x00\x00\x00\x01\x67\xeeNON_STANDARD_SPS_PPS\x00\x00\x00\x01\x68\xeeSMART_GOP_PAYLOAD"

    normalized_stream, was_normalized = preprocessor.preprocess_stream(
        raw_stream=raw_smartcodec_bytes,
        db_path=db_file,
        case_id="c1",
    )

    assert was_normalized is True, "Stream should have been identified as SmartCodec non-standard and normalized"
    assert b"\x68\xee" not in normalized_stream, "Non-standard NAL marker should have been replaced"

    # Verify audit_log entry
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_log WHERE event_type = 'bitstream_normalization';")
    rows = cur.fetchall()

    assert len(rows) == 1
    assert rows[0]["case_id"] == "c1"
    assert "SmartCodec" in rows[0]["details"]
    conn.close()
