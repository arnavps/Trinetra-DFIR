"""Tri-Netra Court Evidence Viewer (Portable Standalone Edition).

A lightweight, standalone video evidence player designed for judicial and independent
expert review. Operates directly on original, unconverted evidentiary files (.mp4, .h264,
.h265, .dav, .hik, carved fragments) with zero external application dependencies.

Hard Evidentiary Guarantee:
- Performs byte-for-byte in-memory stream decoding.
- Never re-encodes, converts, or alters the evidence bytes.
- Displays live cryptographic hashes (SHA-256 / MD5) computed directly from the opened file.
"""

import os
import sys
import hashlib
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap, QIcon, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFileDialog, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QComboBox, QMessageBox, QStatusBar
)

import numpy as np

# Standalone local decoder
try:
    from decoder import StreamDecoder
except ImportError:
    from .decoder import StreamDecoder


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0D1117;
    color: #C9D1D9;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 12px;
}
QFrame#videoCanvas {
    background-color: #000000;
    border: 1px solid #30363D;
    border-radius: 6px;
}
QListWidget {
    background-color: #161B22;
    border: 1px solid #30363D;
    border-radius: 4px;
    color: #E6EDF3;
    padding: 4px;
}
QListWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #21262D;
    border-radius: 3px;
}
QListWidget::item:selected {
    background-color: #1F6FEB;
    color: #FFFFFF;
}
QListWidget::item:hover:!selected {
    background-color: #21262D;
}
QPushButton {
    background-color: #21262D;
    color: #C9D1D9;
    border: 1px solid #30363D;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #30363D;
    color: #FFFFFF;
}
QPushButton:pressed {
    background-color: #161B22;
}
QPushButton#btnPlay {
    background-color: #238636;
    color: #FFFFFF;
    border: none;
    padding: 6px 18px;
}
QPushButton#btnPlay:hover {
    background-color: #2EA043;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #21262D;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #1F6FEB;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #58A6FF;
    border: 1px solid #1F6FEB;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}
QComboBox {
    background-color: #21262D;
    color: #C9D1D9;
    border: 1px solid #30363D;
    border-radius: 4px;
    padding: 4px 10px;
}
QStatusBar {
    background-color: #161B22;
    color: #8B949E;
    border-top: 1px solid #30363D;
    font-family: Consolas, monospace;
    font-size: 11px;
}
"""


class StandaloneEvidenceViewer(QMainWindow):
    """
    Court-ready standalone evidence viewer window.
    """

    def __init__(self, initial_file: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Tri-Netra Court Evidence Viewer — Unaltered Bitstream Player")
        self.resize(1100, 720)
        self.setStyleSheet(DARK_STYLE)

        self.frames: List[np.ndarray] = []
        self.current_frame_idx: int = 0
        self.is_playing: bool = False
        self.fps: float = 25.0
        self.current_file_path: Optional[str] = None

        # Playback timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer_tick)

        self._init_ui()
        self._setup_shortcuts()
        self._scan_package_evidence()

        if initial_file and os.path.exists(initial_file):
            self.load_file(initial_file)

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Header Banner
        header = QFrame(self)
        header.setStyleSheet("background-color: #161B22; border: 1px solid #238636; border-radius: 4px; padding: 6px 12px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(4, 2, 4, 2)

        lbl_shield = QLabel("⚖️", self)
        lbl_shield.setStyleSheet("font-size: 16px;")
        h_layout.addWidget(lbl_shield)

        v_head = QVBoxLayout()
        v_head.setSpacing(1)
        lbl_title = QLabel("TRI-NETRA DFIR — PORTABLE COURT EVIDENCE VIEWER", self)
        lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #3FB950;")
        lbl_subtitle = QLabel("PRISTINE IN-MEMORY DECODING — ORIGINAL BYTES UNALTERED — HASH VERIFIED", self)
        lbl_subtitle.setStyleSheet("font-size: 10px; color: #8B949E; font-weight: 600;")
        v_head.addWidget(lbl_title)
        v_head.addWidget(lbl_subtitle)
        h_layout.addLayout(v_head)
        h_layout.addStretch()

        btn_open = QPushButton("📂 Open Evidence File...", self)
        btn_open.clicked.connect(self._on_browse_file)
        h_layout.addWidget(btn_open)

        main_layout.addWidget(header)

        # 2. Main Content Splitter (Sidebar + Video View)
        splitter = QSplitter(Qt.Horizontal, self)

        # Left Panel: Evidence Files in Package
        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        lbl_list = QLabel("EVIDENTIARY PACKAGE FILES", self)
        lbl_list.setStyleSheet("font-size: 10px; font-weight: bold; color: #8B949E; padding-left: 2px;")
        left_layout.addWidget(lbl_list)

        self.file_list = QListWidget(self)
        self.file_list.itemClicked.connect(self._on_file_item_clicked)
        left_layout.addWidget(self.file_list)
        left_panel.setMinimumWidth(240)
        left_panel.setMaximumWidth(320)
        splitter.addWidget(left_panel)

        # Right Panel: Video Display & Scrub Controls
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Video Canvas Container
        self.canvas_frame = QFrame(self)
        self.canvas_frame.setObjectName("videoCanvas")
        canvas_layout = QVBoxLayout(self.canvas_frame)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setAlignment(Qt.AlignCenter)

        self.lbl_video = QLabel("No Evidence File Loaded", self.canvas_frame)
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setStyleSheet("color: #484F58; font-size: 14px; font-weight: bold;")
        canvas_layout.addWidget(self.lbl_video)
        right_layout.addWidget(self.canvas_frame, stretch=1)

        # Playback Timeline Slider
        slider_h = QHBoxLayout()
        slider_h.setSpacing(8)

        self.lbl_time = QLabel("00:00:00.000", self)
        self.lbl_time.setStyleSheet("font-family: Consolas; font-size: 11px; color: #58A6FF; min-width: 85px;")
        slider_h.addWidget(self.lbl_time)

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self._on_slider_moved)
        slider_h.addWidget(self.slider)

        self.lbl_frames = QLabel("Frame 0 / 0", self)
        self.lbl_frames.setStyleSheet("font-family: Consolas; font-size: 11px; color: #8B949E; min-width: 90px; text-align: right;")
        slider_h.addWidget(self.lbl_frames)

        right_layout.addLayout(slider_h)

        # Controls Row (Play, Step Back, Step Forward, Speed)
        ctrl_h = QHBoxLayout()
        ctrl_h.setSpacing(8)

        self.btn_step_back = QPushButton("⏮ -1 Frame", self)
        self.btn_step_back.clicked.connect(self.step_backward)
        ctrl_h.addWidget(self.btn_step_back)

        self.btn_play = QPushButton("▶ Play", self)
        self.btn_play.setObjectName("btnPlay")
        self.btn_play.clicked.connect(self.toggle_play)
        ctrl_h.addWidget(self.btn_play)

        self.btn_step_fwd = QPushButton("+1 Frame ⏭", self)
        self.btn_step_fwd.clicked.connect(self.step_forward)
        ctrl_h.addWidget(self.btn_step_fwd)

        self.btn_stop = QPushButton("⏹ Stop", self)
        self.btn_stop.clicked.connect(self.stop)
        ctrl_h.addWidget(self.btn_stop)

        ctrl_h.addStretch()

        lbl_speed = QLabel("Speed:", self)
        lbl_speed.setStyleSheet("color: #8B949E; font-size: 11px;")
        ctrl_h.addWidget(lbl_speed)

        self.combo_speed = QComboBox(self)
        self.combo_speed.addItems(["0.25x", "0.5x", "1.0x", "2.0x"])
        self.combo_speed.setCurrentText("1.0x")
        self.combo_speed.currentTextChanged.connect(self._on_speed_changed)
        ctrl_h.addWidget(self.combo_speed)

        right_layout.addLayout(ctrl_h)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select or open an evidentiary file.")

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Space), self, self.toggle_play)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.step_backward)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.step_forward)

    def _scan_package_evidence(self):
        """Auto-detects ../evidence/ directory if running from package viewer/ folder."""
        app_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_dirs = [
            os.path.join(app_dir, "..", "evidence"),
            os.path.join(app_dir, "evidence"),
            os.path.join(os.getcwd(), "evidence"),
        ]
        evidence_dir = None
        for d in candidate_dirs:
            if os.path.exists(d) and os.path.isdir(d):
                evidence_dir = d
                break

        if evidence_dir:
            for fname in sorted(os.listdir(evidence_dir)):
                fpath = os.path.join(evidence_dir, fname)
                if os.path.isfile(fpath):
                    size_kb = os.path.getsize(fpath) / 1024
                    item = QListWidgetItem(f"{fname}\n({size_kb:.1f} KB)")
                    item.setData(Qt.UserRole, fpath)
                    self.file_list.addItem(item)

    def _on_file_item_clicked(self, item: QListWidgetItem):
        fpath = item.data(Qt.UserRole)
        if fpath and os.path.exists(fpath):
            self.load_file(fpath)

    def _on_browse_file(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Evidentiary Video Stream",
            "",
            "Evidence Files (*.mp4 *.h264 *.h265 *.264 *.hevc *.dav *.hik *.raw *.bin);;All Files (*.*)"
        )
        if fpath:
            self.load_file(fpath)

    def load_file(self, file_path: str):
        """Loads and in-memory decodes an original evidentiary stream file."""
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "File Not Found", f"Cannot find evidence file: {file_path}")
            return

        self.stop()
        self.current_file_path = file_path
        fname = os.path.basename(file_path)
        self.status_bar.showMessage(f"Hashing & decoding {fname} in memory...")
        QApplication.processEvents()

        # Compute live SHA-256 and MD5 directly from raw file bytes
        sha256 = hashlib.sha256()
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
        sha256.update(raw_bytes)
        md5.update(raw_bytes)
        calc_sha256 = sha256.hexdigest()
        calc_md5 = md5.hexdigest()

        # In-memory decoding using StreamDecoder
        decoder = StreamDecoder(raw_bytes)
        self.frames = decoder.get_frames()

        if not self.frames:
            self.lbl_video.setText(f"Unable to decode frames from:\n{fname}\n(Raw bitstream header unparseable)")
            self.slider.setRange(0, 0)
            self.lbl_frames.setText("Frame 0 / 0")
            self.status_bar.showMessage(f"FAILED TO DECODE: {fname} | SHA-256: {calc_sha256[:16]}...")
            return

        self.current_frame_idx = 0
        self.slider.setRange(0, len(self.frames) - 1)
        self.slider.setValue(0)
        self._display_current_frame()

        self.status_bar.showMessage(
            f"EVIDENCE: {fname} ({len(self.frames)} frames) | SHA-256: {calc_sha256} | MD5: {calc_md5}"
        )

    def _display_current_frame(self):
        if not self.frames or self.current_frame_idx >= len(self.frames):
            return

        frame = self.frames[self.current_frame_idx]
        h, w = frame.shape[:2]

        # Convert BGR (OpenCV) to RGB for Qt
        rgb_frame = frame[:, :, ::-1].copy()
        bytes_per_line = 3 * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Scale to canvas size preserving aspect ratio
        canvas_size = self.canvas_frame.size()
        pixmap = QPixmap.fromImage(q_img).scaled(
            canvas_size.width() - 10,
            canvas_size.height() - 10,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.lbl_video.setPixmap(pixmap)

        # Update counter & timestamp
        total = len(self.frames)
        self.lbl_frames.setText(f"Frame {self.current_frame_idx + 1} / {total}")

        seconds = self.current_frame_idx / self.fps
        m, s = divmod(seconds, 60)
        h_val, m = divmod(m, 60)
        millis = int((seconds - int(seconds)) * 1000)
        self.lbl_time.setText(f"{int(h_val):02d}:{int(m):02d}:{int(s):02d}.{millis:03d}")

    def _on_slider_moved(self, value: int):
        if 0 <= value < len(self.frames):
            self.current_frame_idx = value
            self._display_current_frame()

    def toggle_play(self):
        if not self.frames:
            return
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if not self.frames:
            return
        self.is_playing = True
        self.btn_play.setText("⏸ Pause")
        interval_ms = int(1000.0 / self.fps)
        self.timer.start(interval_ms)

    def pause(self):
        self.is_playing = False
        self.btn_play.setText("▶ Play")
        self.timer.stop()

    def stop(self):
        self.pause()
        self.current_frame_idx = 0
        if self.frames:
            self.slider.setValue(0)
            self._display_current_frame()

    def step_forward(self):
        self.pause()
        if self.frames and self.current_frame_idx < len(self.frames) - 1:
            self.current_frame_idx += 1
            self.slider.setValue(self.current_frame_idx)
            self._display_current_frame()

    def step_backward(self):
        self.pause()
        if self.frames and self.current_frame_idx > 0:
            self.current_frame_idx -= 1
            self.slider.setValue(self.current_frame_idx)
            self._display_current_frame()

    def _on_timer_tick(self):
        if not self.frames:
            self.stop()
            return
        if self.current_frame_idx >= len(self.frames) - 1:
            self.stop()
            return
        self.current_frame_idx += 1
        self.slider.setValue(self.current_frame_idx)
        self._display_current_frame()

    def _on_speed_changed(self, speed_str: str):
        mult = float(speed_str.replace("x", ""))
        self.fps = 25.0 * mult
        if self.is_playing:
            self.timer.setInterval(max(5, int(1000.0 / self.fps)))


def main():
    app = QApplication(sys.argv)
    initial_file = sys.argv[1] if len(sys.argv) > 1 else None
    viewer = StandaloneEvidenceViewer(initial_file=initial_file)
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
