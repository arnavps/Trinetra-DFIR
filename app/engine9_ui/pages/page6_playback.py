"""Page 6 — Native Playback Viewer.
Multi-channel/maximized in-memory stream player powered by StreamDecoder.
Never transcodes or writes primary evidentiary files to disk.
"""

import os
import cv2
import numpy as np
from typing import Optional, List
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QFrame, QMessageBox
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine1_acquisition.image_reader import ImageReader
from app.engine5_playback.decoder import StreamDecoder
from app.engine3_parsers.fs_base import ExtractedFileEntry


class Page6Playback(QWidget):
    """
    Page 6: Native In-Memory Stream Playback.
    Renders unconverted CCTV streams frame-by-frame with OSD verification.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.decoder: Optional[StreamDecoder] = None
        self.current_frame_idx = 0
        self.total_frames = 0
        self.fps = 25

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer_tick)

        self.init_ui()

        self.session.case_changed.connect(self._on_session_changed)
        self.session.active_file_changed.connect(self._load_active_clip)
        self._on_session_changed()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(12)

        # Header Title
        title = QLabel("NATIVE STREAM PLAYBACK VIEWER", self)
        title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        self.main_layout.addWidget(title)

        self.lbl_subtitle = QLabel("Step 6: Frame-accurate in-memory decoding. Original proprietary streams are decoded without conversion or remuxing.", self)
        self.lbl_subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        self.main_layout.addWidget(self.lbl_subtitle)

        # Empty State
        self.empty_widget = EmptyStateWidget(
            icon_str="🎬",
            title="No Video Clip Selected",
            description="Select a channel clip or carved fragment from Page 4 (Filesystem Explorer) or Page 5 (Carver) to begin native playback.",
            button_text="Open Filesystem Explorer (Page 4)",
            button_callback=lambda: self.navigate_to_page.emit(4),
            parent=self,
        )
        self.main_layout.addWidget(self.empty_widget)

        # Content Player Container
        self.content_widget = QWidget(self)
        self.content_widget.setVisible(False)
        content_v = QVBoxLayout(self.content_widget)
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(10)

        # OSD Stream Banner
        self.lbl_osd_banner = QLabel("", self)
        self.lbl_osd_banner.setStyleSheet("""
            background-color: #161B22;
            color: #3FB950;
            font-family: Consolas;
            font-size: 12px;
            font-weight: bold;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #238636;
        """)
        content_v.addWidget(self.lbl_osd_banner)

        # Video Canvas
        self.video_frame_lbl = QLabel(self)
        self.video_frame_lbl.setMinimumSize(640, 360)
        self.video_frame_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_frame_lbl.setStyleSheet("""
            background-color: #05070A;
            border: 1px solid #30363D;
            border-radius: 6px;
        """)
        content_v.addWidget(self.video_frame_lbl, stretch=1)

        # Scrubber Slider & Timestamp
        slider_h = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self._on_slider_moved)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #30363D;
                height: 6px;
                background: #161B22;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #1F6FEB;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #58A6FF;
                border: 1px solid #58A6FF;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
        """)
        slider_h.addWidget(self.slider)

        self.lbl_frame_counter = QLabel("0 / 0", self)
        self.lbl_frame_counter.setStyleSheet("font-family: Consolas; font-size: 11px; color: #58A6FF; min-width: 90px;")
        slider_h.addWidget(self.lbl_frame_counter)
        content_v.addLayout(slider_h)

        # Control Buttons Row
        ctrl_h = QHBoxLayout()
        self.btn_step_back = QPushButton("◀ Step -1", self)
        self.btn_step_back.clicked.connect(self._step_back)
        ctrl_h.addWidget(self.btn_step_back)

        self.btn_play = QPushButton("▶ Play", self)
        self.btn_play.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['accent_blue']};
            color: #FFFFFF;
            font-weight: bold;
            padding: 6px 18px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_play.clicked.connect(self._toggle_play)
        ctrl_h.addWidget(self.btn_play)

        self.btn_step_fwd = QPushButton("Step +1 ▶", self)
        self.btn_step_fwd.clicked.connect(self._step_fwd)
        ctrl_h.addWidget(self.btn_step_fwd)

        ctrl_h.addStretch()

        # Dedicated Trigger: The ONLY way AI analysis is initiated
        self.btn_run_ai = QPushButton("⚡ Run Live AI Triage on this Clip →", self)
        self.btn_run_ai.setStyleSheet("""
            QPushButton {
                background-color: #A371F7;
                color: #0D1117;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #BC8CFF;
            }
        """)
        self.btn_run_ai.clicked.connect(self._open_ai_triage)
        ctrl_h.addWidget(self.btn_run_ai)

        content_v.addLayout(ctrl_h)
        self.main_layout.addWidget(self.content_widget)

    def _on_session_changed(self):
        if not self.session.active_file_entry:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
            self.timer.stop()
        else:
            self._load_active_clip(self.session.active_file_entry)

    def _load_active_clip(self, entry: Optional[ExtractedFileEntry]):
        if not entry or not self.session.has_evidence:
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
            self.timer.stop()
            return

        self.timer.stop()
        self.btn_play.setText("▶ Play")

        # Read clip stream bytes directly from ImageReader
        try:
            with ImageReader(self.session.image_path) as reader:
                if entry.cluster_runs:
                    start_sec = entry.cluster_runs[0].start_sector
                    sec_cnt = entry.cluster_runs[0].sector_count
                    reader.seek(start_sec * 512)
                    stream_bytes = reader.read(sec_cnt * 512)
                else:
                    reader.seek(0)
                    stream_bytes = reader.read(min(entry.size_bytes, 10 * 1024 * 1024))

            oem_desc = self.session.virtual_file_system.oem if self.session.virtual_file_system else "auto"
            self.decoder = StreamDecoder(stream_bytes, oem=oem_desc, max_frames=None)
            self.total_frames = self.decoder.get_frame_count()

            is_h265 = b"H265" in stream_bytes[:4096] or b"\x40\x01" in stream_bytes[:2048]
            codec_str = "H.265 / HEVC" if is_h265 else "H.264 / AVC"
            self.fps = 15 if is_h265 else 25

            self.lbl_osd_banner.setText(
                f"CLIP: {entry.file_id} | Channel {entry.channel_id} | {codec_str} | "
                f"Original format — not converted (In-Memory Ephemeral Decode)"
            )

            self.slider.setRange(0, max(0, self.total_frames - 1))
            self.current_frame_idx = 0
            self.slider.setValue(0)

            self.empty_widget.setVisible(False)
            self.content_widget.setVisible(True)

            if self.total_frames > 0:
                self._render_frame(0)
            else:
                self._render_blank("No decodable frames found in stream")
        except Exception as e:
            QMessageBox.warning(self, "Decode Error", f"Failed to decode stream for {entry.file_id}:\n\n{e}")

    def _render_frame(self, idx: int):
        if not self.decoder or self.total_frames == 0:
            return

        frame = self.decoder.read_frame(idx)
        if frame is None:
            return

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img)

        target_sz = self.video_frame_lbl.size()
        scaled = pix.scaled(target_sz, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.video_frame_lbl.setPixmap(scaled)

        self.current_frame_idx = idx
        self.slider.blockSignals(True)
        self.slider.setValue(idx)
        self.slider.blockSignals(False)

        sec = idx / max(1, self.fps)
        self.lbl_frame_counter.setText(f"{idx + 1} / {self.total_frames} ({sec:.1f}s)")

    def _render_blank(self, msg: str):
        img = np.zeros((360, 640, 3), dtype=np.uint8)
        img[:] = (15, 18, 22)
        cv2.putText(img, msg, (40, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1, cv2.LINE_AA)
        q_img = QImage(img.data, 640, 360, 3 * 640, QImage.Format.Format_RGB888)
        self.video_frame_lbl.setPixmap(QPixmap.fromImage(q_img))

    def _toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_play.setText("▶ Play")
        else:
            if self.total_frames > 0:
                interval_ms = int(1000 / self.fps)
                self.timer.start(interval_ms)
                self.btn_play.setText("⏸ Pause")

    def _on_timer_tick(self):
        if self.total_frames == 0:
            self.timer.stop()
            return
        next_idx = (self.current_frame_idx + 1) % self.total_frames
        self._render_frame(next_idx)

    def _on_slider_moved(self, val: int):
        self._render_frame(val)

    def _step_back(self):
        if self.total_frames > 0:
            idx = max(0, self.current_frame_idx - 1)
            self._render_frame(idx)

    def _step_fwd(self):
        if self.total_frames > 0:
            idx = min(self.total_frames - 1, self.current_frame_idx + 1)
            self._render_frame(idx)

    def _open_ai_triage(self):
        self.timer.stop()
        self.btn_play.setText("▶ Play")
        self.navigate_to_page.emit(8)
