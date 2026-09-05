"""Hash-chained, append-only logger — every other engine calls this, it never writes to the DB directly itself."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.engine7_case_db.db import get_db_connection, init_db
from app.engine7_case_db.models import AuditEntry, ExtractedFile


GENESIS_HASH = "0" * 64


def compute_entry_hash(case_id: str, timestamp: str, event_type: str, details_json: str, previous_hash: str) -> str:
    payload = f"{case_id}|{timestamp}|{event_type}|{details_json}|{previous_hash}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def log_event(db_path: str, case_id: str, event_type: str, details: Dict[str, Any]) -> AuditEntry:
    init_db(db_path)
    conn = get_db_connection(db_path)

    # Ensure case exists in cases table
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO cases (case_id, name, investigator, created_at) VALUES (?, ?, ?, ?)",
            (case_id, f"Case {case_id}", "System", datetime.now(timezone.utc).isoformat())
        )

    cursor = conn.cursor()
    cursor.execute(
        "SELECT entry_hash FROM audit_log WHERE case_id = ? ORDER BY entry_id DESC LIMIT 1",
        (case_id,)
    )
    row = cursor.fetchone()
    previous_hash = row["entry_hash"] if row else GENESIS_HASH

    timestamp = datetime.now(timezone.utc).isoformat()
    details_json = json.dumps(details, sort_keys=True)
    entry_hash = compute_entry_hash(case_id, timestamp, event_type, details_json, previous_hash)

    with conn:
        cursor.execute(
            """
            INSERT INTO audit_log (case_id, timestamp, event_type, details, previous_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (case_id, timestamp, event_type, details_json, previous_hash, entry_hash)
        )
        entry_id = cursor.lastrowid

    conn.close()

    return AuditEntry(
        entry_id=entry_id,
        case_id=case_id,
        timestamp=timestamp,
        event_type=event_type,
        details=details,
        previous_hash=previous_hash,
        entry_hash=entry_hash
    )


def record_extracted_file(db_path: str, ext_file: ExtractedFile) -> None:
    init_db(db_path)
    conn = get_db_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO extracted_files 
            (file_id, case_id, channel_id, start_timestamp, end_timestamp, size_bytes, file_hash, extraction_type, storage_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ext_file.file_id,
                ext_file.case_id,
                ext_file.channel_id,
                ext_file.start_timestamp,
                ext_file.end_timestamp,
                ext_file.size_bytes,
                ext_file.file_hash,
                ext_file.extraction_type,
                ext_file.storage_path,
            )
        )
    conn.close()


def get_extracted_files(db_path: str, case_id: str) -> List[ExtractedFile]:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT file_id, case_id, channel_id, start_timestamp, end_timestamp, size_bytes, file_hash, extraction_type, storage_path FROM extracted_files WHERE case_id = ? ORDER BY file_id ASC",
        (case_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        ExtractedFile(
            file_id=row["file_id"],
            case_id=row["case_id"],
            channel_id=row["channel_id"],
            start_timestamp=row["start_timestamp"],
            end_timestamp=row["end_timestamp"],
            size_bytes=row["size_bytes"],
            file_hash=row["file_hash"],
            extraction_type=row["extraction_type"],
            storage_path=row["storage_path"],
        )
        for row in rows
    ]


def verify_audit_chain(db_path: str, case_id: str) -> bool:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT entry_id, case_id, timestamp, event_type, details, previous_hash, entry_hash FROM audit_log WHERE case_id = ? ORDER BY entry_id ASC",
        (case_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    expected_prev_hash = GENESIS_HASH

    for row in rows:
        if row["previous_hash"] != expected_prev_hash:
            return False

        recalculated_hash = compute_entry_hash(
            row["case_id"],
            row["timestamp"],
            row["event_type"],
            row["details"],
            row["previous_hash"]
        )

        if row["entry_hash"] != recalculated_hash:
            return False

        expected_prev_hash = row["entry_hash"]

    return True
