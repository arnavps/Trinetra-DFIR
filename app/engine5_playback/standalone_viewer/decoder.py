"""Standalone stream decoder for portable Tri-Netra evidence viewer.
Decodes raw, unconverted elementary bitstreams using ephemeral in-memory buffering.
Zero re-encoding, zero persistent video files produced.
Employs streaming on-demand frame decoding for high-frame-count/high-resolution streams
to prevent host system RAM exhaustion and stuttering.
"""

import os
import tempfile
from typing import Generator, List, Optional
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
    For small streams (<= 120 frames), pre-buffers frames in RAM for instantaneous access.
    For long/large CCTV streams (> 120 frames), decodes on-demand via an active OpenCV
    stream session with zero memory bloat, allowing full multi-minute video playback
    without exhausting system RAM.
    """

    def __init__(self, stream_buffer: bytes, oem: str = "auto", max_frames: Optional[int] = None):
        self.raw_buffer = stream_buffer
        self.depacketized_buffer = depacketize_stream(stream_buffer, oem=oem)
        self.max_frames = max_frames
        self._frames: List[np.ndarray] = []
        self._cap: Optional[cv2.VideoCapture] = None
        self._tmp_name: Optional[str] = None
        self._current_pos: int = -1
        self._last_frame: Optional[np.ndarray] = None
        self._total_frames: int = 0
        self._decoded = False
        self._init_decoder()

    def _init_decoder(self) -> None:
        if not self.depacketized_buffer:
            self._decoded = True
            return

        is_h265 = (
            b"H265" in self.raw_buffer[:4096]
            or b"HEVC" in self.raw_buffer[:4096]
            or b"\x00\x00\x00\x01\x40" in self.depacketized_buffer[:2048]
            or b"\x00\x00\x01\x40" in self.depacketized_buffer[:2048]
            or b"\x00\x00\x00\x01\x42" in self.depacketized_buffer[:2048]
            or b"\x00\x00\x01\x42" in self.depacketized_buffer[:2048]
        )
        suffixes = [".h265", ".hevc", ".h264", ".mp4"] if is_h265 else [".h264", ".264", ".mp4", ".h265"]

        for sfx in suffixes:
            with tempfile.NamedTemporaryFile(suffix=sfx, delete=False) as tmp:
                tmp_name = tmp.name
                tmp.write(self.depacketized_buffer)
                tmp.flush()

            cap = cv2.VideoCapture(tmp_name)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self._cap = cap
                    self._tmp_name = tmp_name
                    self._last_frame = frame
                    self._current_pos = 0
                    break
            cap.release()
            if os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except Exception:
                    pass

        if not self._cap:
            self._decoded = True
            return

        fcnt = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fcnt <= 0:
            frames = [self._last_frame]
            while self._cap.isOpened():
                ret, fr = self._cap.read()
                if not ret or fr is None:
                    break
                frames.append(fr)
                if self.max_frames and len(frames) >= self.max_frames:
                    break
            self._frames = frames
            self._total_frames = len(frames)
            self._cap.release()
            self._cap = None
            if self._tmp_name and os.path.exists(self._tmp_name):
                try:
                    os.remove(self._tmp_name)
                except Exception:
                    pass
                self._tmp_name = None
        else:
            self._total_frames = fcnt
            if self.max_frames is not None:
                self._total_frames = min(self._total_frames, self.max_frames)

            # If clip is short (<= 120 frames), pre-buffer in RAM and remove temp file
            if self._total_frames <= 120:
                frames = [self._last_frame]
                while self._cap.isOpened():
                    ret, fr = self._cap.read()
                    if not ret or fr is None:
                        break
                    frames.append(fr)
                    if len(frames) >= self._total_frames:
                        break
                self._frames = frames
                self._total_frames = len(frames)
                self._cap.release()
                self._cap = None
                if self._tmp_name and os.path.exists(self._tmp_name):
                    try:
                        os.remove(self._tmp_name)
                    except Exception:
                        pass
                    self._tmp_name = None

        self._decoded = True

    def get_frame_count(self) -> int:
        return self._total_frames

    @property
    def frame_count(self) -> int:
        return self._total_frames

    def read_frame(self, frame_index: int) -> Optional[np.ndarray]:
        """Frame-extraction interface: returns single decoded frame at frame_index on demand."""
        if frame_index < 0 or frame_index >= self._total_frames:
            return None

        # Pre-buffered mode for small streams
        if self._frames:
            if frame_index < len(self._frames):
                return self._frames[frame_index]
            return None

        # Streaming on-demand mode for large streams
        if not self._cap or not self._cap.isOpened():
            return None

        if frame_index == self._current_pos:
            return self._last_frame

        if frame_index == self._current_pos + 1:
            ret, fr = self._cap.read()
            if ret and fr is not None:
                self._current_pos = frame_index
                self._last_frame = fr
                return fr

        # Seek to frame_index
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, fr = self._cap.read()
        if ret and fr is not None:
            self._current_pos = frame_index
            self._last_frame = fr
            return fr

        # If set failed or seek lost sync, reopen and seek
        self._cap.release()
        self._cap = cv2.VideoCapture(self._tmp_name)
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, fr = self._cap.read()
        if ret and fr is not None:
            self._current_pos = frame_index
            self._last_frame = fr
            return fr
        return None

    def get_frames(self) -> List[np.ndarray]:
        """Returns all decoded frames as a list (for legacy callers / small test fixtures)."""
        if self._frames:
            return self._frames
        return list(self.iter_frames())

    def iter_frames(self) -> Generator[np.ndarray, None, None]:
        """Live playback interface: yields frames sequentially for UI rendering."""
        if self._frames:
            for frame in self._frames:
                yield frame
        else:
            for i in range(self._total_frames):
                frame = self.read_frame(i)
                if frame is not None:
                    yield frame

    def close(self) -> None:
        """Releases the underlying OpenCV VideoCapture and removes the ephemeral temp file."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        if self._tmp_name and os.path.exists(self._tmp_name):
            try:
                os.remove(self._tmp_name)
            except Exception:
                pass
            self._tmp_name = None

    def __del__(self) -> None:
        self.close()
