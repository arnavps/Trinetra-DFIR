"""Unit tests for Engine 1 ImageReader (.E01, .E02, .E03 split segment support)."""

import os
import pytest
from app.engine1_acquisition.image_reader import ImageReader, find_split_segments, EWF_MAGIC_HEADERS


def test_find_split_segments(tmp_path):
    seg1 = os.path.join(tmp_path, "evidence_case.E01")
    seg2 = os.path.join(tmp_path, "evidence_case.E02")
    seg3 = os.path.join(tmp_path, "evidence_case.E03")

    for p in [seg1, seg2, seg3]:
        with open(p, "wb") as f:
            f.write(b"SEGMENT_DATA_BLOCK_" + p.encode())

    found = find_split_segments(seg1)
    assert len(found) == 3
    assert found == [seg1, seg2, seg3]


def test_image_reader_single_dd_file(tmp_path):
    dd_path = os.path.join(tmp_path, "single_drive.dd")
    payload = b"HEADER_SECTOR_DATA_" + b"A" * 1000
    with open(dd_path, "wb") as f:
        f.write(payload)

    with ImageReader(dd_path) as reader:
        assert not reader.is_ewf
        assert reader.segment_count == 1
        assert reader.size() == len(payload)

        data = reader.read(6)
        assert data == b"HEADER"
        assert reader.tell() == 6

        reader.seek(0)
        assert reader.read(len(payload)) == payload


def test_image_reader_multi_segment_e01_e02_e03(tmp_path):
    e01_path = os.path.join(tmp_path, "evidence.E01")
    e02_path = os.path.join(tmp_path, "evidence.E02")
    e03_path = os.path.join(tmp_path, "evidence.E03")

    payload1 = EWF_MAGIC_HEADERS[0] + b"CHUNK1_DATA_"
    payload2 = b"CHUNK2_SPLIT_DATA_"
    payload3 = b"CHUNK3_TAIL_DATA"

    with open(e01_path, "wb") as f:
        f.write(payload1)
    with open(e02_path, "wb") as f:
        f.write(payload2)
    with open(e03_path, "wb") as f:
        f.write(payload3)

    with ImageReader(e01_path) as reader:
        assert reader.is_ewf
        assert reader.segment_count == 3
        total_expected = len(payload1) + len(payload2) + len(payload3)
        assert reader.size() == total_expected

        full_data = reader.read(total_expected)
        assert full_data == payload1 + payload2 + payload3

        # Test seeking across segment boundary
        reader.seek(len(payload1))
        seg2_read = reader.read(len(payload2))
        assert seg2_read == payload2


def test_image_reader_opening_e03_or_eo3_directly(tmp_path):
    e01_path = os.path.join(tmp_path, "heim_drive.eo1")
    e02_path = os.path.join(tmp_path, "heim_drive.eo2")
    eo3_path = os.path.join(tmp_path, "heim_drive.eo3")

    payload1 = EWF_MAGIC_HEADERS[0] + b"HEIMVISION_SUPERBLOCK_SECTOR_0"
    payload2 = b"HEIMVISION_DATA_SECTOR_CHUNK2"
    payload3 = b"HEIMVISION_INDEX_TABLE_SECTOR_TAIL"

    with open(e01_path, "wb") as f:
        f.write(payload1)
    with open(e02_path, "wb") as f:
        f.write(payload2)
    with open(eo3_path, "wb") as f:
        f.write(payload3)

    # Opening chunk 3 (.eo3) directly MUST locate chunk 1 (.eo1) and start at sector 0
    with ImageReader(eo3_path) as reader:
        assert reader.is_ewf
        assert reader.segment_count == 3
        header_data = reader.read(len(EWF_MAGIC_HEADERS[0]))
        assert header_data == EWF_MAGIC_HEADERS[0]
        assert b"HEIMVISION_SUPERBLOCK" in reader.read(100)

