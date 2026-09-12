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

    def __init__(self, stream_buffer: bytes, oem: str = "auto", max_frames: Optional[int] = None):
        self.raw_buffer = stream_buffer
        self.depacketized_buffer = depacketize_stream(stream_buffer, oem=oem)
        self.max_frames = max_frames
        self._frames: List[np.ndarray] = []
        self._decoded = False
        self._decode_stream()

    def _try_decode(self, suffix: str) -> List[np.ndarray]:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_name = tmp.name
            tmp.write(self.depacketized_buffer)
            tmp.flush()

        frames = []
        try:
            cap = cv2.VideoCapture(tmp_name)
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                frames.append(frame)
                if self.max_frames is not None and len(frames) >= self.max_frames:
                    break
            cap.release()
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except Exception:
                    pass
        return frames

    def _decode_stream(self) -> None:
        if not self.depacketized_buffer:
            self._frames = []
            self._decoded = True
            return

        # Determine codec extension based on H.265 / HEVC stream signatures
        is_h265 = (
            b"H265" in self.raw_buffer[:4096]
            or b"\x00\x00\x00\x01\x40" in self.depacketized_buffer[:2048]
            or b"\x00\x00\x01\x40" in self.depacketized_buffer[:2048]
            or b"\x00\x00\x00\x01\x42" in self.depacketized_buffer[:2048]
            or b"\x00\x00\x01\x42" in self.depacketized_buffer[:2048]
        )
        primary_suffix = ".h265" if is_h265 else ".h264"
        fallback_suffix = ".h264" if is_h265 else ".h265"

        frames = self._try_decode(primary_suffix)
        if not frames:
            frames = self._try_decode(fallback_suffix)

        self._frames = frames
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
