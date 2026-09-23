"""Bookmark / Evidence Flagging storage and queries in Engine 7 Case DB.

Bookmarks are always investigator-authored content, never AI-generated.
They capture human observations, flags, and notes referencing specific frames,
clips, or detections, and are included under 'Investigator Findings' in court reports.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.engine7_case_db.db import get_db_connection


class Bookmark(dict):
    """Investigator Bookmark supporting both attribute and dict-key access."""

    def __init__(
        self,
        id: str,
        case_id: str,
        reference: str,
        note: str,
        created_by: str,
        created_at: str,
    ):
        data = {
            "id": id,
            "case_id": case_id,
            "reference": reference,
            "note": note,
            "created_by": created_by,
            "created_at": created_at,
        }
        super().__init__(data)

    @property
    def id(self) -> str:
        return self["id"]

    @property
    def case_id(self) -> str:
        return self["case_id"]

    @property
    def reference(self) -> str:
        return self["reference"]

    @property
    def note(self) -> str:
        return self["note"]

    @property
    def created_by(self) -> str:
        return self["created_by"]

    @property
    def created_at(self) -> str:
        return self["created_at"]


def add_bookmark(
    db_path: str,
    case_id: str,
    reference: str,
    note: str,
    created_by: str = "Investigator",
) -> Bookmark:
    """
    Creates an investigator bookmark in the case database.
    reference: identifier such as 'file1 @ Frame #14 (00:00:14)' or 'det_12345'
    note: mandatory investigator note text
    """
    if not note or not note.strip():
        raise ValueError("Bookmark note cannot be empty — investigator explanation is required.")

    b_id = f"BM-{uuid.uuid4().hex[:8].upper()}"
    ts = datetime.now(timezone.utc).isoformat()
    note_clean = note.strip()
    ref_clean = reference.strip() if reference else "General Evidence Note"

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO bookmarks (id, case_id, reference, note, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (b_id, case_id, ref_clean, note_clean, created_by, ts),
            )
    finally:
        conn.close()

    return Bookmark(
        id=b_id,
        case_id=case_id,
        reference=ref_clean,
        note=note_clean,
        created_by=created_by,
        created_at=ts,
    )


def get_bookmarks(db_path: str, case_id: str) -> List[Bookmark]:
    """Retrieves all investigator bookmarks for a given case ordered chronologically."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, case_id, reference, note, created_by, created_at
            FROM bookmarks
            WHERE case_id = ?
            ORDER BY created_at ASC;
            """,
            (case_id,),
        )
        rows = cursor.fetchall()
        return [
            Bookmark(
                id=r["id"],
                case_id=r["case_id"],
                reference=r["reference"],
                note=r["note"],
                created_by=r["created_by"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        conn.close()

