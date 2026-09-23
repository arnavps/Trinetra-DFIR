"""Page 3 — OEM & Filesystem Detection.
Deterministic primary-path signature matcher with Random Forest fallback.
No silent auto-routing: unverified predictions require manual confirmation.
"""

import os
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QComboBox, QMessageBox, QFrame
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine2_detector.signature_matcher import match_signature, MatchResult
from app.engine2_detector.fallback_classifier import FallbackClassifier

from app.engine3_parsers.hikfat_parser import HikFatParser
from app.engine3_parsers.dhfs_parser import DhfsParser
from app.engine3_parsers.heimvision_parser import HeimVisionParser
from app.engine3_parsers.generic_parser import GenericParser
from app.engine9_ui.job_manager import JobManager


class Page3OemDetect(QWidget):
    """
    Page 3: OEM Signature Scanner & Fallback Classifier.
    Routes verified OEM drives to physical filesystem parsers.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.fallback_result: Optional[dict] = None
        self.init_ui()

        self.session.case_changed.connect(self._on_session_changed)
        self.session.acquisition_completed.connect(lambda _: self.run_detection())

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # Header Title
        title = QLabel("OEM & FILESYSTEM DETECTION", self)
        title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        self.main_layout.addWidget(title)

        subtitle = QLabel("Step 3: Scan proprietary filesystem signatures and route to deterministic parser plugin.", self)
        subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        self.main_layout.addWidget(subtitle)

        # Empty State
        self.empty_widget = EmptyStateWidget(
            icon_str="🔍",
            title="No Evidence Available",
            description="No acquired evidence is currently loaded. Complete acquisition on Page 1 & 2 before running filesystem detection.",
            button_text="Go to Intake (Page 1)",
            button_callback=lambda: self.navigate_to_page.emit(1),
            parent=self,
        )
        self.main_layout.addWidget(self.empty_widget)

        # Content Widget
        self.content_widget = QWidget(self)
        self.content_widget.setVisible(False)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        # Trigger button row
        act_h = QHBoxLayout()
        self.btn_run_scan = QPushButton("Re-Scan OEM Signatures", self)
        self.btn_run_scan.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['panel_bg']};
            border: 1px solid {DFIR_DARK_THEME['border_color']};
            color: {DFIR_DARK_THEME['text_bright']};
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
        """)
        self.btn_run_scan.clicked.connect(self.run_detection)
        act_h.addWidget(self.btn_run_scan)
        act_h.addStretch()
        content_layout.addLayout(act_h)

        # Match Container (Deterministic Path)
        self.grp_match = QGroupBox("Deterministic Signature Match", self.content_widget)
        self.grp_match.setStyleSheet(f"""
            QGroupBox {{
                color: {DFIR_DARK_THEME['text_bright']};
                font-weight: bold;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 6px;
                margin-top: 8px;
                padding: 14px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
        """)
        match_v = QVBoxLayout(self.grp_match)
        match_v.setSpacing(8)

        self.lbl_match_statement = QLabel("", self)
        self.lbl_match_statement.setStyleSheet("font-size: 13px; font-weight: bold; color: #3FB950;")
        self.lbl_match_statement.setWordWrap(True)
        match_v.addWidget(self.lbl_match_statement)

        self.lbl_sig_details = QLabel("", self)
        self.lbl_sig_details.setStyleSheet("font-family: Consolas; font-size: 11px; color: #8B949E;")
        match_v.addWidget(self.lbl_sig_details)

        self.btn_parse = QPushButton("Parse Filesystem", self)
        self.btn_parse.setStyleSheet("""
            background-color: #238636;
            color: #FFFFFF;
            font-weight: bold;
            padding: 9px 18px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_parse.clicked.connect(self._on_parse_clicked)
        match_v.addWidget(self.btn_parse, alignment=Qt.AlignmentFlag.AlignLeft)

        content_layout.addWidget(self.grp_match)

        # Fallback Container (Random Forest Heuristic Path)
        self.grp_fallback = QGroupBox("Advisory Fallback Classification", self.content_widget)
        self.grp_fallback.setStyleSheet(self.grp_match.styleSheet())
        self.grp_fallback.setVisible(False)
        fb_v = QVBoxLayout(self.grp_fallback)
        fb_v.setSpacing(10)

        # Mandatory non-dismissable unverified warning banner
        self.warn_banner = QLabel("UNVERIFIED — statistical best guess, manual confirmation required before proceeding.", self)
        self.warn_banner.setStyleSheet("""
            background-color: #3A2404;
            color: #F0883E;
            font-weight: bold;
            font-size: 11px;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #9E6A03;
        """)
        fb_v.addWidget(self.warn_banner)

        self.lbl_fb_stats = QLabel("", self)
        self.lbl_fb_stats.setStyleSheet("font-family: Consolas; font-size: 11px; color: #E6EDF3;")
        fb_v.addWidget(self.lbl_fb_stats)

        # Manual Confirmation Controls
        confirm_h = QHBoxLayout()
        confirm_h.addWidget(QLabel("<b>Confirm Target OEM Parser:</b>"))
        self.combo_oem_confirm = QComboBox(self)
        self.combo_oem_confirm.addItems(["Hikvision", "Dahua", "HeimVision", "Generic Carver"])
        confirm_h.addWidget(self.combo_oem_confirm)

        self.btn_confirm_oem = QPushButton("Confirm OEM & Parse →", self)
        self.btn_confirm_oem.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['accent_blue']};
            color: #FFFFFF;
            font-weight: bold;
            padding: 7px 16px;
            border-radius: 4px;
        """)
        self.btn_confirm_oem.clicked.connect(self._on_confirm_oem_clicked)
        confirm_h.addWidget(self.btn_confirm_oem)
        confirm_h.addStretch()
        fb_v.addLayout(confirm_h)

        content_layout.addWidget(self.grp_fallback)

        self.main_layout.addWidget(self.content_widget)
        self.main_layout.addStretch()

    def _on_session_changed(self):
        if not self.session.has_evidence:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
        else:
            self.empty_widget.setVisible(False)
            self.content_widget.setVisible(True)

    def run_detection(self):
        """Executes real OEM signature detection against the currently loaded image inside a background job."""
        if not self.session.has_evidence:
            return

        image_path = self.session.image_path
        self.btn_run_scan.setEnabled(False)
        self.lbl_match_statement.setText("Scanning OEM filesystem signatures in background...")

        def _scan_worker(progress_callback=None):
            if progress_callback:
                progress_callback(15, f"Scanning signatures on {os.path.basename(image_path)}...")
            match_res = match_signature(image_path)
            fb_res = None
            if not match_res.matched:
                if progress_callback:
                    progress_callback(55, "Scanning heuristic fallback features...")
                reader = self.session.get_image_reader()
                if reader:
                    reader.seek(0)
                    sector_bytes = reader.read(4096)
                else:
                    sector_bytes = b""
                clf = FallbackClassifier()
                fb_res = clf.predict(sector_bytes)

            if progress_callback:
                progress_callback(100, "Signature scan complete.")
            return {"match_res": match_res, "fallback_res": fb_res}

        def _on_scan_success(data):
            self.btn_run_scan.setEnabled(True)
            match_res = data["match_res"]
            self.session.set_oem_result(match_res)

            if match_res.matched:
                self.grp_match.setVisible(True)
                self.grp_fallback.setVisible(False)
                statement = f"Bytes at offset 0x{match_res.matched_offset:X} match the published {match_res.oem} signature."
                self.lbl_match_statement.setText(statement)
                self.lbl_sig_details.setText(
                    f"Signature ID: {match_res.signature_id} | Description: {match_res.description} | Target: {match_res.oem}"
                )
                self.btn_parse.setText(f"Parse Filesystem ({match_res.oem}) →")
            else:
                self.grp_match.setVisible(False)
                self.grp_fallback.setVisible(True)
                pred = data.get("fallback_res") or {}
                self.fallback_result = pred
                pred_oem = pred.get("predicted_oem", "Unknown")
                conf = pred.get("confidence", 0.0)
                reasoning = pred.get("reasoning", "")
                self.lbl_fb_stats.setText(
                    f"Predicted OEM: {pred_oem} | Model Confidence: {conf:.2f}\nReasoning: {reasoning}"
                )
                idx = self.combo_oem_confirm.findText(pred_oem)
                if idx >= 0:
                    self.combo_oem_confirm.setCurrentIndex(idx)

        def _on_scan_error(err_msg):
            self.btn_run_scan.setEnabled(True)
            self.lbl_match_statement.setText(f"OEM scan failed: {err_msg}")
            QMessageBox.critical(self, "OEM Scan Error", f"Failed to scan OEM signatures:\n\n{err_msg}")

        return JobManager.instance().submit_job(
            job_type="OEM_DETECT",
            description=f"Scan OEM Signatures ({os.path.basename(image_path)})",
            task_fn=_scan_worker,
            on_success=_on_scan_success,
            on_error=_on_scan_error,
        )

    def _execute_parser(self, oem_choice: str):
        """Runs the chosen parser plugin in a background job and loads VFS into the session."""
        image_path = self.session.image_path
        if not image_path:
            return

        self.btn_parse.setEnabled(False)
        self.btn_confirm_oem.setEnabled(False)

        def _parse_worker(progress_callback=None):
            if progress_callback:
                progress_callback(10, f"Initializing {oem_choice} filesystem parser...")
            oem_lower = oem_choice.lower()
            if "hik" in oem_lower:
                parser = HikFatParser()
            elif "dah" in oem_lower:
                parser = DhfsParser()
            elif "heim" in oem_lower:
                parser = HeimVisionParser()
            else:
                parser = GenericParser()

            if progress_callback:
                progress_callback(40, f"Parsing index blocks on {os.path.basename(image_path)}...")
            vfs = parser.parse(image_path)
            if progress_callback:
                progress_callback(100, f"Parsed {len(vfs.files)} evidentiary files.")
            return vfs

        def _on_parse_success(vfs):
            self.btn_parse.setEnabled(True)
            self.btn_confirm_oem.setEnabled(True)
            self.session.set_vfs(vfs)
            self.navigate_to_page.emit(4)

        def _on_parse_error(err_msg):
            self.btn_parse.setEnabled(True)
            self.btn_confirm_oem.setEnabled(True)
            QMessageBox.critical(self, "Parser Error", f"Parser failed for {oem_choice}:\n\n{err_msg}")

        JobManager.instance().submit_job(
            job_type="VFS_PARSE",
            description=f"Parse {oem_choice} VFS ({os.path.basename(image_path)})",
            task_fn=_parse_worker,
            on_success=_on_parse_success,
            on_error=_on_parse_error,
        )

    def _on_parse_clicked(self):
        if self.session.oem_match_result:
            self._execute_parser(self.session.oem_match_result.oem)

    def _on_confirm_oem_clicked(self):
        selected_oem = self.combo_oem_confirm.currentText()
        self._execute_parser(selected_oem)
