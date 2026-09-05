"""Single-channel video widget. Renders frames streamed from engine5_playback/decoder.py."""

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.engine5_playback.decoder import StreamDecoder


class VideoTileWidget(QWidget):
    """
    Video rendering widget for a single playback channel.
    Renders decoded frames pushed directly from StreamDecoder in memory.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("No Video Stream Loaded", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background-color: #000; color: #aaa; font-size: 14px;")
        self.layout.addWidget(self.label)

        self.decoder: StreamDecoder = None
        self.current_frame_idx = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)

    def load_stream(self, stream_buffer: bytes, oem: str = "auto") -> int:
        """
        Loads and decodes a video stream buffer in memory via StreamDecoder.
        Returns total frame count.
        """
        self.timer.stop()
        self.decoder = StreamDecoder(stream_buffer, oem=oem)
        self.current_frame_idx = 0

        frame_count = self.decoder.get_frame_count()
        if frame_count > 0:
            self.render_frame_at(0)
        else:
            self.label.setText("No playable frames decoded in stream.")

        return frame_count

    def render_frame_at(self, frame_idx: int) -> bool:
        if not self.decoder:
            return False

        frame = self.decoder.read_frame(frame_idx)
        if frame is None:
            return False

        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)

        scaled_pixmap = pixmap.scaled(
            self.label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.label.setPixmap(scaled_pixmap)
        self.current_frame_idx = frame_idx
        return True

    def play(self, fps: int = 25) -> None:
        if self.decoder and self.decoder.get_frame_count() > 0:
            interval_ms = int(1000 / max(fps, 1))
            self.timer.start(interval_ms)

    def stop(self) -> None:
        self.timer.stop()

    def set_proxy_mode(self, enabled: bool, target_fps: int = 5) -> None:
        """Configures proxy decoding mode (downscaled/reduced frame rate for inactive background matrix tiles)."""
        if self.timer.isActive():
            self.play(fps=target_fps if enabled else 25)

    def _next_frame(self) -> None:
        if not self.decoder:
            self.timer.stop()
            return

        total_frames = self.decoder.get_frame_count()
        if total_frames == 0:
            self.timer.stop()
            return

        next_idx = (self.current_frame_idx + 1) % total_frames
        self.render_frame_at(next_idx)

