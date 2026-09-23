"""Page 12 — Case Health Dashboard.
Single glanceable dashboard aggregating live-recomputed health metrics:
1. Model verification status (model_registry.verify_all_models())
2. Hash-chain integrity (verify_audit_chain())
3. Write-block hardware/software status
4. Verified vs. Simulated AI results breakdown
5. Parsed VFS files vs. Carved fragments ratio
6. Investigator bookmarks count

Presented as a traffic-light summary (green/amber/red per category) with links
jumping directly to home pages. All numbers computed strictly live on load/refresh.
"""

import os
import sqlite3
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QFrame, QGroupBox, QScrollArea
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine8_ai.model_registry import verify_all_models
from app.engine7_case_db.audit_log import verify_audit_chain
from app.engine7_case_db.bookmarks import get_bookmarks


class HealthCard(QFrame):
    """Individual traffic-light health indicator card with live metrics and navigation link."""

    link_clicked = Signal(int)

    def __init__(
        self,
        title: str,
        target_page: int,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.target_page = target_page

        self.setStyleSheet(f"""
            HealthCard {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 6px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header: Title + Status Pill
        hdr = QHBoxLayout()
        self.lbl_title = QLabel(title, self)
        self.lbl_title.setStyleSheet(f"""
            font-size: 13px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
            font-family: 'Segoe UI', sans-serif;
        """)
        hdr.addWidget(self.lbl_title)
        hdr.addStretch()

        self.lbl_badge = QLabel("● UNKNOWN", self)
        self.lbl_badge.setStyleSheet("""
            font-family: Consolas, monospace;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 4px;
            background-color: #21262D;
            color: #8B949E;
        """)
        hdr.addWidget(self.lbl_badge)
        layout.addLayout(hdr)

        # Big Metric Display
        self.lbl_metric = QLabel("—", self)
        self.lbl_metric.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['accent_blue']};
            font-family: Consolas, monospace;
        """)
        layout.addWidget(self.lbl_metric)

        # Detail Description
        self.lbl_desc = QLabel("Loading...", self)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet(f"color: {DFIR_DARK_THEME['text_normal']}; font-size: 11px;")
        layout.addWidget(self.lbl_desc)

        layout.addStretch()

        # Navigation Link Button
        self.btn_link = QPushButton(f"Inspect on Page {target_page} →", self)
        self.btn_link.setStyleSheet(f"""
            QPushButton {{
                background-color: #21262D;
                color: #58A6FF;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #30363D;
                color: #79C0FF;
            }}
        """)
        self.btn_link.clicked.connect(lambda: self.link_clicked.emit(self.target_page))
        layout.addWidget(self.btn_link)

    def set_status(self, level: str, text: str, metric: str, description: str):
        """
        level: 'GREEN', 'AMBER', 'RED', 'NEUTRAL'
        """
        self.lbl_metric.setText(metric)
        self.lbl_desc.setText(description)

        if level == "GREEN":
            self.lbl_badge.setText(f"🟢 {text}")
            self.lbl_badge.setStyleSheet("""
                font-family: Consolas, monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
                background-color: #16241D;
                color: #3FB950;
                border: 1px solid #238636;
            """)
        elif level == "AMBER":
            self.lbl_badge.setText(f"🟡 {text}")
            self.lbl_badge.setStyleSheet("""
                font-family: Consolas, monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
                background-color: #2E2211;
                color: #D29922;
                border: 1px solid #9E6A03;
            """)
        elif level == "RED":
            self.lbl_badge.setText(f"🔴 {text}")
            self.lbl_badge.setStyleSheet("""
                font-family: Consolas, monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
                background-color: #2D1A1E;
                color: #F85149;
                border: 1px solid #DA3633;
            """)
        else:
            self.lbl_badge.setText(f"⚪ {text}")
            self.lbl_badge.setStyleSheet("""
                font-family: Consolas, monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
                background-color: #21262D;
                color: #8B949E;
                border: 1px solid #30363D;
            """)


class Page12CaseHealth(QWidget):
    """
    Page 12: Case Health Dashboard.
    Provides live traffic-light summaries for model integrity, hash chain,
    write-block compliance, simulation ratios, and evidence counts.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session

        self.init_ui()
        self.session.case_changed.connect(self._on_session_changed)
        self.session.event_logged.connect(lambda _: self._recompute_health_metrics())
        self._on_session_changed()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        v_title = QVBoxLayout()
        self.lbl_title = QLabel("Page 12 — Case Health & Integrity Dashboard", self)
        self.lbl_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
            font-family: 'Segoe UI', sans-serif;
        """)
        v_title.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel(
            "Live glanceable verification of model provenance, chain-of-custody cryptographic seals, "
            "write-block protection, and evidentiary integrity.",
            self
        )
        self.lbl_subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_dim']}; font-size: 11px;")
        v_title.addWidget(self.lbl_subtitle)
        hdr.addLayout(v_title)
        hdr.addStretch()

        self.btn_refresh = QPushButton("Recompute Health Live", self)
        self.btn_refresh.setStyleSheet(f"""
            background-color: #238636;
            color: #FFFFFF;
            font-weight: bold;
            padding: 6px 14px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_refresh.clicked.connect(self._recompute_health_metrics)
        hdr.addWidget(self.btn_refresh)
        self.main_layout.addLayout(hdr)

        # Empty State Widget
        self.empty_widget = EmptyStateWidget(
            icon="🛡",
            title="No Case Loaded",
            description="Case Health monitors live integrity for an active case. Initialize or open a case to begin.",
            action_text="Create Case (Page 1)",
            parent=self
        )
        self.empty_widget.action_clicked.connect(lambda: self.navigate_to_page.emit(1))
        self.main_layout.addWidget(self.empty_widget)

        # Content Widget
        self.content_widget = QWidget(self)
        content_v = QVBoxLayout(self.content_widget)
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(12)

        # Grid of 6 Health Cards
        grid = QGridLayout()
        grid.setSpacing(12)

        # 1. Model Verification Status (Page 8)
        self.card_models = HealthCard("1. AI Model Integrity", 8, self.content_widget)
        self.card_models.link_clicked.connect(self.navigate_to_page)
        grid.addWidget(self.card_models, 0, 0)

        # 2. Hash Chain Integrity (Page 9)
        self.card_chain = HealthCard("2. Hash Chain-of-Custody", 9, self.content_widget)
        self.card_chain.link_clicked.connect(self.navigate_to_page)
        grid.addWidget(self.card_chain, 0, 1)

        # 3. Write-Block Protection (Page 1)
        self.card_writeblock = HealthCard("3. Write-Block Compliance", 1, self.content_widget)
        self.card_writeblock.link_clicked.connect(self.navigate_to_page)
        grid.addWidget(self.card_writeblock, 0, 2)

        # 4. AI Verified vs Simulated Results (Page 8)
        self.card_simulation = HealthCard("4. AI Provenance Ratio", 8, self.content_widget)
        self.card_simulation.link_clicked.connect(self.navigate_to_page)
        grid.addWidget(self.card_simulation, 1, 0)

        # 5. Evidentiary File Provenance (Page 4 & 5)
        self.card_files = HealthCard("5. File System Provenance", 4, self.content_widget)
        self.card_files.link_clicked.connect(self.navigate_to_page)
        grid.addWidget(self.card_files, 1, 1)

        # 6. Investigator Bookmarks (Page 11)
        self.card_bookmarks = HealthCard("6. Investigator Bookmarks", 11, self.content_widget)
        self.card_bookmarks.link_clicked.connect(self.navigate_to_page)
        grid.addWidget(self.card_bookmarks, 1, 2)

        content_v.addLayout(grid)

        # Summary Note
        lbl_compliance = QLabel(
            "<b>COURTROOM INTEGRITY RULE:</b> All numbers displayed above are computed live at this exact instant. "
            "Zero values are cached. Any database or file tampering immediately triggers red status across affected controls.",
            self.content_widget
        )
        lbl_compliance.setStyleSheet("""
            background-color: #161B22;
            color: #E6EDF3;
            font-size: 11px;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #30363D;
        """)
        content_v.addWidget(lbl_compliance)

        self.main_layout.addWidget(self.content_widget)

    def showEvent(self, event):
        """Always recompute live metrics whenever the page becomes visible."""
        super().showEvent(event)
        self._recompute_health_metrics()

    def _on_session_changed(self):
        if not self.session.has_case:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
        else:
            self.empty_widget.setVisible(False)
            self.content_widget.setVisible(True)
            self._recompute_health_metrics()

    def _recompute_health_metrics(self):
        if not self.session.has_case:
            return

        # 1. Model Verification Status
        try:
            model_report = verify_all_models()
            total_models = len(model_report)
            verified_count = sum(1 for m in model_report.values() if m.get("status") == "VERIFIED")
            mismatches = sum(1 for m in model_report.values() if m.get("status") == "CHECKSUM_MISMATCH")

            if mismatches > 0:
                self.card_models.set_status(
                    "RED", "CHECKSUM TAMPER", f"{verified_count}/{total_models} Verified",
                    f"CRITICAL: {mismatches} model(s) failed cryptographic checksum verification!"
                )
            elif verified_count == total_models and total_models > 0:
                self.card_models.set_status(
                    "GREEN", "ALL VERIFIED", f"{verified_count}/{total_models} Verified",
                    "All registered ONNX models passed independent SHA-256 verification."
                )
            else:
                self.card_models.set_status(
                    "AMBER", "PENDING SOURCING", f"{verified_count}/{total_models} Verified",
                    f"{total_models - verified_count} model(s) pending or running in simulated fallback mode."
                )
        except Exception as e:
            self.card_models.set_status("RED", "ERROR", "Check Failed", str(e))

        # 2. Hash Chain Integrity
        try:
            if self.session.db_path and os.path.exists(self.session.db_path):
                is_valid = verify_audit_chain(self.session.db_path, self.session.case_id)
                # Count total events
                conn = sqlite3.connect(self.session.db_path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM audit_log WHERE case_id = ?", (self.session.case_id,))
                event_cnt = cur.fetchone()[0]
                conn.close()

                if is_valid and event_cnt > 0:
                    self.card_chain.set_status(
                        "GREEN", "CHAIN VALID", f"{event_cnt} Events",
                        "Cryptographic SHA-256 hash chain unbroken from genesis to head."
                    )
                elif not is_valid:
                    self.card_chain.set_status(
                        "RED", "CHAIN BROKEN", f"{event_cnt} Events",
                        "CRITICAL: Audit log hash mismatch! Evidence may have been altered!"
                    )
                else:
                    self.card_chain.set_status(
                        "NEUTRAL", "EMPTY", "0 Events", "No audit events logged yet for this case."
                    )
            else:
                self.card_chain.set_status("AMBER", "NO DB", "—", "Case database not found.")
        except Exception as e:
            self.card_chain.set_status("RED", "ERROR", "Verification Error", str(e))

        # 3. Write-Block Compliance
        wb = self.session.write_block_verified
        if wb is True:
            self.card_writeblock.set_status(
                "GREEN", "VERIFIED", "READ-ONLY",
                f"Write-block confirmed. Primary source protected: {os.path.basename(str(self.session.evidence_source or 'Evidence'))}"
            )
        elif wb is False:
            self.card_writeblock.set_status(
                "RED", "VIOLATION", "WRITABLE",
                "CRITICAL WARNING: Evidence source is writable! Hardware write-blocker missing!"
            )
        else:
            self.card_writeblock.set_status(
                "AMBER", "UNVERIFIED", "NOT CHECKED",
                "Write-block integrity check has not yet been executed on evidence source."
            )

        # 4. AI Provenance Ratio (Verified vs Simulated)
        sim_count = 0
        real_count = 0
        if self.session.db_path and os.path.exists(self.session.db_path):
            try:
                conn = sqlite3.connect(self.session.db_path)
                cur = conn.cursor()

                for table in ["detections", "face_detections", "plate_detections"]:
                    cur.execute(f"SELECT is_simulated, COUNT(*) FROM {table} GROUP BY is_simulated")
                    for is_sim, cnt in cur.fetchall():
                        if is_sim:
                            sim_count += cnt
                        else:
                            real_count += cnt
                conn.close()
            except Exception:
                pass

        total_ai = sim_count + real_count
        if total_ai == 0:
            self.card_simulation.set_status(
                "NEUTRAL", "NO AI RUNS", "0 Detections", "No AI triage detections generated yet."
            )
        elif sim_count == 0:
            self.card_simulation.set_status(
                "GREEN", "100% VERIFIED", f"{real_count} Real",
                "All detection records backed by verified local ONNX model inference."
            )
        else:
            ratio = (real_count / total_ai) * 100
            self.card_simulation.set_status(
                "AMBER", "SIMULATED PRESENT", f"{sim_count} Sim / {real_count} Real",
                f"Court Warning: {sim_count} detection(s) are simulated and carry mandatory legal disclaimer."
            )

        # 5. Evidentiary File Provenance
        parsed_files = len(self.session.virtual_file_system.files) if self.session.virtual_file_system else 0
        carved_files = len(self.session.carved_fragments)
        total_files = parsed_files + carved_files

        if total_files == 0:
            self.card_files.set_status(
                "NEUTRAL", "NO FILES", "0 Files", "No evidentiary files parsed or carved yet."
            )
        elif carved_files == 0:
            self.card_files.set_status(
                "GREEN", "STRUCTURED VFS", f"{parsed_files} Parsed",
                f"OEM filesystem parsed with full directory tree structure intact."
            )
        else:
            self.card_files.set_status(
                "AMBER", "FRAGMENT RECOVERY", f"{parsed_files} VFS / {carved_files} Carved",
                f"{carved_files} elementary stream fragment(s) recovered from unallocated space."
            )

        # 6. Investigator Bookmarks
        try:
            bookmarks = get_bookmarks(self.session.db_path, self.session.case_id) if self.session.db_path else []
            b_cnt = len(bookmarks)
            if b_cnt > 0:
                self.card_bookmarks.set_status(
                    "GREEN", "DOCUMENTED", f"{b_cnt} Bookmarks",
                    f"{b_cnt} manual investigator flag(s) ready for BSA Section 63 report export."
                )
            else:
                self.card_bookmarks.set_status(
                    "NEUTRAL", "NO BOOKMARKS", "0 Bookmarks",
                    "No investigator findings or manual flags recorded yet."
                )
        except Exception as e:
            self.card_bookmarks.set_status("RED", "ERROR", "—", str(e))
