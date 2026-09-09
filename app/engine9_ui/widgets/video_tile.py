"""Single-channel video widget. Renders frames streamed from engine5_playback/decoder.py or OpenCV video files with green monospace OSD & AI bounding box overlays."""

import os
import cv2
import numpy as np
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.engine5_playback.decoder import StreamDecoder


class VideoTileWidget(QWidget):
    """
    Video rendering widget for a single playback channel.
    Renders decoded frames pushed directly from StreamDecoder in memory or OpenCV video file
    with green monospace OSD camera tags and cyan AI detection bounding box overlays.
    """

    def __init__(self, parent: QWidget = None, channel_name: str = "CAM 01 - MAIN GATE"):
        super().__init__(parent)
        self.channel_name = channel_name
        self.osd_text = f"{self.channel_name} | 2023-11-14 18:42:11.042 | 25.0 FPS | H.264 Main@L4.1"
        self.bounding_boxes: List[Dict[str, Any]] = []

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background-color: #06090E; color: #3FB950; font-family: Consolas, monospace; font-size: 11px;")
        self.layout.addWidget(self.label)

        self.decoder: Optional[StreamDecoder] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_file_path: Optional[str] = None
        self.current_frame_idx = 0
        self.total_file_frames = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)

    def set_osd_text(self, text: str) -> None:
        self.osd_text = text

    def set_bounding_boxes(self, boxes: List[Dict[str, Any]]) -> None:
        self.bounding_boxes = boxes

    def load_file(self, file_path: str) -> bool:
        """Loads a video clip directly from local disk via OpenCV VideoCapture."""
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

        if not os.path.exists(file_path):
            self._render_placeholder()
            return False

        self.cap = cv2.VideoCapture(file_path)
        if not self.cap.isOpened():
            self._render_placeholder()
            return False

        self.video_file_path = file_path
        self.total_file_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame_idx = 0
        self.render_frame_at(0)
        return True

    def load_stream(self, stream_buffer: bytes, oem: str = "auto") -> int:
        """Loads a raw stream buffer via StreamDecoder."""
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

        self.decoder = StreamDecoder(stream_buffer, oem=oem)
        self.current_frame_idx = 0

        frame_count = self.decoder.get_frame_count()
        if frame_count > 0:
            self.render_frame_at(0)
        else:
            self._render_placeholder()

        return frame_count

    def _render_placeholder(self) -> None:
        """Renders a realistic synthetic OSD camera frame when no decoder stream or video file is present."""
        img = np.zeros((360, 640, 3), dtype=np.uint8)
        img[:] = (14, 17, 13)

        # Draw grid lines for authentic security camera look
        cv2.line(img, (0, 180), (640, 180), (25, 30, 25), 1)
        cv2.line(img, (320, 0), (320, 360), (25, 30, 25), 1)

        # Draw green monospace OSD header
        cv2.putText(img, self.osd_text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 240, 100), 1, cv2.LINE_AA)

        # Draw AI Bounding Boxes if specified
        for box in self.bounding_boxes:
            x1, y1, x2, y2 = box["bbox"]
            label = f"{box['class_name'].upper()} [{box['confidence']:.2f}]"
            cv2.rectangle(img, (x1, y1), (x2, y2), (248, 189, 56), 2)
            cv2.putText(img, label, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (248, 189, 56), 1, cv2.LINE_AA)

        height, width, _ = img.shape
        bytes_per_line = 3 * width
        q_img = QImage(img.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)

        if not self.label.size().isEmpty():
            scaled = pixmap.scaled(self.label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.label.setPixmap(scaled)
        else:
            self.label.setPixmap(pixmap)

    def render_frame_at(self, frame_idx: int) -> bool:
        frame = None
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            if not ret:
                frame = None

        if frame is None and self.decoder:
            frame = self.decoder.read_frame(frame_idx)

        if frame is None:
            self._render_placeholder()
            return False

        # Clone frame for drawing OSD & BBoxes
        display_frame = frame.copy()
        h, w = display_frame.shape[:2]

        # Overlay OSD
        cv2.putText(display_frame, self.osd_text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 240, 100), 1, cv2.LINE_AA)

        # Draw Bounding Boxes
        for box in self.bounding_boxes:
            x1, y1, x2, y2 = box["bbox"]
            label = f"{box['class_name'].upper()} [{box['confidence']:.2f}]"
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (248, 189, 56), 2)
            cv2.putText(display_frame, label, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (248, 189, 56), 1, cv2.LINE_AA)

        bytes_per_line = 3 * w
        # Convert BGR OpenCV frame to RGB QImage
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        if not self.label.size().isEmpty():
            scaled_pixmap = pixmap.scaled(
                self.label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.label.setPixmap(scaled_pixmap)
        else:
            self.label.setPixmap(pixmap)

        self.current_frame_idx = frame_idx
        return True

    def play(self, fps: int = 25) -> None:
        interval_ms = int(1000 / max(fps, 1))
        self.timer.start(interval_ms)

    def stop(self) -> None:
        self.timer.stop()

    def set_proxy_mode(self, enabled: bool, target_fps: int = 5) -> None:
        if self.timer.isActive():
            self.play(fps=target_fps if enabled else 25)

    def _next_frame(self) -> None:
        total_frames = 0
        if self.cap and self.cap.isOpened():
            total_frames = self.total_file_frames
        elif self.decoder:
            total_frames = self.decoder.get_frame_count()

        if total_frames == 0:
            self._render_placeholder()
            return

        next_idx = (self.current_frame_idx + 1) % total_frames
        self.render_frame_at(next_idx)
