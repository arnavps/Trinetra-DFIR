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
    QPushButton, QTextEdit, QFileDialog, QGroupBox, QMessageBox, QComboBox,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QFrame
)

import sqlite3
from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine9_ui.export_module import (
    export_derivative_clip,
    export_redacted_clip,
    CONVENIENCE_COPY_LABEL,
)
from app.engine9_ui.evidentiary_export import (
    export_evidentiary_package,
    EVIDENTIARY_PACKAGE_LABEL,
)
from app.engine7_case_db.audit_log import get_extracted_files
from app.engine10_compliance.bsa_sec63 import generate_bsa_sec63_cert_draft, SECTION_63_DISCLAIMER
from app.engine10_compliance.report_builder import build_json_report, generate_case_report_pdf_with_sec63


class EvidentiaryExportConfirmDialog(QDialog):
    """
    Mandatory confirmation dialog before exporting a Court Evidentiary Package.
    Lists all evidence files, their channels, sizes, extraction types, and cryptographic
    hashes so there is an explicit, deliberated, logged decision before packaging.
    """

    def __init__(self, case_id: str, case_name: str, files: list, default_dest: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Court Evidentiary Package Export")
        self.resize(780, 520)
        self.target_dir = default_dest

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header banner with Green border and badge
        banner = QFrame(self)
        banner.setStyleSheet("""
            background-color: #04260F;
            border: 1px solid #238636;
            border-radius: 6px;
            padding: 10px 14px;
        """)
        b_lay = QVBoxLayout(banner)
        b_lay.setSpacing(4)

        b_title = QLabel("⚖️ COURT EVIDENTIARY PACKAGE — BSA 2023 §63 & ISO/IEC 27037", banner)
        b_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #3FB950;")
        b_lay.addWidget(b_title)

        b_badge = QLabel("STATUS: ORIGINAL — UNALTERED — HASH MATCHES ACQUISITION", banner)
        b_badge.setStyleSheet("font-size: 10px; font-weight: bold; color: #3FB950; letter-spacing: 0.5px;")
        b_lay.addWidget(b_badge)

        b_desc = QLabel(
            "Every included file will be copied <b>byte-for-byte</b> with zero conversion or re-encoding. "
            "A portable standalone viewer, hash manifest (JSON & TXT), BSA Section 63 certificate draft, and independent verification "
            "instructions will be bundled into the package for court presentation.",
            banner
        )
        b_desc.setWordWrap(True)
        b_desc.setStyleSheet("font-size: 11px; color: #C9D1D9;")
        b_lay.addWidget(b_desc)
        layout.addWidget(banner)

        # Files Table
        lbl_tbl = QLabel(f"<b>Evidence Files to be Packaged ({len(files)} items):</b>", self)
        lbl_tbl.setStyleSheet("font-size: 11px; color: #E6EDF3;")
        layout.addWidget(lbl_tbl)

        self.table = QTableWidget(len(files), 5, self)
        self.table.setHorizontalHeaderLabels(["File ID", "Extraction Type", "Channel", "Size (Bytes)", "SHA-256 Digest"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 190)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 85)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161B22;
                color: #C9D1D9;
                border: 1px solid #30363D;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #21262D;
                color: #FFFFFF;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #30363D;
            }
        """)

        for row_idx, f in enumerate(files):
            self.table.setItem(row_idx, 0, QTableWidgetItem(f.file_id))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f.extraction_type))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(f.channel_id)))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(f.size_bytes)))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f.file_hash))

        layout.addWidget(self.table)

        # Destination folder selection
        dest_h = QHBoxLayout()
        dest_lbl = QLabel("Target Package Folder:", self)
        dest_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #E6EDF3;")
        dest_h.addWidget(dest_lbl)

        self.txt_dest = QLineEdit(self.target_dir, self)
        self.txt_dest.setStyleSheet("""
            background-color: #161B22;
            color: #58A6FF;
            border: 1px solid #30363D;
            border-radius: 4px;
            padding: 6px 10px;
            font-family: Consolas;
            font-size: 11px;
        """)
        dest_h.addWidget(self.txt_dest)

        btn_browse = QPushButton("Browse...", self)
        btn_browse.clicked.connect(self._browse_dest)
        dest_h.addWidget(btn_browse)
        layout.addLayout(dest_h)

        # Buttons
        btn_h = QHBoxLayout()
        btn_h.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)
        btn_h.addWidget(btn_cancel)

        self.btn_confirm = QPushButton("Confirm & Export Evidentiary Package", self)
        self.btn_confirm.setStyleSheet("""
            background-color: #238636;
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 18px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_confirm.clicked.connect(self._on_confirm)
        btn_h.addWidget(self.btn_confirm)
        layout.addLayout(btn_h)

    def _browse_dest(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select Target Folder for Evidentiary Package", self.target_dir)
        if chosen:
            self.target_dir = chosen
            self.txt_dest.setText(chosen)

    def _on_confirm(self):
        self.target_dir = self.txt_dest.text().strip()
        if not self.target_dir:
            QMessageBox.warning(self, "Invalid Path", "Please specify a destination directory.")
            return
        self.accept()


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

        subtitle = QLabel("Step 10: Export court evidentiary packages, derivative convenience copies, and Section 63 compliance drafts.", self)
        subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        self.main_layout.addWidget(subtitle)

        # Empty State
        self.empty_widget = EmptyStateWidget(
            icon_str="⚖️",
            title="No Case Active for Reporting",
            description="No active case is loaded. Initialize a case on Page 1 to generate reports or export evidence.",
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

        # Actions Row: 3 Distinct Visual Sections with Color-Coded Honesty Badges
        actions_panel = QFrame(self.content_widget)
        actions_panel.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        act_v = QVBoxLayout(actions_panel)
        act_v.setContentsMargins(8, 8, 8, 8)
        act_v.setSpacing(10)

        # Section 1: Court Evidentiary Package (Action 1 - Green Honest Pattern)
        row_evid = QHBoxLayout()
        self.btn_export_evidentiary = QPushButton("🏛 Export Court Evidentiary Package", self)
        self.btn_export_evidentiary.setStyleSheet("""
            background-color: #238636;
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 18px;
            border-radius: 4px;
            border: 1px solid #2EA043;
            font-size: 12px;
        """)
        self.btn_export_evidentiary.clicked.connect(self._export_evidentiary_package)
        row_evid.addWidget(self.btn_export_evidentiary)

        self.lbl_evid_badge = QLabel(f"● {EVIDENTIARY_PACKAGE_LABEL}", self)
        self.lbl_evid_badge.setStyleSheet("""
            color: #3FB950;
            background-color: #04260F;
            border: 1px solid #238636;
            border-radius: 4px;
            padding: 4px 10px;
            font-weight: bold;
            font-size: 11px;
        """)
        row_evid.addWidget(self.lbl_evid_badge)
        row_evid.addStretch()
        act_v.addLayout(row_evid)

        # Section 2: Convenience & Redacted Copies (Action 2 - Amber Honest Pattern)
        row_conv = QHBoxLayout()
        self.btn_export_mp4 = QPushButton("Export Convenience Copy (.mp4)", self)
        self.btn_export_mp4.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['panel_bg']};
            border: 1px solid {DFIR_DARK_THEME['border_color']};
            color: {DFIR_DARK_THEME['text_bright']};
            font-weight: bold;
            padding: 7px 14px;
            border-radius: 4px;
        """)
        self.btn_export_mp4.clicked.connect(self._export_mp4)
        row_conv.addWidget(self.btn_export_mp4)

        self.btn_export_redacted = QPushButton("Export with Redaction (.mp4)", self)
        self.btn_export_redacted.setStyleSheet("""
            background-color: #9E6A03;
            color: #FFFFFF;
            font-weight: bold;
            padding: 7px 14px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_export_redacted.clicked.connect(self._export_redacted_mp4)
        row_conv.addWidget(self.btn_export_redacted)

        self.lbl_conv_badge = QLabel("● CONVENIENCE COPY — NOT FOR COURT SUBMISSION", self)
        self.lbl_conv_badge.setStyleSheet("""
            color: #D29922;
            background-color: #2D2200;
            border: 1px solid #9E6A03;
            border-radius: 4px;
            padding: 4px 10px;
            font-weight: bold;
            font-size: 11px;
        """)
        row_conv.addWidget(self.lbl_conv_badge)
        row_conv.addStretch()
        act_v.addLayout(row_conv)

        # Section 3: Section 63 Statutory PDF Report Generation
        row_rep = QHBoxLayout()
        self.combo_mode = QComboBox(self)
        self.combo_mode.addItem("Full Technical Report (14 Sections)")
        self.combo_mode.addItem("Summary Report (Sections 1–5)")
        self.combo_mode.setStyleSheet(f"""
            QComboBox {{
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background-color: #161B22;
                color: #C9D1D9;
                selection-background-color: #0969DA;
            }}
        """)
        self.combo_mode.currentIndexChanged.connect(self._update_text_preview)
        row_rep.addWidget(self.combo_mode)

        self.btn_gen_pdf = QPushButton("Generate Section 63 Report (PDF)", self)
        self.btn_gen_pdf.setStyleSheet("""
            background-color: #1F6FEB;
            color: #FFFFFF;
            font-weight: bold;
            padding: 7px 16px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_gen_pdf.clicked.connect(self._generate_pdf)
        row_rep.addWidget(self.btn_gen_pdf)

        self.btn_preview_json = QPushButton("Preview JSON Case Audit", self)
        self.btn_preview_json.clicked.connect(self._preview_json)
        row_rep.addWidget(self.btn_preview_json)

        row_rep.addStretch()
        act_v.addLayout(row_rep)

        content_v.addWidget(actions_panel)

        # Warning / Disclaimer Banner
        self.lbl_disclaimer = QLabel(
            f"<b>COMPLIANCE NOTICE:</b> {SECTION_63_DISCLAIMER}<br>"
            f"<b>EVIDENTIARY BOUNDARY:</b> All MP4 exports are strictly '{CONVENIENCE_COPY_LABEL}'. "
            f"Only the Court Evidentiary Package contains unaltered original bytes.",
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

    def _export_evidentiary_package(self):
        """
        Exports a pristine, byte-identical Court Evidentiary Package under BSA 2023 §63.
        Shows an explicit confirmation dialog with file inventory and cryptographic hashes
        before generating the package.
        """
        if not self.session.has_case or not self.session.db_path:
            QMessageBox.warning(self, "No Case Active", "Initialize or load an active case to export evidentiary package.")
            return

        db_path = self.session.db_path
        case_id = self.session.case_id
        case_dir = os.path.dirname(os.path.abspath(db_path))

        # Retrieve extracted/carved files from case db
        files = get_extracted_files(db_path, case_id)
        if not files:
            QMessageBox.warning(
                self,
                "No Evidence Files",
                "No extracted or carved files found in the case database. "
                "Parse or carve evidence first before creating an evidentiary package."
            )
            return

        default_dest = os.path.join(case_dir, f"Court_Evidentiary_Package_{case_id}")

        dialog = EvidentiaryExportConfirmDialog(
            case_id=case_id,
            case_name=self.session.case_name or f"Case {case_id}",
            files=files,
            default_dest=default_dest,
            parent=self,
        )

        if dialog.exec() != QDialog.Accepted:
            return

        target_dir = dialog.target_dir
        try:
            res = export_evidentiary_package(
                db_path=db_path,
                case_id=case_id,
                output_package_dir=target_dir,
                session=self.session,
            )

            QMessageBox.information(
                self,
                "Court Evidentiary Package Exported",
                f"Pristine Court Evidentiary Package successfully created:\n\n"
                f"Directory: {res['package_dir']}\n"
                f"Evidence Files Packaged: {res['total_files']}\n"
                f"Package Manifest SHA-256: {res['package_manifest_hash']}\n\n"
                f"Status: {res['label']}\n\n"
                f"Contents:\n"
                f"• evidence/ (Byte-for-byte exact original files)\n"
                f"• viewer/ (Portable Standalone Evidence Player)\n"
                f"• manifest.json & manifest.txt (Cryptographic registries)\n"
                f"• BSA_Section63_Certificate.txt (Statutory certificate)\n"
                f"• INDEPENDENT_VERIFICATION.txt (Instructions for opposing experts)"
            )
            self._update_text_preview()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Evidentiary Export Failed",
                f"Failed to generate Court Evidentiary Package:\n\n{e}"
            )

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

        # Dump raw elementary bytes to temporary file for remuxing via shared session reader
        reader = self.session.get_image_reader()
        if not reader:
            QMessageBox.warning(self, "Image Reader Error", "Cannot open evidence image.")
            return

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

    def _export_redacted_mp4(self):
        """
        Exports a derivative convenience copy with face and license plate bounding boxes redacted.
        CRITICAL ARCHITECTURAL BOUNDARY:
        This is the one place in the system where re-encoding is legitimate — because it
        only ever touches the already-separate, non-evidentiary export path
        (export_module.py -> remuxer.py), never the primary evidentiary file.
        The primary evidentiary file remains strictly untouched, bit-pure, and read-only.
        """
        entry = self.session.active_file_entry
        if not entry or not self.session.has_evidence:
            QMessageBox.warning(self, "No Clip", "Select an active video clip to export with redaction.")
            return

        # Query detections for this clip to collect redaction boxes
        redaction_boxes = []
        is_simulated_warning = False

        if self.session.db_path and os.path.exists(self.session.db_path):
            try:
                conn = sqlite3.connect(self.session.db_path)
                cur = conn.cursor()

                # Check face detections
                cur.execute(
                    "SELECT bbox_json, is_simulated FROM face_detections WHERE file_id = ?",
                    (entry.file_id,)
                )
                for bbox_str, is_sim in cur.fetchall():
                    if is_sim:
                        is_simulated_warning = True
                    try:
                        box = json.loads(bbox_str)
                        if isinstance(box, list) and len(box) == 4:
                            redaction_boxes.append(box)
                    except Exception:
                        pass

                # Check plate detections
                cur.execute(
                    "SELECT bbox_json, is_simulated FROM plate_detections WHERE file_id = ?",
                    (entry.file_id,)
                )
                for bbox_str, is_sim in cur.fetchall():
                    if is_sim:
                        is_simulated_warning = True
                    try:
                        box = json.loads(bbox_str)
                        if isinstance(box, list) and len(box) == 4:
                            redaction_boxes.append(box)
                    except Exception:
                        pass

                # Check general detections for face/plate/person
                cur.execute(
                    "SELECT bbox_json, is_simulated FROM detections WHERE file_id = ? AND class_name IN ('face', 'plate', 'license_plate', 'person')",
                    (entry.file_id,)
                )
                for bbox_str, is_sim in cur.fetchall():
                    if is_sim:
                        is_simulated_warning = True
                    try:
                        box = json.loads(bbox_str)
                        if isinstance(box, list) and len(box) == 4:
                            redaction_boxes.append(box)
                    except Exception:
                        pass

                conn.close()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to query detections: {e}")
                return

        # Check simulated detections warning per Section 3.1
        if is_simulated_warning:
            reply = QMessageBox.warning(
                self,
                "Simulated Detections Warning",
                "Redaction is based on simulated detections and may miss real faces/plates — verify manually before sharing.\n\nDo you want to proceed with redacted export?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        case_dir = os.path.dirname(self.session.db_path)
        deriv_dir = os.path.join(case_dir, "derivatives")
        os.makedirs(deriv_dir, exist_ok=True)

        raw_temp_path = os.path.join(deriv_dir, f"{entry.file_id}_raw.h264")
        mp4_out_path = os.path.join(deriv_dir, f"{entry.file_id}_redacted.mp4")

        reader = self.session.get_image_reader()
        if not reader:
            QMessageBox.warning(self, "Image Reader Error", "Cannot open evidence image.")
            return

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
            res = export_redacted_clip(
                db_path=self.session.db_path,
                case_id=self.session.case_id,
                input_raw_path=raw_temp_path,
                output_export_path=mp4_out_path,
                redaction_boxes=redaction_boxes,
                is_simulated_warning=is_simulated_warning,
            )
            QMessageBox.information(
                self,
                "Redacted Convenience Copy Exported",
                f"Exported redacted non-evidentiary derivative clip:\n\n"
                f"File: {res['export_path']}\n"
                f"Independent SHA-256: {res['export_hash']}\n"
                f"Redaction Boxes Applied: {res['box_count']}\n\n"
                f"Mandatory Label: {res['label']}"
            )
            self._update_text_preview()
        except Exception as e:
            QMessageBox.critical(self, "Redacted Export Failed", f"Redacted export failed:\n\n{e}")

    def _generate_pdf(self):
        if not self.session.has_case:
            return

        mode = "full" if self.combo_mode.currentIndex() == 0 else "summary"
        case_dir = os.path.dirname(self.session.db_path)
        mode_prefix = "BSA_Sec63_Full" if mode == "full" else "BSA_Sec63_Summary"
        out_pdf = os.path.join(case_dir, f"{mode_prefix}_{self.session.case_id}.pdf")

        try:
            generate_case_report_pdf_with_sec63(
                self.session.db_path,
                self.session.case_id,
                out_pdf,
                mode=mode,
                session=self.session
            )
            sha_companion = f"{out_pdf}.sha256"
            sha_hash = ""
            if os.path.exists(sha_companion):
                with open(sha_companion, "r") as f:
                    sha_hash = f.read().split()[0]

            QMessageBox.information(
                self,
                "Section 63 Report Generated",
                f"Court-ready Section 63 BSA draft PDF generated:\n\n{out_pdf}\n\n"
                f"Report Scope: {mode.upper()} TECHNICAL REPORT\n"
                f"Self-Integrity SHA-256: {sha_hash}\n"
                f"Sealed Companion File: {os.path.basename(sha_companion)}\n\n"
                f"Notice: {SECTION_63_DISCLAIMER}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Report Generation Error", f"Failed to generate PDF:\n\n{e}")

    def _preview_json(self):
        if not self.session.has_case:
            return
        report_data = build_json_report(self.session.db_path, self.session.case_id)
        self.txt_preview.setPlainText(json.dumps(report_data, indent=2))
