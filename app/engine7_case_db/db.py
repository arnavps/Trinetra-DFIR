"""SQLite WAL-mode connection management, one file per case."""

import sqlite3
import os


def get_db_connection(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: str) -> None:
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    investigator TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL,
                    FOREIGN KEY(case_id) REFERENCES cases(case_id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS extracted_files (
                    file_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    channel_id INTEGER NOT NULL,
                    start_timestamp TEXT NOT NULL,
                    end_timestamp TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    extraction_type TEXT NOT NULL,
                    storage_path TEXT,
                    FOREIGN KEY(case_id) REFERENCES cases(case_id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    detection_id TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    frame_index INTEGER NOT NULL,
                    class_name TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    bbox_json TEXT NOT NULL,
                    is_simulated INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY(file_id) REFERENCES extracted_files(file_id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS face_detections (
                    face_id TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    frame_index INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    bbox_json TEXT NOT NULL,
                    landmarks_json TEXT,
                    is_simulated INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY(file_id) REFERENCES extracted_files(file_id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS person_reid_embeddings (
                    reid_id TEXT PRIMARY KEY,
                    detection_id TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    label TEXT NOT NULL,
                    is_simulated INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY(detection_id) REFERENCES detections(detection_id),
                    FOREIGN KEY(file_id) REFERENCES extracted_files(file_id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plate_detections (
                    plate_id TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    frame_index INTEGER NOT NULL,
                    plate_text TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    bbox_json TEXT NOT NULL,
                    is_simulated INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY(file_id) REFERENCES extracted_files(file_id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_reid_embeddings (
                    reid_id TEXT PRIMARY KEY,
                    detection_id TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    label TEXT NOT NULL,
                    is_simulated INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY(detection_id) REFERENCES detections(detection_id),
                    FOREIGN KEY(file_id) REFERENCES extracted_files(file_id)
                );
            """)
    finally:
        conn.close()


