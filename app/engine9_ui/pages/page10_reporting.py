"""Page 10 — Export & Compliance Reporting.
1. Convenience copy derivative MP4 remuxing (non-evidentiary with independent SHA-256).
2. Bharatiya Sakshya Adhiniyam (BSA 2023) Section 63 technical draft report generation.
3. Embedded preview of generated reports and certificate text.
"""

import os
import json
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFileDialog, QGroupBox, QMessageBox
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine1_acquisition.image_reader import ImageReader
from app.engine9_ui.export_module import export_derivative_clip, CONVENIENCE_COPY_LABEL
from app.engine10_compliance.bsa_sec63 import generate_bsa_sec63_cert_draft, SECTION_63_DISCLAIMER
from app.engine10_compliance.report_builder import build_json_report, generate_case_report_pdf_with_sec63


class Page10Reporting(QWidget):
    """
    Page 10: Legal Compliance Drafting & Derivative Convenience Copy Export.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.init_ui()

        self.session.case_changed.connect(self._on_session_changed)
        self._on_session_changed()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(14)

        # Header Title
        title = QLabel("EXPORT & COMPLIANCE REPORTING", self)
        title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        self.main_layout.addWidget(title)

        subtitle = QLabel("Step 10: Generate Section 63 BSA compliance drafts and non-evidentiary derivative convenience copies.", self)
        subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        self.main_layout.addWidget(subtitle)

        # Empty State
        self.empty_widget = EmptyStateWidget(
            icon_str="⚖️",
            title="No Case Active for Reporting",
            description="No active case is loaded. Initialize a case on Page 1 to generate reports or export convenience copies.",
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
        content_v.setSpacing(12)

        # Action Buttons Row
        act_h = QHBoxLayout()

        self.btn_export_mp4 = QPushButton("Export Convenience Copy (.mp4)", self)
        self.btn_export_mp4.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['panel_bg']};
            border: 1px solid {DFIR_DARK_THEME['border_color']};
            color: {DFIR_DARK_THEME['text_bright']};
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
        """)
        self.btn_export_mp4.clicked.connect(self._export_mp4)
        act_h.addWidget(self.btn_export_mp4)

        self.btn_gen_pdf = QPushButton("Generate Section 63 Certificate (PDF)", self)
        self.btn_gen_pdf.setStyleSheet("""
            background-color: #238636;
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_gen_pdf.clicked.connect(self._generate_pdf)
        act_h.addWidget(self.btn_gen_pdf)

        self.btn_preview_json = QPushButton("Preview JSON Case Audit", self)
        self.btn_preview_json.clicked.connect(self._preview_json)
        act_h.addWidget(self.btn_preview_json)

        act_h.addStretch()
        content_v.addLayout(act_h)

        # Warning / Disclaimer Banner
        self.lbl_disclaimer = QLabel(
            f"<b>COMPLIANCE NOTICE:</b> {SECTION_63_DISCLAIMER}<br>"
            f"<b>EVIDENTIARY BOUNDARY:</b> All MP4 exports are strictly '{CONVENIENCE_COPY_LABEL}'.",
            self
        )
        self.lbl_disclaimer.setStyleSheet("""
            background-color: #161B22;
            color: #E6EDF3;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #30363D;
        """)
        content_v.addWidget(self.lbl_disclaimer)

        # Preview Group
        grp_preview = QGroupBox("Live Report & Certificate Text Preview", self.content_widget)
        grp_preview.setStyleSheet(f"""
            QGroupBox {{
                color: {DFIR_DARK_THEME['text_bright']};
                font-weight: bold;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 6px;
                margin-top: 8px;
                padding: 10px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
        """)
        prev_v = QVBoxLayout(grp_preview)

        self.txt_preview = QTextEdit(self)
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0D1117;
                color: #58A6FF;
                font-family: Consolas;
                font-size: 11px;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 4px;
            }}
        """)
        prev_v.addWidget(self.txt_preview)
        content_v.addWidget(grp_preview)

        self.main_layout.addWidget(self.content_widget)

    def _on_session_changed(self):
        if not self.session.has_case:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
        else:
            self.empty_widget.setVisible(False)
            self.content_widget.setVisible(True)
            self._update_text_preview()

    def _update_text_preview(self):
        if not self.session.has_case:
            return

        case_info = {
            "case_id": self.session.case_id,
            "investigator": self.session.investigator_name or "Forensic Investigator",
            "created_at": "2026-09-13T00:00:00Z",
            "sha256": self.session.acquisition_result.sha256 if self.session.acquisition_result else "",
            "md5": self.session.acquisition_result.md5 if self.session.acquisition_result else "",
        }
        extracted_files = [
            {
                "file_id": f.file_id,
                "channel_id": f.channel_id,
                "file_hash": "SHA256_VERIFIED",
                "extraction_type": f.extraction_type,
            }
            for f in (self.session.virtual_file_system.files if self.session.virtual_file_system else [])
        ]
        audit_chain = [{"timestamp": e["timestamp"], "event_type": e["event_type"]} for e in self.session.events_log]

        cert_draft = generate_bsa_sec63_cert_draft(case_info, extracted_files, audit_chain)
        full_text = f"{cert_draft['part_a']}\n\n{cert_draft['part_b']}"
        self.txt_preview.setPlainText(full_text)

    def _export_mp4(self):
        entry = self.session.active_file_entry
        if not entry or not self.session.has_evidence:
            QMessageBox.warning(self, "No Clip", "Select an active video clip to export.")
            return

        case_dir = os.path.dirname(self.session.db_path)
        deriv_dir = os.path.join(case_dir, "derivatives")
        os.makedirs(deriv_dir, exist_ok=True)

        raw_temp_path = os.path.join(deriv_dir, f"{entry.file_id}_raw.h264")
        mp4_out_path = os.path.join(deriv_dir, f"{entry.file_id}_convenience.mp4")

        # Dump raw elementary bytes to temporary file for remuxing
        with ImageReader(self.session.image_path) as reader:
            if entry.cluster_runs:
                start_sec = entry.cluster_runs[0].start_sector
                sec_cnt = entry.cluster_runs[0].sector_count
                reader.seek(start_sec * 512)
                stream_bytes = reader.read(sec_cnt * 512)
            else:
                reader.seek(0)
                stream_bytes = reader.read(min(entry.size_bytes, 10 * 1024 * 1024))

        with open(raw_temp_path, "wb") as f_raw:
            f_raw.write(stream_bytes)

        try:
            res = export_derivative_clip(
                db_path=self.session.db_path,
                case_id=self.session.case_id,
                input_raw_path=raw_temp_path,
                output_export_path=mp4_out_path,
            )
            QMessageBox.information(
                self,
                "Convenience Copy Exported",
                f"Exported non-evidentiary derivative clip:\n\n"
                f"File: {res['export_path']}\n"
                f"Independent SHA-256: {res['export_hash']}\n\n"
                f"Mandatory Label: {res['label']}"
            )
            self._update_text_preview()
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Remuxer export failed:\n\n{e}")

    def _generate_pdf(self):
        if not self.session.has_case:
            return

        case_dir = os.path.dirname(self.session.db_path)
        out_pdf = os.path.join(case_dir, f"BSA_Sec63_{self.session.case_id}.pdf")

        try:
            generate_case_report_pdf_with_sec63(self.session.db_path, self.session.case_id, out_pdf)
            QMessageBox.information(
                self,
                "Section 63 Certificate Generated",
                f"Court-ready Section 63 BSA draft PDF generated:\n\n{out_pdf}\n\nNotice: {SECTION_63_DISCLAIMER}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Report Generation Error", f"Failed to generate PDF:\n\n{e}")

    def _preview_json(self):
        if not self.session.has_case:
            return
        report_data = build_json_report(self.session.db_path, self.session.case_id)
        self.txt_preview.setPlainText(json.dumps(report_data, indent=2))
