"""Page 11 — Unified Case Timeline.
Aggregates and visualizes every real, timestamped forensic event for the current case:
acquisition, parsing, carving, AI triage runs, bookmarks, and derivative exports.
Read-only aggregation layer pulling directly from SQLite audit logs and result tables.
"""

import os
import json
import sqlite3
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QGroupBox
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine7_case_db.bookmarks import get_bookmarks


class Page11CaseTimeline(QWidget):
    """
    Page 11: Unified Case Timeline.
    Displays all chronological forensic events with visual distinction
    for verified vs simulated results, filterable by event type and channel.
    Double-clicking a record jumps directly to its source page.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self._all_events: List[Dict[str, Any]] = []

        self.init_ui()
        self.session.case_changed.connect(self._on_session_changed)
        self.session.event_logged.connect(lambda _: self._load_timeline_data())
        self._on_session_changed()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # Header Title Banner
        hdr_box = QHBoxLayout()
        v_title = QVBoxLayout()
        self.lbl_title = QLabel("Page 11 — Unified Case Timeline", self)
        self.lbl_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
            font-family: 'Segoe UI', sans-serif;
        """)
        v_title.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel(
            "Unified chronological aggregation of acquisitions, file system events, AI detections, "
            "investigator bookmarks, and derivative exports.",
            self
        )
        self.lbl_subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_dim']}; font-size: 11px;")
        v_title.addWidget(self.lbl_subtitle)
        hdr_box.addLayout(v_title)
        hdr_box.addStretch()

        self.btn_refresh = QPushButton("Refresh Timeline", self)
        self.btn_refresh.setStyleSheet(f"""
            background-color: #21262D;
            color: {DFIR_DARK_THEME['text_normal']};
            border: 1px solid {DFIR_DARK_THEME['border_color']};
            border-radius: 4px;
            padding: 6px 14px;
            font-weight: bold;
        """)
        self.btn_refresh.clicked.connect(self._load_timeline_data)
        hdr_box.addWidget(self.btn_refresh)

        self.main_layout.addLayout(hdr_box)

        # Empty State Widget
        self.empty_widget = EmptyStateWidget(
            icon="⏱",
            title="No Case Timeline Events",
            description="Create or load a case to aggregate acquisition, parsing, carving, AI detections, and bookmarks.",
            action_text="Go to Intake (Page 1)",
            parent=self
        )
        self.empty_widget.action_clicked.connect(lambda: self.navigate_to_page.emit(1))
        self.main_layout.addWidget(self.empty_widget)

        # Content Widget
        self.content_widget = QWidget(self)
        content_v = QVBoxLayout(self.content_widget)
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(10)

        # Filter Control Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        lbl_filter_type = QLabel("Filter Event Type:", self.content_widget)
        lbl_filter_type.setStyleSheet("color: #8B949E; font-size: 11px; font-weight: bold;")
        filter_bar.addWidget(lbl_filter_type)

        self.cmb_event_type = QComboBox(self.content_widget)
        self.cmb_event_type.addItems([
            "All Types",
            "Acquisition & Hash",
            "OEM & VFS Parsing",
            "Carved Fragments",
            "AI Detections",
            "Investigator Bookmarks",
            "Derivative Exports",
            "System Audit Events",
        ])
        self.cmb_event_type.setStyleSheet(f"""
            QComboBox {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                color: {DFIR_DARK_THEME['text_normal']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }}
        """)
        self.cmb_event_type.currentTextChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.cmb_event_type)

        lbl_filter_chan = QLabel("Channel:", self.content_widget)
        lbl_filter_chan.setStyleSheet("color: #8B949E; font-size: 11px; font-weight: bold;")
        filter_bar.addWidget(lbl_filter_chan)

        self.cmb_channel = QComboBox(self.content_widget)
        self.cmb_channel.addItems(["All Channels", "CH 01", "CH 02", "CH 03", "CH 04", "System"])
        self.cmb_channel.setStyleSheet(self.cmb_event_type.styleSheet())
        self.cmb_channel.currentTextChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.cmb_channel)

        self.txt_search = QLineEdit(self.content_widget)
        self.txt_search.setPlaceholderText("Search summary or reference ID...")
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: #0D1117;
                color: {DFIR_DARK_THEME['text_normal']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
        """)
        self.txt_search.textChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.txt_search, stretch=1)

        content_v.addLayout(filter_bar)

        # Timeline Events Table
        self.table = QTableWidget(0, 7, self.content_widget)
        self.table.setHorizontalHeaderLabels([
            "Timestamp (UTC)", "Category", "Event Type", "Channel", "Summary & Traceable Evidence", "Verification", "Source Link"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #0D1117;
                color: {DFIR_DARK_THEME['text_normal']};
                gridline-color: {DFIR_DARK_THEME['border_color']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: #161B22;
                color: #8B949E;
                font-weight: bold;
                border: 1px solid #30363D;
                padding: 6px;
            }}
            QTableWidget::item:selected {{
                background-color: #1F2D40;
                color: #58A6FF;
            }}
        """)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        content_v.addWidget(self.table)

        # Footer Navigation Guidance
        lbl_hint = QLabel("💡 Tip: Double-click any row to jump directly to its source page in the workflow.", self.content_widget)
        lbl_hint.setStyleSheet("color: #8B949E; font-size: 11px; font-style: italic;")
        content_v.addWidget(lbl_hint)

        self.main_layout.addWidget(self.content_widget)

    def _on_session_changed(self):
        if not self.session.has_case:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
        else:
            self.empty_widget.setVisible(False)
            self.content_widget.setVisible(True)
            self._load_timeline_data()

    def _load_timeline_data(self):
        if not self.session.has_case:
            return

        events: List[Dict[str, Any]] = []

        # 1. Pull Audit Events from SQLite case.db
        if self.session.db_path and os.path.exists(self.session.db_path):
            try:
                conn = sqlite3.connect(self.session.db_path)
                cur = conn.cursor()

                # Audit Log Events
                cur.execute(
                    "SELECT entry_id, timestamp, event_type, details FROM audit_log WHERE case_id = ? ORDER BY entry_id ASC",
                    (self.session.case_id,)
                )
                for event_id, ts, etype, details_raw in cur.fetchall():
                    details = {}
                    try:
                        details = json.loads(details_raw) if details_raw else {}
                    except Exception:
                        pass

                    category = "System Audit Events"
                    page = 9
                    if "ACQUISITION" in etype or "HASH" in etype or "SOURCE" in etype:
                        category = "Acquisition & Hash"
                        page = 2
                    elif "OEM" in etype or "VFS" in etype:
                        category = "OEM & VFS Parsing"
                        page = 3 if "OEM" in etype else 4
                    elif "CARV" in etype or "FRAGMENT" in etype:
                        category = "Carved Fragments"
                        page = 5
                    elif "EXPORT" in etype:
                        category = "Derivative Exports"
                        page = 10

                    msg = details.get("message", etype)
                    events.append({
                        "timestamp": ts,
                        "category": category,
                        "event_type": etype,
                        "channel": str(details.get("channel_id", "System")),
                        "summary": msg,
                        "is_simulated": False,
                        "page": page,
                        "ref_id": f"AUDIT-{event_id}",
                    })

                # AI Detections
                cur.execute(
                    "SELECT detection_id, file_id, timestamp, frame_index, class_name, confidence, is_simulated "
                    "FROM detections ORDER BY detection_id ASC"
                )
                for det_id, fid, ts, frame_idx, cname, conf, is_sim in cur.fetchall():
                    events.append({
                        "timestamp": ts,
                        "category": "AI Detections",
                        "event_type": f"DETECT_{cname.upper()}",
                        "channel": "CH 01",
                        "summary": f"Detected {cname} (conf: {conf:.2f}) on frame {frame_idx} [{fid}]",
                        "is_simulated": bool(is_sim),
                        "page": 8,
                        "ref_id": det_id,
                    })

                # Face Detections
                cur.execute(
                    "SELECT face_id, file_id, timestamp, frame_index, confidence, is_simulated "
                    "FROM face_detections ORDER BY face_id ASC"
                )
                for face_id, fid, ts, frame_idx, conf, is_sim in cur.fetchall():
                    events.append({
                        "timestamp": ts,
                        "category": "AI Detections",
                        "event_type": "DETECT_FACE",
                        "channel": "CH 01",
                        "summary": f"Face detected (conf: {conf:.2f}) on frame {frame_idx} [{fid}]",
                        "is_simulated": bool(is_sim),
                        "page": 8,
                        "ref_id": face_id,
                    })

                # Plate Detections
                cur.execute(
                    "SELECT plate_id, file_id, timestamp, frame_index, plate_text, confidence, is_simulated "
                    "FROM plate_detections ORDER BY plate_id ASC"
                )
                for plate_id, fid, ts, frame_idx, ptext, conf, is_sim in cur.fetchall():
                    events.append({
                        "timestamp": ts,
                        "category": "AI Detections",
                        "event_type": "DETECT_ANPR",
                        "channel": "CH 01",
                        "summary": f"ANPR Plate '{ptext}' (conf: {conf:.2f}) on frame {frame_idx} [{fid}]",
                        "is_simulated": bool(is_sim),
                        "page": 8,
                        "ref_id": plate_id,
                    })

                # Investigator Bookmarks
                bookmarks = get_bookmarks(self.session.db_path, self.session.case_id)
                for b in bookmarks:
                    events.append({
                        "timestamp": b.created_at,
                        "category": "Investigator Bookmarks",
                        "event_type": "BOOKMARK_FLAG",
                        "channel": "System",
                        "summary": f"Flag [{b.reference}]: {b.note} (by {b.created_by})",
                        "is_simulated": False,
                        "page": 6 if "frame" in b.reference.lower() or "clip" in b.reference.lower() else 8,
                        "ref_id": b.id,
                    })

                conn.close()
            except Exception:
                pass

        # Sort all aggregated events strictly chronologically
        events.sort(key=lambda x: str(x.get("timestamp", "")))
        self._all_events = events
        self._apply_filters()

    def _apply_filters(self):
        cat_filter = self.cmb_event_type.currentText()
        chan_filter = self.cmb_channel.currentText()
        search_query = self.txt_search.text().strip().lower()

        filtered = []
        for e in self._all_events:
            # Category filter
            if cat_filter != "All Types" and e["category"] != cat_filter:
                continue

            # Channel filter
            if chan_filter != "All Channels":
                chan_str = str(e["channel"])
                if chan_filter == "System" and "System" not in chan_str:
                    continue
                elif chan_filter.startswith("CH") and chan_filter.replace("CH 0", "").replace("CH ", "") not in chan_str:
                    continue

            # Search text query
            if search_query:
                combined = f"{e['summary']} {e['event_type']} {e['ref_id']}".lower()
                if search_query not in combined:
                    continue

            filtered.append(e)

        self._render_table(filtered)

    def _render_table(self, events: List[Dict[str, Any]]):
        self.table.setRowCount(len(events))

        for row, e in enumerate(events):
            ts_item = QTableWidgetItem(e["timestamp"][:19].replace("T", " "))
            cat_item = QTableWidgetItem(e["category"])
            etype_item = QTableWidgetItem(e["event_type"])
            chan_item = QTableWidgetItem(str(e["channel"]))
            summary_item = QTableWidgetItem(e["summary"])

            # Visual badge for verification status
            if e["is_simulated"]:
                verif_item = QTableWidgetItem("⚠ SIMULATED")
                verif_item.setForeground(Qt.yellow)
            else:
                verif_item = QTableWidgetItem("✓ VERIFIED")
                verif_item.setForeground(Qt.green)

            link_btn_text = f"Jump to Page {e['page']} →"
            link_item = QTableWidgetItem(link_btn_text)
            link_item.setForeground(Qt.cyan)

            # Store page index on item
            link_item.setData(Qt.UserRole, e["page"])

            self.table.setItem(row, 0, ts_item)
            self.table.setItem(row, 1, cat_item)
            self.table.setItem(row, 2, etype_item)
            self.table.setItem(row, 3, chan_item)
            self.table.setItem(row, 4, summary_item)
            self.table.setItem(row, 5, verif_item)
            self.table.setItem(row, 6, link_item)

    def _on_item_double_clicked(self, item: QTableWidgetItem):
        row = item.row()
        link_item = self.table.item(row, 6)
        if link_item:
            target_page = link_item.data(Qt.UserRole)
            if target_page and isinstance(target_page, int):
                self.navigate_to_page.emit(target_page)
