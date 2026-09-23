"""Unit test asserting bounded peak memory usage during ImageReader construction on large EWF images."""

import os
import struct
import tracemalloc
import pytest
from app.engine1_acquisition.image_reader import ImageReader, EWF_MAGIC_HEADERS


def create_synthetic_large_e01(file_path: str, virtual_chunk_count: int = 1000):
    """
    Creates a valid synthetic .E01 segment structure that declares many chunks
    (e.g. 1000 chunks * 32KB = 32MB virtual volume) with padding, verifying that
    ImageReader never reads the whole file into RAM.
    """
    with open(file_path, "wb") as f:
        # 13 bytes file header
        f.write(EWF_MAGIC_HEADERS[0] + b"\x00\x00\x00\x00\x00\x00")

        pos = 13
        # Section 1: header section
        sec1_name = b"header\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        sec1_next = pos + 1000
        sec1_size = 1000
        f.write(sec1_name)
        f.write(struct.pack("<Q", sec1_next))
        f.write(struct.pack("<Q", sec1_size))
        # pad to sec1_next
        pad_len = sec1_next - (pos + 32)
        f.write(b"\x00" * pad_len)

        # Section 2: table section at sec1_next
        pos = sec1_next
        sec2_name = b"table\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        # Table size: 76 bytes header + 24 bytes + (virtual_chunk_count + 1) * 4 bytes
        table_data_len = 76 + 24 + (virtual_chunk_count + 1) * 4
        sec2_next = pos + table_data_len + 5000000  # simulate file having 5MB+ data beyond table
        sec2_size = table_data_len

        f.write(sec2_name)
        f.write(struct.pack("<Q", sec2_next))
        f.write(struct.pack("<Q", sec2_size))
        # pad to pos + 76
        f.write(b"\x00" * (76 - 32))
        # write num_chunks at pos + 76
        f.write(struct.pack("<I", virtual_chunk_count + 1))
        # pad 20 bytes to pos + 100
        f.write(b"\x00" * 20)

        # write chunk offsets
        for i in range(virtual_chunk_count + 1):
            offset_val = 1000 + i * 100
            # uncompressed entry
            f.write(struct.pack("<I", offset_val))

        # pad file to 6MB to ensure file on disk is substantial
        f.write(b"\xAA" * (6 * 1024 * 1024))


def test_image_reader_construction_peak_memory_bounded(tmp_path):
    """
    Asserts that constructing an ImageReader on an E01 file does NOT allocate memory
    proportional to the file size (peak memory must stay under 5 MB).
    """
    large_e01 = os.path.join(tmp_path, "synthetic_large.E01")
    create_synthetic_large_e01(large_e01, virtual_chunk_count=2000)

    file_size_bytes = os.path.getsize(large_e01)
    assert file_size_bytes > 5 * 1024 * 1024, "Test file should be at least 5MB on disk"

    tracemalloc.start()
    tracemalloc.reset_peak()

    reader = ImageReader(large_e01)
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    try:
        assert reader.is_ewf is True
        assert len(reader.ewf_chunks) == 2000
        # Peak memory allocated must be well under 5 MB (in reality under 1 MB)
        assert peak_mem < 2 * 1024 * 1024, f"Peak memory was {peak_mem} bytes, expected < 2MB"
    finally:
        reader.close()
