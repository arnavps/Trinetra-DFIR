"""Standalone stream decoder for portable Tri-Netra evidence viewer.
Decodes raw, unconverted elementary bitstreams using ephemeral in-memory buffering.
Zero re-encoding, zero persistent video files produced.
"""

import os
import tempfile
from typing import List, Optional
import cv2
import numpy as np

# Import local standalone depacketizer
try:
    from depacketizer import depacketize_stream
except ImportError:
    try:
        from .depacketizer import depacketize_stream
    except Exception:
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from depacketizer import depacketize_stream

# Suppress FFmpeg C-level log noise
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"


class StreamDecoder:
    """
    Decodes the original, unconverted elementary stream.
    For decoding, original bytes are written to an ephemeral OS temp file solely
    because OpenCV VideoCapture cannot read raw elementary buffers directly in memory;
    the temp file is deleted immediately after decode and at no point is a converted
    or re-encoded video file created.
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

        is_h265 = (
            b"H265" in self.raw_buffer[:4096]
            or b"HEVC" in self.raw_buffer[:4096]
            or self.depacketized_buffer.startswith(b"\x00\x00\x00\x01\x40")
            or self.depacketized_buffer.startswith(b"\x00\x00\x00\x01\x42")
        )

        suffixes = [".h265", ".hevc", ".h264", ".mp4"] if is_h265 else [".h264", ".264", ".mp4", ".h265"]

        for sfx in suffixes:
            frames = self._try_decode(sfx)
            if frames:
                self._frames = frames
                self._decoded = True
                return

        # Direct read fallback if depacketized buffer was identical
        self._frames = []
        self._decoded = True

    def get_frames(self) -> List[np.ndarray]:
        return self._frames

    @property
    def frame_count(self) -> int:
        return len(self._frames)
