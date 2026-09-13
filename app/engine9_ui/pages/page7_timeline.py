"""Page 7 — Timeline Normalization.
Combines OSD timestamps and visual anchor change-points into unified clock synchronization.
Honest fallback when no visual anchor exists.
"""

from typing import Optional, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine1_acquisition.image_reader import ImageReader
from app.engine5_playback.decoder import StreamDecoder
from app.engine6_timeline.normalizer import TimelineNormalizer
from app.engine6_timeline.osd_extractor import extract_osd_timestamp


class Page7Timeline(QWidget):
    """
    Page 7: Per-Channel Clock Calibration & Visual Anchor Normalization.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.normalization_result = None
        self.init_ui()

        self.session.case_changed.connect(self._on_session_changed)
        self._on_session_changed()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(14)

        # Header Title
        title = QLabel("TIMELINE SYNCHRONIZATION & NORMALIZATION", self)
        title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        self.main_layout.addWidget(title)

        subtitle = QLabel("Step 7: Reconcile clock drift using OSD timecodes and visual anchor change-points.", self)
        subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        self.main_layout.addWidget(subtitle)

        # Empty State
        self.empty_widget = EmptyStateWidget(
            icon_str="⏱️",
            title="No Video Footage Selected",
            description="Select a video clip from Page 4 (Explorer) or Page 6 (Playback) to inspect timecode extraction and anchor normalization.",
            button_text="Select Clip in Explorer (Page 4)",
            button_callback=lambda: self.navigate_to_page.emit(4),
            parent=self,
        )
        self.main_layout.addWidget(self.empty_widget)

        # Content Widget
        self.content_widget = QWidget(self)
        self.content_widget.setVisible(False)
        content_v = QVBoxLayout(self.content_widget)
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(10)

        # Action bar
        act_h = QHBoxLayout()
        self.btn_run_norm = QPushButton("Run Timeline Normalization", self)
        self.btn_run_norm.setStyleSheet("""
            background-color: #238636;
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_run_norm.clicked.connect(self._run_normalization)
        act_h.addWidget(self.btn_run_norm)
        act_h.addStretch()
        content_v.addLayout(act_h)

        # Mode & Drift Banner
        self.lbl_mode_banner = QLabel("", self)
        self.lbl_mode_banner.setWordWrap(True)
        self.lbl_mode_banner.setStyleSheet("""
            background-color: #161B22;
            color: #58A6FF;
            font-family: Consolas;
            font-size: 12px;
            padding: 10px 14px;
            border-radius: 4px;
            border: 1px solid #30363D;
        """)
        content_v.addWidget(self.lbl_mode_banner)

        # Normalization Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Frame Index", "Extracted OSD Timestamp", "Normalized Case Timestamp", "Anchor Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
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

    def _on_session_changed(self):
        if not self.session.active_file_entry:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
        else:
            self.empty_widget.setVisible(False)
            self.content_widget.setVisible(True)
            if self.normalization_result is None:
                entry = self.session.active_file_entry
                self.lbl_mode_banner.setText(f"Active Clip: {entry.file_id} (Channel {entry.channel_id}). Click 'Run Timeline Normalization' to calculate clock alignment.")

    def _run_normalization(self):
        entry = self.session.active_file_entry
        if not entry or not self.session.has_evidence:
            return

        # Decode sample frames from stream
        try:
            with ImageReader(self.session.image_path) as reader:
                if entry.cluster_runs:
                    start_sec = entry.cluster_runs[0].start_sector
                    sec_cnt = entry.cluster_runs[0].sector_count
                    reader.seek(start_sec * 512)
                    stream_bytes = reader.read(sec_cnt * 512)
                else:
                    reader.seek(0)
                    stream_bytes = reader.read(min(entry.size_bytes, 2 * 1024 * 1024))

            decoder = StreamDecoder(stream_bytes, max_frames=40)
            frames = [decoder.read_frame(i) for i in range(decoder.get_frame_count())]

            # Extract raw OSD timestamps
            raw_osd = [extract_osd_timestamp(f) for f in frames if f is not None]
            if not any(raw_osd) and entry.start_timestamp:
                raw_osd = [entry.start_timestamp] * len(frames)

            normalizer = TimelineNormalizer(fps=25.0)
            res = normalizer.normalize_channel_clock(raw_osd, frames=frames)
            self.normalization_result = res
            self.session.timeline_normalization = res

            mode = res.get("mode", "osd_only")
            clock_offset = res.get("clock_offset_seconds", 0.0)
            anchors = res.get("anchors_found", [])

            if mode == "osd_only" or not anchors:
                self.lbl_mode_banner.setText(
                    f"MODE: OSD-ONLY (Offset: {clock_offset:+.2f}s)\n"
                    f"Notice: No usable visual anchor found in this footage — using on-screen timestamps only."
                )
                self.lbl_mode_banner.setStyleSheet("""
                    background-color: #3A2404;
                    color: #F0883E;
                    font-family: Consolas;
                    font-size: 12px;
                    padding: 10px 14px;
                    border-radius: 4px;
                    border: 1px solid #9E6A03;
                """)
            else:
                self.lbl_mode_banner.setText(
                    f"MODE: VISUAL ANCHOR SYNCHRONIZED ({len(anchors)} anchor change-points detected)\n"
                    f"Calculated Clock Drift Offset: {clock_offset:+.3f} seconds across camera channels."
                )
                self.lbl_mode_banner.setStyleSheet("""
                    background-color: #0D3321;
                    color: #3FB950;
                    font-family: Consolas;
                    font-size: 12px;
                    padding: 10px 14px;
                    border-radius: 4px;
                    border: 1px solid #238636;
                """)

            norm_stamps = res.get("normalized_timestamps", [])
            self.table.setRowCount(len(norm_stamps))

            for row, n_ts in enumerate(norm_stamps):
                item_idx = QTableWidgetItem(str(row))
                item_raw = QTableWidgetItem(raw_osd[row] if row < len(raw_osd) and raw_osd[row] else "N/A")
                item_norm = QTableWidgetItem(n_ts)

                is_anchor = row in anchors
                anchor_str = "VISUAL ANCHOR" if is_anchor else "Standard"
                item_anc = QTableWidgetItem(anchor_str)
                if is_anchor:
                    item_anc.setForeground(Qt.GlobalColor.cyan)

                self.table.setItem(row, 0, item_idx)
                self.table.setItem(row, 1, item_raw)
                self.table.setItem(row, 2, item_norm)
                self.table.setItem(row, 3, item_anc)

        except Exception as e:
            self.lbl_mode_banner.setText(f"Timeline normalization error: {e}")
