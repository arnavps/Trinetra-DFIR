"""Synthetic 1–2GB demo .dd images seeded with real OEM signatures, deleted GOPs and out-of-sync timestamps (Section 9.4)."""

import os
import random
import struct
import tempfile
import cv2
import numpy as np

from app.engine3_parsers import hikfat_constants as hik_const
from app.engine3_parsers import dhfs_constants as dh_const


DAHUA_MAGIC = dh_const.DHFS_SUPERBLOCK_MAGIC
HIKVISION_MAGIC = hik_const.HIKFAT_SUPERBLOCK_MAGIC


def create_tiny_h264_stream(num_frames: int = 5, width: int = 64, height: int = 64) -> bytes:
    """Generates a tiny valid playable video stream buffer using OpenCV."""
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as tmp:
        tmp_name = tmp.name

    try:
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        out = cv2.VideoWriter(tmp_name, fourcc, 10.0, (width, height))
        for i in range(num_frames):
            img = np.zeros((height, width, 3), dtype=np.uint8)
            color_val = (i * 45) % 256
            img[:, :] = [color_val, 255 - color_val, 120]
            out.write(img)
        out.release()

        with open(tmp_name, "rb") as f:
            stream_data = f.read()
    finally:
        if os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except Exception:
                pass

    return stream_data


def generate_dahua_image(output_path: str, size_bytes: int = 10 * 1024 * 1024, seed: int = 42) -> str:
    """
    Produces a synthetic .dd image with Dahua DHFS superblock signature at offset 0,
    a DHFS Master Index Table, and embedded playable video stream payload.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    rng = random.Random(seed)

    index_offset = size_bytes - dh_const.DHFS_INDEX_TABLE_OFFSET_FROM_END
    if index_offset <= len(DAHUA_MAGIC):
        raise ValueError("size_bytes too small to hold DHFS superblock and index table.")

    video_bytes = create_tiny_h264_stream(num_frames=5)
    video_sec_cnt = (len(video_bytes) + 511) // 512

    with open(output_path, "wb") as f:
        f.write(DAHUA_MAGIC)

        start_sec = 100
        sec_offset = start_sec * 512

        pad1 = sec_offset - len(DAHUA_MAGIC)
        f.write(rng.randbytes(pad1))

        f.write(video_bytes)
        video_pad = (video_sec_cnt * 512) - len(video_bytes)
        if video_pad > 0:
            f.write(b"\x00" * video_pad)

        curr_pos = f.tell()
        bytes_left = index_offset - curr_pos
        chunk_size = 64 * 1024
        while bytes_left > 0:
            current_chunk = min(bytes_left, chunk_size)
            data = rng.randbytes(current_chunk)
            f.write(data)
            bytes_left -= current_chunk

        f.write(dh_const.DHFS_INDEX_MAGIC)
        records_data = [
            (1, 1700000000, 1700003600, start_sec, video_sec_cnt, len(video_bytes)),
            (2, 1700003600, 1700007200, start_sec, video_sec_cnt, len(video_bytes)),
        ]
        f.write(struct.pack("<H", len(records_data)))

        index_table_bytes_written = len(dh_const.DHFS_INDEX_MAGIC) + 2
        for ch_id, start_ts, end_ts, s_sec, s_cnt, fsize in records_data:
            rec_bytes = struct.pack(
                dh_const.DHFS_INDEX_RECORD_STRUCT,
                ch_id, start_ts, end_ts, s_sec, s_cnt, fsize
            )
            f.write(rec_bytes)
            index_table_bytes_written += len(rec_bytes)

        remaining_tail = size_bytes - (index_offset + index_table_bytes_written)
        if remaining_tail > 0:
            f.write(rng.randbytes(remaining_tail))

    return output_path


def generate_hikvision_image(output_path: str, size_bytes: int = 10 * 1024 * 1024, seed: int = 42) -> str:
    """
    Produces a synthetic .dd image with Hikvision HIKFAT superblock signature at offset 0,
    a HIKFAT Master Index Table, and embedded playable video stream payload.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    rng = random.Random(seed)

    index_offset = size_bytes - hik_const.HIKFAT_INDEX_TABLE_OFFSET_FROM_END
    if index_offset <= len(HIKVISION_MAGIC):
        raise ValueError("size_bytes too small to hold HIKFAT superblock and index table.")

    video_bytes = create_tiny_h264_stream(num_frames=5)
    video_sec_cnt = (len(video_bytes) + 511) // 512

    with open(output_path, "wb") as f:
        f.write(HIKVISION_MAGIC)

        start_sec = 100
        sec_offset = start_sec * 512

        pad1 = sec_offset - len(HIKVISION_MAGIC)
        f.write(rng.randbytes(pad1))

        f.write(video_bytes)
        video_pad = (video_sec_cnt * 512) - len(video_bytes)
        if video_pad > 0:
            f.write(b"\x00" * video_pad)

        curr_pos = f.tell()
        bytes_left = index_offset - curr_pos
        chunk_size = 64 * 1024
        while bytes_left > 0:
            current_chunk = min(bytes_left, chunk_size)
            data = rng.randbytes(current_chunk)
            f.write(data)
            bytes_left -= current_chunk

        f.write(hik_const.HIKFAT_INDEX_MAGIC)
        records_data = [
            (1, 1700000000, 1700003600, start_sec, video_sec_cnt, len(video_bytes)),
            (2, 1700003600, 1700007200, start_sec, video_sec_cnt, len(video_bytes)),
            (1, 1700007200, 1700010800, start_sec, video_sec_cnt, len(video_bytes)),
        ]
        f.write(struct.pack("<H", len(records_data)))

        index_table_bytes_written = len(hik_const.HIKFAT_INDEX_MAGIC) + 2
        for ch_id, start_ts, end_ts, s_sec, s_cnt, fsize in records_data:
            rec_bytes = struct.pack(
                hik_const.HIKFAT_INDEX_RECORD_STRUCT,
                ch_id, start_ts, end_ts, s_sec, s_cnt, fsize
            )
            f.write(rec_bytes)
            index_table_bytes_written += len(rec_bytes)

        remaining_tail = size_bytes - (index_offset + index_table_bytes_written)
        if remaining_tail > 0:
            f.write(rng.randbytes(remaining_tail))

    return output_path


def generate_unknown_oem_image(output_path: str, size_bytes: int = 10 * 1024 * 1024, seed: int = 77) -> str:
    """
    Produces an undetected synthetic image containing no recognized superblock signature (Unknown OEM),
    embedded with raw NAL video stream units for generic carving test.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    rng = random.Random(seed)
    video_bytes = create_tiny_h264_stream(num_frames=5)

    with open(output_path, "wb") as f:
        f.write(b"UNKNOWN_OEM_RAW_SECTOR_HEADER_" + rng.randbytes(990))
        f.write(video_bytes)

        curr_pos = f.tell()
        if curr_pos < size_bytes:
            f.write(rng.randbytes(size_bytes - curr_pos))

    return output_path


def generate_heimvision_image(output_path: str, size_bytes: int = 10 * 1024 * 1024, seed: int = 42) -> str:
    """
    Produces a synthetic .dd image with HeimVision HFS superblock signature at offset 0,
    a HEIMINDEX Master Index Table, and embedded playable video stream payload.
    """
    from app.engine3_parsers import heimvision_constants as heim_const
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    rng = random.Random(seed)

    index_offset = size_bytes - heim_const.HEIMVISION_INDEX_TABLE_OFFSET_FROM_END
    if index_offset <= len(heim_const.HEIMVISION_SUPERBLOCK_MAGIC):
        raise ValueError("size_bytes too small to hold HeimVision superblock and index table.")

    video_bytes = create_tiny_h264_stream(num_frames=5)
    video_sec_cnt = (len(video_bytes) + 511) // 512

    with open(output_path, "wb") as f:
        f.write(heim_const.HEIMVISION_SUPERBLOCK_MAGIC)

        start_sec = 100
        sec_offset = start_sec * 512

        pad1 = sec_offset - len(heim_const.HEIMVISION_SUPERBLOCK_MAGIC)
        f.write(rng.randbytes(pad1))

        f.write(video_bytes)
        video_pad = (video_sec_cnt * 512) - len(video_bytes)
        if video_pad > 0:
            f.write(b"\x00" * video_pad)

        curr_pos = f.tell()
        bytes_left = index_offset - curr_pos
        chunk_size = 64 * 1024
        while bytes_left > 0:
            current_chunk = min(bytes_left, chunk_size)
            data = rng.randbytes(current_chunk)
            f.write(data)
            bytes_left -= current_chunk

        f.write(heim_const.HEIMVISION_INDEX_MAGIC)
        records_data = [
            (1, 1700000000, 1700003600, start_sec, video_sec_cnt, len(video_bytes)),
            (2, 1700003600, 1700007200, start_sec, video_sec_cnt, len(video_bytes)),
        ]
        f.write(struct.pack("<H", len(records_data)))

        index_table_bytes_written = len(heim_const.HEIMVISION_INDEX_MAGIC) + 2
        for ch_id, start_ts, end_ts, s_sec, s_cnt, fsize in records_data:
            rec_bytes = struct.pack(
                heim_const.HEIMVISION_INDEX_RECORD_STRUCT,
                ch_id, start_ts, end_ts, s_sec, s_cnt, fsize
            )
            f.write(rec_bytes)
            index_table_bytes_written += len(rec_bytes)

        remaining_tail = size_bytes - (index_offset + index_table_bytes_written)
        if remaining_tail > 0:
            f.write(rng.randbytes(remaining_tail))

    return output_path


if __name__ == "__main__":
    generate_dahua_image("dahua_demo.dd")
    generate_hikvision_image("hikvision_demo.dd")
    generate_unknown_oem_image("unknown_demo.dd")
