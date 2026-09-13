"""
2D cross-camera Re-ID trajectory map — investigative-lead framing only.
Visibly flags simulated Re-ID matches when ONNX model weights are unverified.
"""

import json
import sqlite3
from typing import List, Dict, Any, Optional
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)

from app.engine7_case_db.models import INVESTIGATIVE_LEAD_LABEL


def cross_reference_reid(
    db_path: str,
    source_channel: int = 1,
    target_channel: int = 2,
    threshold: float = 0.5,
) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    matches = []

    try:
        cur = conn.cursor()

        query_sql = """
            SELECT r.reid_id, r.detection_id, r.file_id, r.embedding_json, r.label, r.is_simulated,
                   f.channel_id, d.timestamp, d.class_name
            FROM person_reid_embeddings r
            JOIN extracted_files f ON r.file_id = f.file_id
            JOIN detections d ON r.detection_id = d.detection_id
        """
        cur.execute(query_sql)
        person_rows = cur.fetchall()

        query_v_sql = """
            SELECT r.reid_id, r.detection_id, r.file_id, r.embedding_json, r.label, r.is_simulated,
                   f.channel_id, d.timestamp, d.class_name
            FROM vehicle_reid_embeddings r
            JOIN extracted_files f ON r.file_id = f.file_id
            JOIN detections d ON r.detection_id = d.detection_id
        """
        cur.execute(query_v_sql)
        vehicle_rows = cur.fetchall()

        all_rows = list(person_rows) + list(vehicle_rows)

        source_items = [r for r in all_rows if r["channel_id"] == source_channel]
        target_items = [r for r in all_rows if r["channel_id"] == target_channel]

        for s in source_items:
            s_emb = np.array(json.loads(s["embedding_json"]), dtype=np.float32)
            s_norm = s_emb / (np.linalg.norm(s_emb) + 1e-6)

            for t in target_items:
                t_emb = np.array(json.loads(t["embedding_json"]), dtype=np.float32)
                t_norm = t_emb / (np.linalg.norm(t_emb) + 1e-6)

                sim = float(np.dot(s_norm, t_norm))
                if sim >= threshold:
                    lbl = s["label"]
                    is_sim = s["is_simulated"] or t["is_simulated"]
                    if is_sim and "(SIMULATED)" not in lbl:
                        lbl += " (SIMULATED)"
                    matches.append({
                        "source_channel": source_channel,
                        "source_time": s["timestamp"],
                        "target_channel": target_channel,
                        "target_time": t["timestamp"],
                        "class_name": s["class_name"],
                        "similarity": sim,
                        "label": lbl,
                    })

    finally:
        conn.close()

    return matches


class SuspectJourneyViewWidget(QWidget):
    def __init__(self, db_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Cross-Camera Suspect Journey & Trajectory View")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 4px; color: #58A6FF;")
        layout.addWidget(header)

        advisory_label = QLabel(f"Mandatory Classification Notice: All matches are {INVESTIGATIVE_LEAD_LABEL.upper()} | [SIMULATED MATCHES — model weights unverified]")
        advisory_label.setStyleSheet("color: #dc2626; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(advisory_label)

        # Control layout
        ctrl_layout = QHBoxLayout()

        ctrl_layout.addWidget(QLabel("Source Camera:"))
        self.src_combo = QComboBox()
        self.src_combo.addItems(["Ch 1 - Main Gate", "Ch 2 - Cashier", "Ch 3 - Parking", "Ch 4 - Vault"])
        ctrl_layout.addWidget(self.src_combo)

        ctrl_layout.addWidget(QLabel("Target Camera:"))
        self.tgt_combo = QComboBox()
        self.tgt_combo.addItems(["Ch 2 - Cashier", "Ch 1 - Main Gate", "Ch 3 - Parking", "Ch 4 - Vault"])
        ctrl_layout.addWidget(self.tgt_combo)

        self.btn_match = QPushButton("Run Cross-Camera Match")
        self.btn_match.clicked.connect(self.perform_match)
        ctrl_layout.addWidget(self.btn_match)

        layout.addLayout(ctrl_layout)

        # Matches Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Source Cam", "Source Timestamp", "Target Cam", "Target Timestamp", "Entity Class", "Re-ID Cosine Similarity", "Advisory Tag"
        ])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("""
            QTableWidget {
                font-family: Consolas, monospace;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #161B22;
                color: #58A6FF;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)

    def set_db_path(self, db_path: str):
        self.db_path = db_path
        self.perform_match()

    def perform_match(self):
        if not self.db_path:
            self.table.setRowCount(0)
            return

        src_ch = self.src_combo.currentIndex() + 1
        tgt_ch = self.tgt_combo.currentIndex() + 1

        matches = cross_reference_reid(self.db_path, source_channel=src_ch, target_channel=tgt_ch, threshold=0.1)

        if not matches:
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(matches))
        for row_idx, m in enumerate(matches):
            self.table.setItem(row_idx, 0, QTableWidgetItem(f"Ch {m['source_channel']}"))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(m["source_time"])))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"Ch {m['target_channel']}"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(m["target_time"])))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(m["class_name"])))
            self.table.setItem(row_idx, 5, QTableWidgetItem(f"{m['similarity']:.3f}"))
            self.table.setItem(row_idx, 6, QTableWidgetItem(m["label"]))
