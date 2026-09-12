"""
NAL-unit heuristic recovery from unallocated/corrupted sectors.
Attempts Rust hot path (unidvr_rustcore.find_nal_start_codes) first with Python bytes.find() fallback.
"""

import os
from typing import List, Tuple, Union

try:
    import unidvr_rustcore
except ImportError:
    unidvr_rustcore = None

NAL_START_CODE_4 = b"\x00\x00\x00\x01"
NAL_START_CODE_3 = b"\x00\x00\x01"


def find_nal_start_codes(data: bytes, max_units: int = 2000) -> List[int]:
    """Scans binary data for 3-byte and 4-byte NAL unit start codes using Rust extension or bytes.find() fallback."""
    if unidvr_rustcore is not None and hasattr(unidvr_rustcore, "find_nal_start_codes"):
        try:
            return unidvr_rustcore.find_nal_start_codes(data, max_units)
        except Exception:
            pass

    offsets = []
    pos = 0
    data_len = len(data)
    while pos < data_len - 3:
        idx4 = data.find(NAL_START_CODE_4, pos)
        idx3 = data.find(NAL_START_CODE_3, pos)

        if idx4 == -1 and idx3 == -1:
            break

        if idx4 != -1 and (idx3 == -1 or idx4 <= idx3):
            offsets.append(idx4)
            pos = idx4 + 4
        else:
            offsets.append(idx3)
            pos = idx3 + 3

        if len(offsets) >= max_units:
            break

    return offsets


def carve_nal_units(source: Union[str, bytes], start_offset: int = 0, max_bytes: int = 64 * 1024 * 1024) -> List[bytes]:
    """
    Heuristically carves raw NAL unit elementary stream blocks from unallocated or corrupted sector data.
    Recovered output is returned exactly as scanned — raw elementary stream bytes with no container wrapper.
    """
    if isinstance(source, str):
        if not os.path.exists(source):
            raise FileNotFoundError(f"Source path '{source}' does not exist.")
        file_size = os.path.getsize(source)
        read_size = min(file_size - start_offset, max_bytes)
        with open(source, "rb") as f:
            f.seek(start_offset)
            data = f.read(read_size)
    else:
        data = source[start_offset : start_offset + max_bytes]

    offsets = find_nal_start_codes(data)
    if not offsets:
        return []

    nal_units = []
    for idx in range(len(offsets)):
        start = offsets[idx]
        end = offsets[idx + 1] if idx + 1 < len(offsets) else len(data)
        unit = data[start:end]
        if len(unit) > 4:
            nal_units.append(unit)

    return nal_units
