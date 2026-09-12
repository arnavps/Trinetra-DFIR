"""Decodes the original, unconverted elementary stream. For decoding, the original bytes are written to an ephemeral OS temp file (never the case directory) solely because OpenCV cannot decode from an in-memory buffer directly; the temp file is deleted immediately after decode and at no point is a converted or re-encoded file produced."""

import os
import tempfile
import cv2
import numpy as np
from typing import Generator, List, Optional
from app.engine5_playback.depacketizer import depacketize_stream

# Suppress FFmpeg C-level log noise for non-video sector blocks
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"


class StreamDecoder:
    """
    Decodes the original, unconverted elementary stream. For decoding, the original bytes are written to an ephemeral OS temp file (never the case directory) solely because OpenCV cannot decode from an in-memory buffer directly; the temp file is deleted immediately after decode and at no point is a converted or re-encoded file produced.
    """

    def __init__(self, stream_buffer: bytes, oem: str = "auto"):
        self.raw_buffer = stream_buffer
        self.depacketized_buffer = depacketize_stream(stream_buffer, oem=oem)
        self._frames: List[np.ndarray] = []
        self._decoded = False
        self._decode_stream()

    def _decode_stream(self) -> None:
        if not self.depacketized_buffer:
            self._frames = []
            self._decoded = True
            return

        # Use an ephemeral system temp file (outside case directory) for OpenCV H.264 demuxing
        with tempfile.NamedTemporaryFile(suffix=".h264", delete=False) as tmp:
            tmp_name = tmp.name
            tmp.write(self.depacketized_buffer)
            tmp.flush()

        try:
            cap = cv2.VideoCapture(tmp_name)
            frames = []
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                frames.append(frame)
            cap.release()
            self._frames = frames
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except Exception:
                    pass

        self._decoded = True

    def get_frame_count(self) -> int:
        return len(self._frames)

    def read_frame(self, frame_index: int) -> Optional[np.ndarray]:
        """Frame-extraction interface: returns single decoded frame at frame_index on demand."""
        if 0 <= frame_index < len(self._frames):
            return self._frames[frame_index]
        return None

    def iter_frames(self) -> Generator[np.ndarray, None, None]:
        """Live playback interface: yields frames sequentially for UI rendering."""
        for frame in self._frames:
            yield frame
