"""Unified ImageReader abstraction — seamlessly reads raw (.dd, .raw) and split EWF (.E01, .E02, .E03, .eo3...) segment images.

Decompresses EnCase EWF zlib sector chunks on-the-fly, providing a transparent
uncompressed virtual drive interface (read, seek, tell) for all parsers and carvers.
"""

import glob
import os
import re
import struct
import zlib
from typing import Dict, List, Optional

# EWF / EnCase Magic Headers: EVF\r\n\x81\x00 or EVF\t\r\n\xff\x00
EWF_MAGIC_HEADERS = (
    b"\x45\x56\x46\x0d\x0a\x81\x00",
    b"\x45\x56\x46\x09\x0d\x0a\xff\x00",
    b"EVF",
)


def parse_segment_ext(path: str) -> Optional[int]:
    """
    Returns sequential index of an EWF/split extension (.e01->1, .e02->2, .eo3->3, .e03->3, .eaa->100).
    Normalizes common typos like '.eo3' (letter O instead of number 0).
    """
    ext = os.path.splitext(path)[1].lower()
    m = re.match(r"^\.[eE]([0-9a-zA-Z]{2})$", ext)
    if not m:
        return None

    code = m.group(1).lower().replace("o", "0")
    if code.isdigit():
        return int(code)

    if len(code) == 2 and code.isalpha():
        return 100 + (ord(code[0]) - ord("a")) * 26 + (ord(code[1]) - ord("a"))

    return None


def find_split_segments(input_path: str) -> List[str]:
    """
    Given a path to any EWF segment file (e.g., 'case.E01', 'case.e03', or 'case.eo3'),
    discovers all matching split segment files in the directory and returns them
    in true sequential order starting from chunk 1 (.E01 / .eo1).
    """
    if not os.path.exists(input_path):
        return []

    base_dir = os.path.dirname(os.path.abspath(input_path))
    file_name = os.path.basename(input_path)

    seg_idx = parse_segment_ext(file_name)
    if seg_idx is None:
        return [input_path]

    stem = os.path.splitext(file_name)[0]
    pattern = os.path.join(base_dir, f"{stem}.*")
    candidates = glob.glob(pattern)

    valid_segments = []
    for p in candidates:
        idx = parse_segment_ext(p)
        if idx is not None:
            valid_segments.append((idx, p))

    if not valid_segments:
        return [input_path]

    valid_segments.sort(key=lambda item: item[0])
    return [p for _, p in valid_segments]


class EWFChunkDescriptor:
    __slots__ = ("offset", "length", "is_compressed", "file_path")

    def __init__(self, offset: int, length: int, is_compressed: bool, file_path: str):
        self.offset = offset
        self.length = length
        self.is_compressed = is_compressed
        self.file_path = file_path


def parse_ewf_chunks(segment_paths: List[str]) -> List[EWFChunkDescriptor]:
    """Parses EWF section headers and chunk tables across segment files."""
    chunks = []
    for seg_path in segment_paths:
        with open(seg_path, "rb") as f:
            buf = f.read()

        pos = 13
        while pos < len(buf) - 76:
            sec_name = buf[pos : pos + 16].rstrip(b"\x00").decode("latin1", errors="ignore")
            next_offset = struct.unpack("<Q", buf[pos + 16 : pos + 24])[0]

            if sec_name == "table":
                num_chunks = struct.unpack("<I", buf[pos + 76 : pos + 80])[0]
                offsets_start = pos + 76 + 24

                chunk_offsets = []
                for i in range(num_chunks):
                    entry = struct.unpack("<I", buf[offsets_start + i * 4 : offsets_start + (i + 1) * 4])[0]
                    chunk_offsets.append(entry)

                for i in range(len(chunk_offsets) - 1):
                    entry = chunk_offsets[i]
                    is_comp = bool(entry & 0x80000000)
                    off0 = entry & 0x7FFFFFFF
                    off1 = chunk_offsets[i + 1] & 0x7FFFFFFF
                    clen = off1 - off0
                    chunks.append(EWFChunkDescriptor(off0, clen, is_comp, seg_path))

            if next_offset > pos and next_offset < len(buf):
                pos = next_offset
            else:
                break
    return chunks


class ImageReader:
    """
    Unified file-like reader providing read, seek, tell across single (.dd, .raw)
    or split EWF (.E01, .E02, .E03, .eo3) evidence segment files with on-the-fly zlib decompression.
    """

    def __init__(self, first_segment_path: str):
        if not os.path.exists(first_segment_path):
            raise FileNotFoundError(f"Evidence file not found: {first_segment_path}")

        self.first_segment_path = first_segment_path
        self.segments = find_split_segments(first_segment_path)
        self.current_offset = 0
        self._is_ewf = False
        self.ewf_chunks: List[EWFChunkDescriptor] = []
        self._chunk_cache: Dict[int, bytes] = {}

        # Check EWF Header Magic in the primary segment (chunk 1)
        if self.segments:
            with open(self.segments[0], "rb") as f:
                header_bytes = f.read(16)
                if any(header_bytes.startswith(magic) for magic in EWF_MAGIC_HEADERS):
                    self._is_ewf = True

        if self._is_ewf:
            self.ewf_chunks = parse_ewf_chunks(self.segments)
            if self.ewf_chunks:
                self.total_size = len(self.ewf_chunks) * 32768
            else:
                self.segment_sizes = [os.path.getsize(p) for p in self.segments]
                self.total_size = sum(self.segment_sizes)
        else:
            self.segment_sizes = [os.path.getsize(p) for p in self.segments]
            self.total_size = sum(self.segment_sizes)

    @property
    def is_ewf(self) -> bool:
        return self._is_ewf

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    def size(self) -> int:
        return self.total_size

    def _read_ewf_chunk(self, chunk_idx: int) -> bytes:
        if chunk_idx in self._chunk_cache:
            return self._chunk_cache[chunk_idx]

        if chunk_idx < 0 or chunk_idx >= len(self.ewf_chunks):
            return b"\x00" * 32768

        info = self.ewf_chunks[chunk_idx]
        if info.length == 52 or info.length == 0:
            decomp = b"\x00" * 32768
        else:
            with open(info.file_path, "rb") as f:
                f.seek(info.offset)
                chunk_bytes = f.read(info.length)
            if info.is_compressed:
                try:
                    decomp = zlib.decompress(chunk_bytes)
                except Exception:
                    decomp = b"\x00" * 32768
            else:
                decomp = chunk_bytes

            if len(decomp) < 32768:
                decomp = decomp + b"\x00" * (32768 - len(decomp))

        if len(self._chunk_cache) > 256:
            self._chunk_cache.clear()
        self._chunk_cache[chunk_idx] = decomp
        return decomp

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

        if not self._is_ewf or not self.ewf_chunks:
            # Raw file stream reading
            bytes_to_read = size
            buffer = bytearray()
            target_offset = self.current_offset

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

        else:
            # Decompressed EWF virtual stream reading
            buffer = bytearray()
            rem = size
            cur = self.current_offset

            while rem > 0 and cur < self.total_size:
                chunk_idx = cur // 32768
                chunk_off = cur % 32768
                chunk_bytes = self._read_ewf_chunk(chunk_idx)

                avail = len(chunk_bytes) - chunk_off
                to_copy = min(rem, avail)
                buffer.extend(chunk_bytes[chunk_off : chunk_off + to_copy])

                rem -= to_copy
                cur += to_copy

            self.current_offset = cur
            return bytes(buffer)

    def close(self) -> None:
        self._chunk_cache.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
