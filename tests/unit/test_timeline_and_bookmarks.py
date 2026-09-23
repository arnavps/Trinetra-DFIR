"""Unit tests for Bookmark & Case Timeline features (Section 3.2, 3.3, 5)."""

import os
import pytest
from PySide6.QtWidgets import QApplication

from app.engine7_case_db.db import init_db
from app.engine7_case_db.bookmarks import add_bookmark, get_bookmarks
from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.pages.page11_timeline import Page11CaseTimeline


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_case(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "case.db")
    init_db(db_path)
    case_id = "CASE-TIMELINE-BM-001"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO cases (case_id, name, created_at) VALUES (?, ?, ?);",
        (case_id, "Timeline Test Case", "2026-09-23T12:00:00")
    )
    conn.commit()
    conn.close()
    return {"db_path": db_path, "case_id": case_id, "tmp_path": tmp_path}


def test_bookmarks_persistence_and_empty_state(temp_case):
    db_path = temp_case["db_path"]
    case_id = temp_case["case_id"]

    # 1. Initially empty
    initial_bookmarks = get_bookmarks(db_path, case_id)
    assert len(initial_bookmarks) == 0

    # 2. Add investigator bookmark
    bm = add_bookmark(
        db_path=db_path,
        case_id=case_id,
        reference="CLIP_CH01:frame_1520",
        note="Suspect observed wearing reflective jacket holding device.",
        created_by="Insp. V. Sharma",
    )

    assert bm.id.startswith("BM-")
    assert bm.reference == "CLIP_CH01:frame_1520"
    assert bm.note == "Suspect observed wearing reflective jacket holding device."
    assert bm.created_by == "Insp. V. Sharma"

    # 3. Retrieve persists across restarts/connections
    stored = get_bookmarks(db_path, case_id)
    assert len(stored) == 1
    assert stored[0].id == bm.id
    assert stored[0].reference == bm.reference


def test_page11_timeline_empty_and_populated(qapp, temp_case):
    session = CaseSession()
    session.case_id = temp_case["case_id"]
    session.db_path = temp_case["db_path"]

    page11 = Page11CaseTimeline(session)

    # Empty state when no events
    assert page11.table.rowCount() == 0

    # Log an engine event and add a bookmark
    session.log_engine_event(
        event_type="ACQUISITION_RECORDED",
        message="Acquisition completed for test image",
        details={"channel_id": "System"},
    )
    add_bookmark(
        db_path=temp_case["db_path"],
        case_id=temp_case["case_id"],
        reference="DET_001",
        note="Key vehicle identified",
        created_by="Investigator",
    )

    # Reload timeline data
    page11._load_timeline_data()
    qapp.processEvents()

    assert page11.table.rowCount() >= 2
    # Verify every rendered row has a traceable event
    categories = [page11.table.item(r, 1).text() for r in range(page11.table.rowCount())]
    assert "Acquisition & Hash" in categories or "System Audit Events" in categories
    assert "Investigator Bookmarks" in categories
