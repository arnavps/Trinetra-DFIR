"""Unit tests for Case Health Dashboard live-recomputation (Section 3.5 & 5)."""

import os
import sqlite3
import pytest
from PySide6.QtWidgets import QApplication

from app.engine7_case_db.db import init_db
from app.engine7_case_db.audit_log import log_event
from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.pages.page12_case_health import Page12CaseHealth


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_health_case(tmp_path):
    db_path = str(tmp_path / "case.db")
    init_db(db_path)
    case_id = "CASE-HEALTH-LIVE-001"
    return {"db_path": db_path, "case_id": case_id, "tmp_path": tmp_path}


def test_case_health_live_recompute(qapp, temp_health_case):
    session = CaseSession()
    session.case_id = temp_health_case["case_id"]
    session.db_path = temp_health_case["db_path"]
    session.evidence_source = "C:/evidence/source.E01"
    session.set_write_block_status(True)

    page12 = Page12CaseHealth(session)
    qapp.processEvents()

    # Initial check on write block
    assert "READ-ONLY" in page12.card_writeblock.lbl_metric.text()

    # Initial check on AI provenance
    assert "0 Detections" in page12.card_simulation.lbl_metric.text()

    # Insert a simulated detection dynamically into the database
    conn = sqlite3.connect(temp_health_case["db_path"])
    conn.execute(
        """INSERT INTO detections 
           (detection_id, file_id, timestamp, frame_index, class_name, confidence, bbox_json, is_simulated)
           VALUES ('DET-TEST-01', 'FILE-01', '2026-09-23T12:00:00', 10, 'person', 0.95, '[0,0,10,10]', 1)"""
    )
    conn.commit()
    conn.close()

    # Recompute live — dashboard MUST reflect changes immediately without caching stale values
    page12._recompute_health_metrics()
    qapp.processEvents()

    # Now AI simulation card MUST reflect the inserted simulated detection
    assert "1 Sim" in page12.card_simulation.lbl_metric.text()

    # Insert an audit event into audit log
    log_event(
        db_path=temp_health_case["db_path"],
        case_id=temp_health_case["case_id"],
        event_type="HEALTH_TEST_EVENT",
        details={"note": "live test"},
    )

    page12._recompute_health_metrics()
    qapp.processEvents()

    assert "Events" in page12.card_chain.lbl_metric.text()
    assert "CHAIN VALID" in page12.card_chain.lbl_badge.text()
