"""Unified ImageReader abstraction — seamlessly reads raw (.dd, .raw) and split EWF (.E01, .E02, .E03...) segment images.

Provides standard Python file-like interface (read, seek, tell) across single or split forensic evidence segment files.
"""

import glob
import os
import re
from typing import List, Optional

# EWF / EnCase Magic Header: EVF\r\n\x81\x00 (0x4556460D0A8100)
EWF_MAGIC_HEADER = b"\x45\x56\x46\x0d\x0a\x81\x00"


def find_split_segments(first_segment_path: str) -> List[str]:
    """
    Given a path to an E01 file (e.g., 'case_drive.E01'), discovers all matching split segment files
    in sequential order (e.g., '.E01', '.E02', '.E03', ... '.E99', '.EAA', '.EAB').
    """
    if not os.path.exists(first_segment_path):
        return []

    base_dir = os.path.dirname(os.path.abspath(first_segment_path))
    file_name = os.path.basename(first_segment_path)
    prefix_match = re.match(r"^(.*?)\.e\d{2}$", file_name, re.IGNORECASE)

    if not prefix_match:
        return [first_segment_path]

    stem = prefix_match.group(1)
    pattern = os.path.join(base_dir, f"{stem}.[eE][0-9a-zA-Z][0-9a-zA-Z]")
    matches = glob.glob(pattern)

    def segment_key(path_str: str) -> str:
        ext = os.path.splitext(path_str)[1].upper()
        return ext

    return sorted(matches, key=segment_key)


class ImageReader:
    """
    Unified file-like reader providing read, seek, tell across single (.dd, .raw)
    or split EWF (.E01, .E02, .E03) evidence segment files.
    """

    def __init__(self, first_segment_path: str):
        if not os.path.exists(first_segment_path):
            raise FileNotFoundError(f"Evidence file not found: {first_segment_path}")

        self.first_segment_path = first_segment_path
        self.segments = find_split_segments(first_segment_path)
        self.segment_files = []
        self.segment_sizes = []
        self.total_size = 0

        for seg_path in self.segments:
            size = os.path.getsize(seg_path)
            self.segment_sizes.append(size)
            self.total_size += size

        self.current_offset = 0
        self._is_ewf = False
        self._header_offset = 0

        # Check EWF Header Magic in first segment
        with open(first_segment_path, "rb") as f:
            header_bytes = f.read(len(EWF_MAGIC_HEADER))
            if header_bytes == EWF_MAGIC_HEADER:
                self._is_ewf = True

    @property
    def is_ewf(self) -> bool:
        return self._is_ewf

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    def size(self) -> int:
        return self.total_size

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if whence == os.SEEK_SET:
            self.current_offset = offset
        elif whence == os.SEEK_CUR:
            self.current_offset += offset
        elif whence == os.SEEK_END:
            self.current_offset = self.total_size + offset
        else:
            raise ValueError(f"Invalid whence argument: {whence}")

        self.current_offset = max(0, min(self.current_offset, self.total_size))
        return self.current_offset

    def tell(self) -> int:
        return self.current_offset

    def read(self, size: int = -1) -> bytes:
        if size < 0 or self.current_offset + size > self.total_size:
            size = max(0, self.total_size - self.current_offset)

        if size == 0:
            return b""

        bytes_to_read = size
        buffer = bytearray()
        target_offset = self.current_offset

        # Map target_offset into specific segment file
        seg_idx = 0
        accum_size = 0
        while seg_idx < len(self.segment_sizes) and accum_size + self.segment_sizes[seg_idx] <= target_offset:
            accum_size += self.segment_sizes[seg_idx]
            seg_idx += 1

        while bytes_to_read > 0 and seg_idx < len(self.segments):
            seg_offset = target_offset - accum_size
            seg_path = self.segments[seg_idx]
            seg_avail = self.segment_sizes[seg_idx] - seg_offset

            read_chunk_len = min(bytes_to_read, seg_avail)
            with open(seg_path, "rb") as f:
                f.seek(seg_offset)
                chunk = f.read(read_chunk_len)
                buffer.extend(chunk)

            bytes_to_read -= len(chunk)
            target_offset += len(chunk)
            accum_size += self.segment_sizes[seg_idx]
            seg_idx += 1

            if len(chunk) == 0:
                break

        self.current_offset += len(buffer)
        return bytes(buffer)

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
