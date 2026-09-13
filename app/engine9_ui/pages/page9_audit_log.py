"""Page 9 — Case Database & Chain-of-Custody Log.
Live, read-only view of hash-chained audit log records.
Interactive verification re-walks the cryptographic Merkle chain.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine7_case_db.db import get_db_connection
from app.engine7_case_db.audit_log import verify_audit_chain, compute_entry_hash, GENESIS_HASH


class Page9AuditLog(QWidget):
    """
    Page 9: Cryptographic Chain-of-Custody Audit Log & Integrity Validator.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.init_ui()

        self.session.case_changed.connect(self.refresh_log)
        self.session.event_logged.connect(lambda _: self.refresh_log())
        self.refresh_log()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(14)

        # Header Title
        title = QLabel("CASE DATABASE & CHAIN-OF-CUSTODY AUDIT LOG", self)
        title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        self.main_layout.addWidget(title)

        subtitle = QLabel("Step 9: Review append-only, SHA-256 hash-chained forensic audit logs per ISO/IEC 27037.", self)
        subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        self.main_layout.addWidget(subtitle)

        # Empty State
        self.empty_widget = EmptyStateWidget(
            icon_str="📜",
            title="No Active Case Database",
            description="No active case is loaded. Initialize a new case in Page 1 (Intake) to start recording verifiable audit events.",
            button_text="Go to Intake (Page 1)",
            button_callback=lambda: self.navigate_to_page.emit(1),
            parent=self,
        )
        self.main_layout.addWidget(self.empty_widget)

        # Content Widget
        self.content_widget = QWidget(self)
        self.content_widget.setVisible(False)
        content_v = QVBoxLayout(self.content_widget)
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(10)

        # Controls & Verification Banner
        ctrl_h = QHBoxLayout()
        self.btn_verify_chain = QPushButton("Verify Chain Integrity Live", self)
        self.btn_verify_chain.setStyleSheet("""
            background-color: #238636;
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_verify_chain.clicked.connect(self._verify_chain_live)
        ctrl_h.addWidget(self.btn_verify_chain)

        self.lbl_verify_result = QLabel("", self)
        self.lbl_verify_result.setStyleSheet("font-family: Consolas; font-size: 12px; font-weight: bold;")
        ctrl_h.addWidget(self.lbl_verify_result)
        ctrl_h.addStretch()

        self.btn_refresh = QPushButton("Refresh Log", self)
        self.btn_refresh.clicked.connect(self.refresh_log)
        ctrl_h.addWidget(self.btn_refresh)
        content_v.addLayout(ctrl_h)

        # Audit Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Timestamp (UTC)", "Event Type", "Details", "Previous Hash", "Entry Hash (SHA256)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                gridline-color: {DFIR_DARK_THEME['border_color']};
                color: {DFIR_DARK_THEME['text_normal']};
            }}
            QHeaderView::section {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                color: {DFIR_DARK_THEME['text_bright']};
                font-weight: bold;
                padding: 6px;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
            }}
        """)
        content_v.addWidget(self.table)

        self.main_layout.addWidget(self.content_widget)

    def refresh_log(self):
        if not self.session.has_case:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
            return

        self.empty_widget.setVisible(False)
        self.content_widget.setVisible(True)

        try:
            conn = get_db_connection(self.session.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT entry_id, timestamp, event_type, details, previous_hash, entry_hash FROM audit_log WHERE case_id = ? ORDER BY entry_id ASC",
                (self.session.case_id,)
            )
            rows = cursor.fetchall()
            conn.close()

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                item_id = QTableWidgetItem(str(row["entry_id"]))
                item_ts = QTableWidgetItem(row["timestamp"])
                item_evt = QTableWidgetItem(row["event_type"])
                item_det = QTableWidgetItem(row["details"])

                prev_h = row["previous_hash"]
                prev_display = prev_h[:12] + "..." if len(prev_h) > 12 else prev_h
                item_prev = QTableWidgetItem(prev_display)
                item_prev.setToolTip(prev_h)

                cur_h = row["entry_hash"]
                cur_display = cur_h[:12] + "..." if len(cur_h) > 12 else cur_h
                item_cur = QTableWidgetItem(cur_display)
                item_cur.setToolTip(cur_h)
                item_cur.setForeground(Qt.GlobalColor.cyan)

                self.table.setItem(i, 0, item_id)
                self.table.setItem(i, 1, item_ts)
                self.table.setItem(i, 2, item_evt)
                self.table.setItem(i, 3, item_det)
                self.table.setItem(i, 4, item_prev)
                self.table.setItem(i, 5, item_cur)

            if rows and not self.lbl_verify_result.text():
                self.lbl_verify_result.setText(f"{len(rows)} hash-chained events logged.")
                self.lbl_verify_result.setStyleSheet("color: #8B949E; font-size: 11px;")
        except Exception as e:
            self.lbl_verify_result.setText(f"Audit log read error: {e}")

    def _verify_chain_live(self):
        """Walks the entire audit log hash chain live and verifies cryptographic integrity."""
        if not self.session.has_case:
            return

        conn = get_db_connection(self.session.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT entry_id, case_id, timestamp, event_type, details, previous_hash, entry_hash FROM audit_log WHERE case_id = ? ORDER BY entry_id ASC",
            (self.session.case_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            self.lbl_verify_result.setText("Chain is empty (0 records).")
            self.lbl_verify_result.setStyleSheet("color: #8B949E;")
            return

        expected_prev = GENESIS_HASH
        broken_entry = None

        for row in rows:
            if row["previous_hash"] != expected_prev:
                broken_entry = row["entry_id"]
                break

            recalculated = compute_entry_hash(
                row["case_id"],
                row["timestamp"],
                row["event_type"],
                row["details"],
                row["previous_hash"]
            )
            if row["entry_hash"] != recalculated:
                broken_entry = row["entry_id"]
                break

            expected_prev = row["entry_hash"]

        if broken_entry is None:
            self.lbl_verify_result.setText(f"CHAIN OF CUSTODY VERIFIED: PASS ({len(rows)} entries intact, Genesis to #{rows[-1]['entry_id']})")
            self.lbl_verify_result.setStyleSheet("color: #3FB950; font-weight: bold;")
        else:
            self.lbl_verify_result.setText(f"CHAIN OF CUSTODY INTEGRITY VIOLATION: Cryptographic mismatch at Entry #{broken_entry}!")
            self.lbl_verify_result.setStyleSheet("color: #F85149; font-weight: bold;")
            QMessageBox.critical(
                self,
                "Audit Chain Integrity Failure",
                f"Cryptographic hash chain verification failed!\nBroken link at entry ID #{broken_entry}."
            )
