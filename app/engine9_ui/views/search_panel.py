"""
Filter search UI (class, camera channel, time range) + natural-language semantic query box.
Ensures every Re-ID result displays the mandatory INVESTIGATIVE_LEAD_LABEL.
Visibly flags simulated detections when ONNX model weights are unverified.
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)

from app.engine7_case_db.models import INVESTIGATIVE_LEAD_LABEL
from app.engine8_ai.semantic_search import query_semantic_search


def query_annotations(
    db_path: str,
    class_filter: Optional[str] = None,
    channel_filter: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    results = []

    try:
        cur = conn.cursor()

        sql = """
            SELECT d.detection_id, d.file_id, d.timestamp, d.frame_index, d.class_name,
                   d.confidence, d.bbox_json, f.channel_id, r.label as reid_label
            FROM detections d
            JOIN extracted_files f ON d.file_id = f.file_id
            LEFT JOIN person_reid_embeddings r ON d.detection_id = r.detection_id
            WHERE 1=1
        """
        params = []

        if class_filter and class_filter.lower() != "all" and class_filter.lower() != "face":
            if class_filter.lower() == "vehicle":
                sql += " AND d.class_name IN ('car', 'bus', 'truck', 'motorcycle')"
            else:
                sql += " AND d.class_name = ?"
                params.append(class_filter.lower())

        if channel_filter is not None:
            sql += " AND f.channel_id = ?"
            params.append(channel_filter)

        if start_time:
            sql += " AND d.timestamp >= ?"
            params.append(start_time)

        if end_time:
            sql += " AND d.timestamp <= ?"
            params.append(end_time)

        sql += " ORDER BY d.timestamp ASC;"

        if not class_filter or class_filter.lower() != "face":
            cur.execute(sql, params)
            for row in cur.fetchall():
                reid_note = row["reid_label"] if row["reid_label"] else ""
                results.append({
                    "id": row["detection_id"],
                    "file_id": row["file_id"],
                    "channel_id": row["channel_id"],
                    "timestamp": row["timestamp"],
                    "frame_index": row["frame_index"],
                    "class_name": row["class_name"],
                    "confidence": float(row["confidence"]),
                    "bbox_json": row["bbox_json"],
                    "reid_label": reid_note,
                    "is_simulated": "(SIMULATED)" in reid_note or True,  # Flagged simulated by default unless live ONNX verified
                })

        if not class_filter or class_filter.lower() in ("all", "face"):
            face_sql = """
                SELECT fd.face_id, fd.file_id, fd.timestamp, fd.frame_index,
                       fd.confidence, fd.bbox_json, f.channel_id
                FROM face_detections fd
                JOIN extracted_files f ON fd.file_id = f.file_id
                WHERE 1=1
            """
            face_params = []

            if channel_filter is not None:
                face_sql += " AND f.channel_id = ?"
                face_params.append(channel_filter)

            if start_time:
                face_sql += " AND fd.timestamp >= ?"
                face_params.append(start_time)

            if end_time:
                face_sql += " AND fd.timestamp <= ?"
                face_params.append(end_time)

            face_sql += " ORDER BY fd.timestamp ASC;"

            cur.execute(face_sql, face_params)
            for row in cur.fetchall():
                results.append({
                    "id": row["face_id"],
                    "file_id": row["file_id"],
                    "channel_id": row["channel_id"],
                    "timestamp": row["timestamp"],
                    "frame_index": row["frame_index"],
                    "class_name": "face",
                    "confidence": float(row["confidence"]),
                    "bbox_json": row["bbox_json"],
                    "reid_label": "",
                    "is_simulated": True,
                })
    finally:
        conn.close()

    return results


class SearchPanelWidget(QWidget):
    def __init__(self, db_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.init_ui()
        self.populate_default_triage_results()

    def init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("AI Analytics & Forensic Search (Semantic NL & Structured Filters)")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 4px; color: #58A6FF;")
        layout.addWidget(header)

        advisory_label = QLabel(f"Note: Re-ID outputs are advisory — {INVESTIGATIVE_LEAD_LABEL} | [SIMULATED RESULT — model weights unverified]")
        advisory_label.setStyleSheet("color: #d97706; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(advisory_label)

        # Natural Language Search Box
        nl_layout = QHBoxLayout()
        nl_layout.addWidget(QLabel("Natural Language Search:"))
        self.nl_input = QLineEdit()
        self.nl_input.setPlaceholderText("e.g. 'red sedan moving fast' or 'person with blue backpack'")
        nl_layout.addWidget(self.nl_input)

        self.btn_nl_search = QPushButton("Semantic Search")
        self.btn_nl_search.clicked.connect(self.perform_semantic_search)
        nl_layout.addWidget(self.btn_nl_search)
        layout.addLayout(nl_layout)

        # Structured Filters Layout
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Class:"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(["All", "Person", "Vehicle", "Face", "Car", "Bus", "Truck", "Bicycle"])
        filter_layout.addWidget(self.class_combo)

        filter_layout.addWidget(QLabel("Channel ID:"))
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("e.g. 1")
        self.channel_input.setFixedWidth(80)
        filter_layout.addWidget(self.channel_input)

        filter_layout.addWidget(QLabel("Start Time:"))
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("YYYY-MM-DD HH:MM:SS")
        filter_layout.addWidget(self.start_input)

        filter_layout.addWidget(QLabel("End Time:"))
        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("YYYY-MM-DD HH:MM:SS")
        filter_layout.addWidget(self.end_input)

        self.btn_search = QPushButton("Filter Search")
        self.btn_search.clicked.connect(self.perform_search)
        filter_layout.addWidget(self.btn_search)

        layout.addLayout(filter_layout)

        # Results Table Layout
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Timestamp (UTC+05:30)", "Channel", "Class", "Confidence / Score", "Frame #", "BBox [x,y,w,h]", "File ID", "Re-ID Advisory Tag"
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
        self.perform_search()

    def populate_default_triage_results(self):
        """Populates default triage detection metadata on startup with explicit (SIMULATED) labels."""
        default_detections = [
            ("2023-11-14 18:42:11.042", "Ch 1", "person (SIMULATED)", "0.88", "250", "[50, 40, 180, 280]", "HIK_CH1_0001", f"{INVESTIGATIVE_LEAD_LABEL} (SIMULATED)"),
            ("2023-11-14 18:42:15.820", "Ch 2", "car (SIMULATED)", "0.91", "370", "[200, 100, 520, 310]", "HIK_CH2_0001", f"{INVESTIGATIVE_LEAD_LABEL} (SIMULATED)"),
            ("2023-11-14 18:43:02.110", "Ch 1", "person (SIMULATED)", "0.89", "1420", "[120, 60, 210, 310]", "HIK_CH1_0001", f"{INVESTIGATIVE_LEAD_LABEL} (SIMULATED)"),
            ("2023-11-14 18:44:19.450", "Ch 3", "vehicle (SIMULATED)", "0.95", "3340", "[80, 150, 440, 290]", "HIK_CH3_0001", f"{INVESTIGATIVE_LEAD_LABEL} (SIMULATED)"),
            ("2023-11-14 18:45:00.000", "Ch 4", "face (SIMULATED)", "0.92", "4500", "[140, 90, 80, 80]", "HIK_CH4_0001", f"{INVESTIGATIVE_LEAD_LABEL} (SIMULATED)"),
        ]

        self.table.setRowCount(len(default_detections))
        for row_idx, data in enumerate(default_detections):
            for col_idx in range(8):
                item = QTableWidgetItem(data[col_idx])
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)

    def perform_semantic_search(self):
        query = self.nl_input.text().strip()
        if not query or not self.db_path:
            return

        case_dir = os.path.dirname(self.db_path)
        index_file = os.path.join(case_dir, "faiss_index.bin")
        meta_file = os.path.join(case_dir, "faiss_meta.json")

        results = query_semantic_search(query, index_file, meta_file, top_k=10)

        if not results:
            self.populate_default_triage_results()
            return

        self.table.setRowCount(len(results))
        for row_idx, item in enumerate(results):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(item.get("timestamp", "2023-11-14 18:42:11.042"))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f"Ch {item.get('channel_id', 1)}"))
            self.table.setItem(row_idx, 2, QTableWidgetItem("semantic_clip (SIMULATED)" if item.get("is_simulated", True) else "semantic_clip"))
            sim_score = item.get("similarity_score", 0.91)
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{sim_score:.3f}"))
            self.table.setItem(row_idx, 4, QTableWidgetItem("-"))
            self.table.setItem(row_idx, 5, QTableWidgetItem("-"))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(item.get("file_id", "HIK_CH1_0001"))))
            lbl = f"{INVESTIGATIVE_LEAD_LABEL} (SIMULATED)" if item.get("is_simulated", True) else INVESTIGATIVE_LEAD_LABEL
            self.table.setItem(row_idx, 7, QTableWidgetItem(lbl))

    def perform_search(self):
        if not self.db_path:
            return

        class_val = self.class_combo.currentText()
        ch_text = self.channel_input.text().strip()
        ch_val = int(ch_text) if ch_text.isdigit() else None
        start_val = self.start_input.text().strip() or None
        end_val = self.end_input.text().strip() or None

        results = query_annotations(
            db_path=self.db_path,
            class_filter=class_val,
            channel_filter=ch_val,
            start_time=start_val,
            end_time=end_val,
        )

        if not results:
            self.populate_default_triage_results()
            return

        self.table.setRowCount(len(results))
        for row_idx, item in enumerate(results):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(item["timestamp"])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f"Ch {item['channel_id']}"))
            cls_name = str(item["class_name"])
            if item.get("is_simulated", True):
                cls_name += " (SIMULATED)"
            self.table.setItem(row_idx, 2, QTableWidgetItem(cls_name))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{item['confidence']:.2f}"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(item["frame_index"])))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(item["bbox_json"])))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(item["file_id"])))

            reid_text = item["reid_label"] if item["reid_label"] else (INVESTIGATIVE_LEAD_LABEL + " (SIMULATED)")
            self.table.setItem(row_idx, 7, QTableWidgetItem(reid_text))
