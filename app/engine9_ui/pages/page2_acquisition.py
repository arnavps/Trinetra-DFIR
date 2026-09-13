"""Page 2 — Acquisition & Integrity Report.
Populated strictly by real AcquisitionResult from Engine 1.
No field on this page may ever be blank-but-styled-as-populated.
"""

from typing import Optional
from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QApplication, QGroupBox
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME


class Page2Acquisition(QWidget):
    """
    Page 2: Cryptographic Integrity & Acquisition Ledger.
    Displays live SHA-256, MD5, Merkle root, byte counts, and execution timestamps.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.init_ui()

        # Connect session updates
        self.session.case_changed.connect(self.refresh_data)
        self.session.acquisition_completed.connect(lambda _: self.refresh_data())
        self.refresh_data()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # Header Title
        title = QLabel("ACQUISITION & INTEGRITY REPORT", self)
        title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        self.main_layout.addWidget(title)

        subtitle = QLabel("Step 2: Review cryptographically verified bitstream hashes, Merkle root, and timing metrics.", self)
        subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        self.main_layout.addWidget(subtitle)

        # Empty State Container
        self.empty_widget = EmptyStateWidget(
            icon_str="🛡️",
            title="No Acquisition Run Yet",
            description="Acquisition has not yet been performed for this evidence. Return to Page 1 (Case Intake) to select a source, verify write-block, and begin acquisition.",
            button_text="Go to Case Intake (Page 1)",
            button_callback=lambda: self.navigate_to_page.emit(1),
            parent=self,
        )
        self.main_layout.addWidget(self.empty_widget)

        # Populated Content Container
        self.content_widget = QWidget(self)
        self.content_widget.setVisible(False)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        # Group 1: Source & Output
        grp_source = QGroupBox("Evidence File & Source Paths", self.content_widget)
        grp_source.setStyleSheet(f"""
            QGroupBox {{
                color: {DFIR_DARK_THEME['text_bright']};
                font-weight: bold;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 14px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
        """)
        s_layout = QGridLayout(grp_source)
        s_layout.setContentsMargins(14, 14, 14, 14)
        s_layout.setHorizontalSpacing(16)
        s_layout.setVerticalSpacing(8)

        s_layout.addWidget(QLabel("<b>Source Path / Device:</b>"), 0, 0)
        self.val_source = QLabel("", self)
        self.val_source.setStyleSheet("font-family: Consolas; color: #58A6FF;")
        s_layout.addWidget(self.val_source, 0, 1)

        s_layout.addWidget(QLabel("<b>Acquired Image Path:</b>"), 1, 0)
        self.val_dest = QLabel("", self)
        self.val_dest.setStyleSheet("font-family: Consolas; color: #58A6FF;")
        s_layout.addWidget(self.val_dest, 1, 1)

        s_layout.addWidget(QLabel("<b>Write-Block Status:</b>"), 2, 0)
        self.val_wb = QLabel("", self)
        s_layout.addWidget(self.val_wb, 2, 1)

        content_layout.addWidget(grp_source)

        # Group 2: Cryptographic Hashes
        grp_hashes = QGroupBox("Cryptographic Hash Verification", self.content_widget)
        grp_hashes.setStyleSheet(grp_source.styleSheet())
        h_layout = QGridLayout(grp_hashes)
        h_layout.setContentsMargins(14, 14, 14, 14)
        h_layout.setHorizontalSpacing(16)
        h_layout.setVerticalSpacing(10)

        # SHA-256
        h_layout.addWidget(QLabel("<b>SHA-256:</b>"), 0, 0)
        self.val_sha256 = QLabel("", self)
        self.val_sha256.setStyleSheet("font-family: Consolas; font-size: 12px; color: #3FB950; font-weight: bold;")
        h_layout.addWidget(self.val_sha256, 0, 1)

        self.btn_copy_sha = QPushButton("Copy SHA-256", self)
        self.btn_copy_sha.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.btn_copy_sha.clicked.connect(self._copy_sha256)
        h_layout.addWidget(self.btn_copy_sha, 0, 2)

        # MD5
        h_layout.addWidget(QLabel("<b>MD5:</b>"), 1, 0)
        self.val_md5 = QLabel("", self)
        self.val_md5.setStyleSheet("font-family: Consolas; font-size: 12px; color: #E6EDF3;")
        h_layout.addWidget(self.val_md5, 1, 1)

        self.btn_copy_md5 = QPushButton("Copy MD5", self)
        self.btn_copy_md5.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.btn_copy_md5.clicked.connect(self._copy_md5)
        h_layout.addWidget(self.btn_copy_md5, 1, 2)

        # Merkle Root
        h_layout.addWidget(QLabel("<b>Merkle Tree Root:</b>"), 2, 0)
        self.val_merkle = QLabel("", self)
        self.val_merkle.setStyleSheet("font-family: Consolas; font-size: 12px; color: #58A6FF;")
        h_layout.addWidget(self.val_merkle, 2, 1)

        content_layout.addWidget(grp_hashes)

        # Group 3: Metrics & Timestamps
        grp_metrics = QGroupBox("Timing & Sector Telemetry", self.content_widget)
        grp_metrics.setStyleSheet(grp_source.styleSheet())
        m_layout = QGridLayout(grp_metrics)
        m_layout.setContentsMargins(14, 14, 14, 14)
        m_layout.setHorizontalSpacing(16)
        m_layout.setVerticalSpacing(8)

        m_layout.addWidget(QLabel("<b>Total Byte Count:</b>"), 0, 0)
        self.val_bytes = QLabel("", self)
        self.val_bytes.setStyleSheet("font-family: Consolas;")
        m_layout.addWidget(self.val_bytes, 0, 1)

        m_layout.addWidget(QLabel("<b>Acquisition Started (UTC):</b>"), 1, 0)
        self.val_started = QLabel("", self)
        self.val_started.setStyleSheet("font-family: Consolas;")
        m_layout.addWidget(self.val_started, 1, 1)

        m_layout.addWidget(QLabel("<b>Acquisition Finished (UTC):</b>"), 2, 0)
        self.val_finished = QLabel("", self)
        self.val_finished.setStyleSheet("font-family: Consolas;")
        m_layout.addWidget(self.val_finished, 2, 1)

        m_layout.addWidget(QLabel("<b>Elapsed Duration:</b>"), 3, 0)
        self.val_duration = QLabel("", self)
        self.val_duration.setStyleSheet("font-family: Consolas;")
        m_layout.addWidget(self.val_duration, 3, 1)

        content_layout.addWidget(grp_metrics)

        # Bottom navigation
        nav_h = QHBoxLayout()
        self.btn_next = QPushButton("Proceed to OEM & Filesystem Detection (Page 3) →", self)
        self.btn_next.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['accent_blue']};
            color: #FFFFFF;
            font-weight: bold;
            font-size: 12px;
            padding: 10px 18px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_next.clicked.connect(lambda: self.navigate_to_page.emit(3))
        nav_h.addWidget(self.btn_next, alignment=Qt.AlignmentFlag.AlignRight)
        content_layout.addLayout(nav_h)

        self.main_layout.addWidget(self.content_widget)
        self.main_layout.addStretch()

    def refresh_data(self):
        """Refreshes report strictly from CaseSession.acquisition_result."""
        res = self.session.acquisition_result
        if res is None:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
            return

        self.empty_widget.setVisible(False)
        self.content_widget.setVisible(True)

        self.val_source.setText(self.session.evidence_source or res.path)
        self.val_dest.setText(res.path)

        if res.write_blocked:
            self.val_wb.setText("WRITE-BLOCKED — VERIFIED (Read-Only Enforcement Confirmed)")
            self.val_wb.setStyleSheet("color: #3FB950; font-weight: bold;")
        else:
            self.val_wb.setText("WRITE VIOLATION WARNING (Writable Handle Detected)")
            self.val_wb.setStyleSheet("color: #F85149; font-weight: bold;")

        self.val_sha256.setText(res.sha256)
        self.val_md5.setText(res.md5)
        self.val_merkle.setText(res.merkle_root)

        mb_val = res.byte_count / (1024 * 1024)
        self.val_bytes.setText(f"{res.byte_count:,} bytes ({mb_val:.2f} MB)")
        self.val_started.setText(res.started_at)
        self.val_finished.setText(res.finished_at)

        try:
            t0 = datetime.fromisoformat(res.started_at)
            t1 = datetime.fromisoformat(res.finished_at)
            dur = (t1 - t0).total_seconds()
            self.val_duration.setText(f"{dur:.2f} seconds")
        except Exception:
            self.val_duration.setText("N/A")

    def _copy_sha256(self):
        if self.session.acquisition_result:
            QApplication.clipboard().setText(self.session.acquisition_result.sha256)
            self.btn_copy_sha.setText("Copied!")

    def _copy_md5(self):
        if self.session.acquisition_result:
            QApplication.clipboard().setText(self.session.acquisition_result.md5)
            self.btn_copy_md5.setText("Copied!")
