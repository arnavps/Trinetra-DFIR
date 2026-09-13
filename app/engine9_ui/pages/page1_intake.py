"""Page 1 — New Case & Evidence Intake.
The only entry point into the application. Nothing else is reachable until this completes.
"""

import os
import subprocess
import sys
from typing import Optional, List, Dict, Callable
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QRadioButton, QButtonGroup,
    QProgressBar, QComboBox, QGroupBox, QMessageBox, QFrame
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine1_acquisition.writeblock_check import verify_read_only, WriteBlockViolationError
from app.engine1_acquisition.acquirer import acquire_image, AcquisitionResult


class AcquisitionWorker(QThread):
    """Background worker for bit-stream acquisition and hashing."""
    progress_signal = Signal(int, int)  # bytes_done, total_bytes
    finished_signal = Signal(object)    # AcquisitionResult
    error_signal = Signal(str)          # exception message

    def __init__(
        self,
        source_path: str,
        dest_path: str,
        case_id: str,
        db_path: str,
        enforce_write_block: bool = True,
    ):
        super().__init__()
        self.source_path = source_path
        self.dest_path = dest_path
        self.case_id = case_id
        self.db_path = db_path
        self.enforce_write_block = enforce_write_block

    def run(self):
        try:
            def on_progress(done: int, total: int):
                self.progress_signal.emit(done, total)

            result = acquire_image(
                source_path=self.source_path,
                dest_path=self.dest_path,
                case_id=self.case_id,
                db_path=self.db_path,
                enforce_write_block=self.enforce_write_block,
                progress_callback=on_progress,
            )
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class Page1Intake(QWidget):
    """
    Page 1: Case Creation, Evidence Source Selection, Write-Block Verification, and Acquisition.
    """

    navigate_to_page = Signal(int)  # 1-indexed page number

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.worker: Optional[AcquisitionWorker] = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header Title
        title = QLabel("CASE INTAKE & FORENSIC ACQUISITION", self)
        title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        main_layout.addWidget(title)

        subtitle = QLabel("Step 1: Initialize new case record, verify read-only write block, and acquire bitstream evidence.", self)
        subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        main_layout.addWidget(subtitle)

        # Group 1: Case Identity
        grp_case = QGroupBox("1. Case Identification", self)
        grp_case.setStyleSheet(f"""
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
        case_layout = QVBoxLayout(grp_case)

        form_h = QHBoxLayout()
        lbl_case_no = QLabel("Case Reference ID:")
        self.txt_case_id = QLineEdit(self)
        self.txt_case_id.setPlaceholderText("e.g. CR-2026-0812")

        lbl_case_name = QLabel("Case Name:")
        self.txt_case_name = QLineEdit(self)
        self.txt_case_name.setPlaceholderText("e.g. CCTV Forensic Examination")

        lbl_inv = QLabel("Investigator:")
        self.txt_investigator = QLineEdit(self)
        self.txt_investigator.setPlaceholderText("e.g. Det. Inspector Sharma")

        self.btn_init_case = QPushButton("Initialize Case Record", self)
        self.btn_init_case.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['accent_blue']};
            color: #FFFFFF;
            font-weight: bold;
            padding: 6px 14px;
            border-radius: 4px;
        """)
        self.btn_init_case.clicked.connect(self._on_init_case_clicked)

        form_h.addWidget(lbl_case_no)
        form_h.addWidget(self.txt_case_id)
        form_h.addWidget(lbl_case_name)
        form_h.addWidget(self.txt_case_name)
        form_h.addWidget(lbl_inv)
        form_h.addWidget(self.txt_investigator)
        form_h.addWidget(self.btn_init_case)
        case_layout.addLayout(form_h)

        self.lbl_case_status = QLabel("Case DB: Not yet created.", self)
        self.lbl_case_status.setStyleSheet("color: #8B949E; font-size: 11px; font-family: Consolas;")
        case_layout.addWidget(self.lbl_case_status)
        main_layout.addWidget(grp_case)

        # Group 2: Evidence Source Selection
        grp_source = QGroupBox("2. Evidence Source Selection", self)
        grp_source.setStyleSheet(grp_case.styleSheet())
        source_layout = QVBoxLayout(grp_source)

        src_radio_h = QHBoxLayout()
        self.rb_file = QRadioButton("Disk Image File (.dd, .raw, .E01, .E03, .AFF4)", self)
        self.rb_file.setChecked(True)
        self.rb_device = QRadioButton("Physical Block Device (Drive/Disk)", self)
        self.rb_file.toggled.connect(self._on_source_type_toggled)

        src_radio_h.addWidget(self.rb_file)
        src_radio_h.addWidget(self.rb_device)
        src_radio_h.addStretch()
        source_layout.addLayout(src_radio_h)

        # File picker row
        self.file_picker_widget = QWidget(self)
        fp_layout = QHBoxLayout(self.file_picker_widget)
        fp_layout.setContentsMargins(0, 4, 0, 4)
        self.txt_file_path = QLineEdit(self)
        self.txt_file_path.setPlaceholderText("Select raw disk image or EWF split container...")
        self.btn_browse = QPushButton("Browse Image...", self)
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        fp_layout.addWidget(self.txt_file_path)
        fp_layout.addWidget(self.btn_browse)
        source_layout.addWidget(self.file_picker_widget)

        # Device selector row
        self.device_widget = QWidget(self)
        self.device_widget.setVisible(False)
        dev_layout = QHBoxLayout(self.device_widget)
        dev_layout.setContentsMargins(0, 4, 0, 4)
        self.combo_devices = QComboBox(self)
        self.btn_refresh_devs = QPushButton("Enumerate Disks", self)
        self.btn_refresh_devs.clicked.connect(self._enumerate_devices)
        dev_layout.addWidget(self.combo_devices, stretch=4)
        dev_layout.addWidget(self.btn_refresh_devs, stretch=1)
        source_layout.addWidget(self.device_widget)

        main_layout.addWidget(grp_source)

        # Group 3: Write-Block Verification
        grp_wb = QGroupBox("3. Write-Block Hardware/Software Integrity", self)
        grp_wb.setStyleSheet(grp_case.styleSheet())
        wb_layout = QVBoxLayout(grp_wb)

        wb_btn_h = QHBoxLayout()
        self.btn_verify_wb = QPushButton("Verify Read-Only Write-Block", self)
        self.btn_verify_wb.setStyleSheet(f"""
            background-color: #21262D;
            border: 1px solid {DFIR_DARK_THEME['border_color']};
            color: {DFIR_DARK_THEME['text_bright']};
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
        """)
        self.btn_verify_wb.clicked.connect(self._on_verify_wb_clicked)
        wb_btn_h.addWidget(self.btn_verify_wb)
        wb_btn_h.addStretch()
        wb_layout.addLayout(wb_btn_h)

        self.wb_banner = QLabel("Write-block status not yet verified. Verification required before acquisition.", self)
        self.wb_banner.setWordWrap(True)
        self.wb_banner.setStyleSheet("""
            background-color: #161B22;
            color: #8B949E;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #30363D;
            font-size: 11px;
        """)
        wb_layout.addWidget(self.wb_banner)
        main_layout.addWidget(grp_wb)

        # Group 4: Acquisition
        grp_acq = QGroupBox("4. Bit-Stream Acquisition & Hashing", self)
        grp_acq.setStyleSheet(grp_case.styleSheet())
        acq_layout = QVBoxLayout(grp_acq)

        self.btn_acquire = QPushButton("Begin Bit-Stream Acquisition", self)
        self.btn_acquire.setEnabled(False)  # Unlocked strictly on Write-Block PASS
        self.btn_acquire.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:disabled {
                background-color: #21262D;
                color: #484F58;
            }
            QPushButton:hover:!disabled {
                background-color: #2EA043;
            }
        """)
        self.btn_acquire.clicked.connect(self._on_acquire_clicked)
        acq_layout.addWidget(self.btn_acquire, alignment=Qt.AlignmentFlag.AlignLeft)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0D1117;
                border: 1px solid #30363D;
                border-radius: 4px;
                height: 18px;
                text-align: center;
                color: #FFFFFF;
                font-family: Consolas;
            }
            QProgressBar::chunk {
                background-color: #1F6FEB;
                border-radius: 3px;
            }
        """)
        acq_layout.addWidget(self.progress_bar)

        self.lbl_acq_status = QLabel("", self)
        self.lbl_acq_status.setStyleSheet("font-family: Consolas; font-size: 11px; color: #58A6FF;")
        acq_layout.addWidget(self.lbl_acq_status)

        main_layout.addWidget(grp_acq)
        main_layout.addStretch()

    def _on_init_case_clicked(self):
        case_id = self.txt_case_id.text().strip()
        case_name = self.txt_case_name.text().strip()
        investigator = self.txt_investigator.text().strip()

        new_id = self.session.create_case(case_id=case_id, name=case_name, investigator=investigator)
        self.txt_case_id.setText(new_id)
        self.lbl_case_status.setText(f"Case DB Initialized: {self.session.db_path}")
        self.lbl_case_status.setStyleSheet("color: #3FB950; font-size: 11px; font-family: Consolas;")

    def _on_source_type_toggled(self, is_file: bool):
        self.file_picker_widget.setVisible(is_file)
        self.device_widget.setVisible(not is_file)
        if not is_file:
            self._enumerate_devices()

    def _on_browse_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Forensic Evidence Image",
            "",
            "Forensic Images (*.dd *.raw *.E01 *.E02 *.E03 *.eo3 *.AFF4 *.img *.001);;All Files (*.*)",
        )
        if file_path:
            self.txt_file_path.setText(file_path)
            self.session.set_evidence_source(file_path)
            # Invalidate write-block until re-verified for this file
            self.session.write_block_verified = None
            self.btn_acquire.setEnabled(False)
            self.wb_banner.setText("Evidence source updated. Write-block verification required.")
            self.wb_banner.setStyleSheet("background-color: #161B22; color: #8B949E; padding: 8px 12px; border: 1px solid #30363D;")

    def _enumerate_devices(self):
        """Discovers physical block devices on Windows or Linux."""
        self.combo_devices.clear()
        devices: List[str] = []

        if sys.platform == "win32":
            try:
                cmd = ["powershell", "-NoProfile", "-Command", "Get-Disk | Select-Object -Property Number, FriendlyName, Size | ConvertTo-Csv -NoTypeInformation"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                lines = [l.strip().replace('"', '') for l in res.stdout.strip().splitlines() if l.strip()]
                for line in lines[1:]:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        num, name, sz = parts[0], parts[1], parts[2]
                        try:
                            gb = int(sz) / (1024 ** 3)
                            devices.append(f"\\\\.\\PhysicalDrive{num} — {name} ({gb:.1f} GB)")
                        except ValueError:
                            devices.append(f"\\\\.\\PhysicalDrive{num} — {name}")
            except Exception:
                pass
        else:
            # Linux lsblk
            try:
                cmd = ["lsblk", "-d", "-n", "-o", "NAME,SIZE,MODEL"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                for line in res.stdout.splitlines():
                    if line.strip():
                        parts = line.split()
                        dev_path = f"/dev/{parts[0]}"
                        devices.append(f"{dev_path} — {' '.join(parts[1:])}")
            except Exception:
                pass

        if devices:
            for d in devices:
                self.combo_devices.addItem(d)
        else:
            self.combo_devices.addItem("No physical block devices enumerated (use Image File mode)")

    def _get_current_source_path(self) -> str:
        if self.rb_file.isChecked():
            return self.txt_file_path.text().strip()
        else:
            current_text = self.combo_devices.currentText()
            if " — " in current_text:
                return current_text.split(" — ")[0].strip()
            return current_text.strip()

    def _on_verify_wb_clicked(self):
        source = self._get_current_source_path()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "Invalid Source", "Please select an existing evidence image or disk path.")
            return

        self.session.set_evidence_source(source)

        try:
            verify_read_only(source)
            self.session.set_write_block_status(True)
            self.wb_banner.setText("WRITE-BLOCKED — VERIFIED: Source handle is confirmed read-only (r+b & O_RDWR denied). Safe to acquire.")
            self.wb_banner.setStyleSheet("""
                background-color: #0D3321;
                color: #3FB950;
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid #238636;
                font-weight: bold;
            """)
            self.btn_acquire.setEnabled(True)
        except WriteBlockViolationError as e:
            self.session.set_write_block_status(False)
            self.wb_banner.setText(f"WRITE VIOLATION HARD-STOP: {e}")
            self.wb_banner.setStyleSheet("""
                background-color: #3A1D1D;
                color: #F85149;
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid #DA3633;
                font-weight: bold;
            """)
            self.btn_acquire.setEnabled(False)
        except Exception as e:
            self.session.set_write_block_status(False)
            self.wb_banner.setText(f"ERROR CHECKING SOURCE: {e}")
            self.wb_banner.setStyleSheet("background-color: #3A1D1D; color: #F85149; padding: 8px 12px; border: 1px solid #DA3633;")
            self.btn_acquire.setEnabled(False)

    def _on_acquire_clicked(self):
        source = self._get_current_source_path()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "No Source", "Selected evidence source path does not exist.")
            return

        if not self.session.has_case:
            self._on_init_case_clicked()

        # Destination file
        case_dir = os.path.dirname(self.session.db_path)
        dest_filename = os.path.basename(source)
        if not dest_filename.lower().endswith((".dd", ".raw", ".img", ".e01", ".e02", ".e03", ".eo3", ".aff4")):
            dest_filename = f"{self.session.case_id}_acquired.dd"
        dest_path = os.path.join(case_dir, dest_filename)

        # If source is already an evidence image, we can acquire directly (hash verification without redundant copy if paths match)
        if os.path.abspath(source) == os.path.abspath(dest_path):
            dest_path = source

        self.btn_acquire.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_acq_status.setText(f"Acquiring from {os.path.basename(source)}...")

        self.worker = AcquisitionWorker(
            source_path=source,
            dest_path=dest_path,
            case_id=self.session.case_id,
            db_path=self.session.db_path,
            enforce_write_block=False,
        )
        self.worker.progress_signal.connect(self._on_acq_progress)
        self.worker.finished_signal.connect(self._on_acq_finished)
        self.worker.error_signal.connect(self._on_acq_error)
        self.worker.start()

    def _on_acq_progress(self, done: int, total: int):
        if total > 0:
            pct = int((done / total) * 100)
            self.progress_bar.setValue(min(100, pct))
            mb_done = done / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.lbl_acq_status.setText(f"Processed {mb_done:.1f} MB / {mb_total:.1f} MB ({pct}%)")
        else:
            mb_done = done / (1024 * 1024)
            self.lbl_acq_status.setText(f"Processed {mb_done:.1f} MB")

    def _on_acq_finished(self, result: AcquisitionResult):
        self.progress_bar.setValue(100)
        self.lbl_acq_status.setText("Acquisition & Hash Verification complete!")
        self.session.set_acquisition_result(result)
        # Navigate to Page 2 (Acquisition Report)
        self.navigate_to_page.emit(2)

    def _on_acq_error(self, err_msg: str):
        self.progress_bar.setVisible(False)
        self.lbl_acq_status.setText(f"ACQUISITION FAILED: {err_msg}")
        self.lbl_acq_status.setStyleSheet("color: #F85149; font-size: 11px;")
        self.btn_acquire.setEnabled(True)
        QMessageBox.critical(self, "Acquisition Failure", f"Forensic acquisition failed with error:\n\n{err_msg}")
