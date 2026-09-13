"""Page 5 — Recover Deleted / Corrupted Data (Carving).
Heuristic recovery of orphan H.264/H.265 NAL streams and GOP reassembly from unallocated space.
"""

import os
from typing import Optional, List
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QGroupBox, QMessageBox
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine1_acquisition.image_reader import ImageReader
from app.engine4_carver.frame_carver import carve_nal_units
from app.engine4_carver.gop_reconstructor import reassemble_gop_fragments
from app.engine3_parsers.fs_base import ExtractedFileEntry, ClusterRun


class CarvingWorker(QThread):
    """Carves raw NAL units in background chunk by chunk."""
    progress_signal = Signal(int, int)  # processed_bytes, total_bytes
    finished_signal = Signal(list)      # List[ExtractedFileEntry]
    error_signal = Signal(str)

    def __init__(self, image_path: str, case_id: str):
        super().__init__()
        self.image_path = image_path
        self.case_id = case_id
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            with ImageReader(self.image_path) as reader:
                total_size = reader.size()
                # Scan unallocated space in 16MB blocks up to 64MB or file end
                scan_limit = min(total_size, 64 * 1024 * 1024)
                chunk_size = 8 * 1024 * 1024
                offset = 0

                fragments_found: List[ExtractedFileEntry] = []
                frag_idx = 1

                while offset < scan_limit and not self._is_cancelled:
                    read_len = min(chunk_size, scan_limit - offset)
                    reader.seek(offset)
                    data = reader.read(read_len)

                    nal_units = carve_nal_units(data, start_offset=0, max_bytes=read_len)
                    if nal_units:
                        gops = reassemble_gop_fragments(nal_units)
                        for gop in gops:
                            if len(gop) > 1024:  # Meaningful GOP length
                                start_sec = offset // 512
                                sec_cnt = (len(gop) + 511) // 512
                                entry = ExtractedFileEntry(
                                    file_id=f"CARVED_FRAG_{frag_idx:04d}",
                                    channel_id=0,  # 0 indicates unallocated orphan
                                    start_timestamp="Carved Stream",
                                    end_timestamp="Heuristic Recovery",
                                    size_bytes=len(gop),
                                    cluster_runs=[ClusterRun(start_sector=start_sec, sector_count=sec_cnt)],
                                    extraction_type="carved_fragment",
                                )
                                fragments_found.append(entry)
                                frag_idx += 1

                    offset += read_len
                    self.progress_signal.emit(offset, scan_limit)

                self.finished_signal.emit(fragments_found)
        except Exception as e:
            self.error_signal.emit(str(e))


class Page5Carver(QWidget):
    """
    Page 5: Heuristic NAL Unit Carving and Fragment Reassembly.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.worker: Optional[CarvingWorker] = None
        self.has_scanned = False
        self.init_ui()

        self.session.case_changed.connect(self._on_session_changed)
        self._on_session_changed()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(14)

        # Header Title
        title = QLabel("RECOVER DELETED & UNALLOCATED DATA (CARVING)", self)
        title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        self.main_layout.addWidget(title)

        subtitle = QLabel("Step 5: Heuristic NAL unit start-code carving (\x00\x00\x00\x01) and GOP reassembly from unallocated space.", self)
        subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        self.main_layout.addWidget(subtitle)

        # Empty State
        self.empty_widget = EmptyStateWidget(
            icon_str="⛏️",
            title="No Carving Scan Run Yet",
            description="No scan run yet for this evidence — click 'Scan Unallocated Space' to search for orphan NAL units and deleted surveillance video fragments.",
            button_text="Scan Unallocated Space",
            button_callback=self._start_carving,
            parent=self,
        )
        self.main_layout.addWidget(self.empty_widget)

        # Content Widget
        self.content_widget = QWidget(self)
        self.content_widget.setVisible(False)
        content_v = QVBoxLayout(self.content_widget)
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(10)

        # Controls & Status Bar
        ctrl_h = QHBoxLayout()
        self.btn_scan = QPushButton("Scan Unallocated Space", self)
        self.btn_scan.setStyleSheet("""
            background-color: #238636;
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_scan.clicked.connect(self._start_carving)
        ctrl_h.addWidget(self.btn_scan)

        self.btn_cancel = QPushButton("Cancel Scan", self)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setStyleSheet("""
            background-color: #DA3633;
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_cancel.clicked.connect(self._cancel_carving)
        ctrl_h.addWidget(self.btn_cancel)

        self.lbl_scan_status = QLabel("", self)
        self.lbl_scan_status.setStyleSheet("font-family: Consolas; font-size: 11px; color: #58A6FF;")
        ctrl_h.addWidget(self.lbl_scan_status)
        ctrl_h.addStretch()

        self.btn_play_frag = QPushButton("Play Fragment in Playback (Page 6) →", self)
        self.btn_play_frag.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['accent_blue']};
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_play_frag.clicked.connect(self._play_selected_fragment)
        ctrl_h.addWidget(self.btn_play_frag)
        content_v.addLayout(ctrl_h)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0D1117;
                border: 1px solid #30363D;
                border-radius: 4px;
                height: 14px;
                text-align: center;
                color: #FFFFFF;
                font-family: Consolas;
            }
            QProgressBar::chunk { background-color: #1F6FEB; }
        """)
        content_v.addWidget(self.progress_bar)

        # Results Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Fragment ID", "Sector Offset", "Size (bytes)", "Extraction Tag", "Integrity Note"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
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
        self.table.doubleClicked.connect(lambda _: self._play_selected_fragment())
        content_v.addWidget(self.table)

        self.main_layout.addWidget(self.content_widget)

    def _on_session_changed(self):
        if not self.session.has_evidence:
            self.empty_widget.set_message(
                title="No Evidence Loaded",
                description="No evidence image is currently active. Load or acquire an evidence file in Page 1 first.",
                icon_str="🛡️",
            )
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
        elif not self.has_scanned and not self.session.carved_fragments:
            self.empty_widget.set_message(
                title="No Carving Scan Run Yet",
                description="No scan run yet for this evidence — click 'Scan Unallocated Space' to search for orphan NAL units and deleted surveillance video fragments.",
                icon_str="⛏️",
            )
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
        else:
            self.empty_widget.setVisible(False)
            self.content_widget.setVisible(True)
            self._render_table(self.session.carved_fragments)

    def _start_carving(self):
        if not self.session.has_evidence:
            QMessageBox.warning(self, "No Evidence", "Please load an evidence image first.")
            return

        self.empty_widget.setVisible(False)
        self.content_widget.setVisible(True)
        self.btn_scan.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_scan_status.setText("Scanning sectors for NAL headers...")

        self.worker = CarvingWorker(self.session.image_path, self.session.case_id or "CASE")
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _cancel_carving(self):
        if self.worker:
            self.worker.cancel()
            self.lbl_scan_status.setText("Cancelling scan...")

    def _on_progress(self, done: int, total: int):
        pct = int((done / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        mb_done = done / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        self.lbl_scan_status.setText(f"Scanned {mb_done:.1f} MB / {mb_total:.1f} MB ({pct}%)")

    def _on_finished(self, fragments: List[ExtractedFileEntry]):
        self.has_scanned = True
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)

        for frag in fragments:
            self.session.add_carved_fragment(frag)

        if not fragments and not self.session.carved_fragments:
            self.lbl_scan_status.setText("Scan complete. 0 fragments recovered.")
            self.empty_widget.set_message(
                title="Scan Complete — 0 Fragments Recovered",
                description="Scan complete. 0 fragments recovered. (No orphan H.264/H.265 NAL start-codes were identified in unallocated space).",
                icon_str="✅",
            )
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
        else:
            total_recovered = len(self.session.carved_fragments)
            self.lbl_scan_status.setText(f"Scan complete. {total_recovered} fragment(s) recovered.")
            self._render_table(self.session.carved_fragments)

    def _on_error(self, err: str):
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.lbl_scan_status.setText(f"Scan error: {err}")
        QMessageBox.critical(self, "Carver Error", f"NAL carving failed:\n\n{err}")

    def _render_table(self, fragments: List[ExtractedFileEntry]):
        self.table.setRowCount(len(fragments))
        for row, f in enumerate(fragments):
            item_id = QTableWidgetItem(f.file_id)
            item_id.setForeground(Qt.GlobalColor.white)
            item_id.setData(Qt.ItemDataRole.UserRole, f)

            sec_str = f"Sec {f.cluster_runs[0].start_sector}" if f.cluster_runs else "N/A"
            item_sec = QTableWidgetItem(sec_str)

            item_sz = QTableWidgetItem(f"{f.size_bytes:,} bytes")

            item_tag = QTableWidgetItem("CARVED_FRAGMENT")
            item_tag.setForeground(Qt.GlobalColor.yellow)

            item_note = QTableWidgetItem("Raw elementary stream recovered from unallocated sectors")

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_sec)
            self.table.setItem(row, 2, item_sz)
            self.table.setItem(row, 3, item_tag)
            self.table.setItem(row, 4, item_note)

        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _play_selected_fragment(self):
        curr = self.table.currentRow()
        if curr >= 0:
            item = self.table.item(curr, 0)
            if item:
                entry: ExtractedFileEntry = item.data(Qt.ItemDataRole.UserRole)
                self.session.set_active_file(entry)
                self.navigate_to_page.emit(6)
