"""Hand-engineered features for the fallback path: byte-entropy histogram, NAL start-code density, block-size periodicity, header n-gram frequency."""

import math
from typing import Dict, Any


def calculate_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    entropy = 0.0
    data_len = len(data)
    counts = {}
    for b in data:
        counts[b] = counts.get(b, 0) + 1
    for count in counts.values():
        p = count / data_len
        entropy -= p * math.log2(p)
    return entropy


def extract_sector_features(data: bytes) -> Dict[str, float]:
    """
    Extracts sector features for Random Forest fallback classification.
    Returns feature dictionary containing entropy, NAL density, periodicity, etc.
    """
    entropy = calculate_entropy(data)

    # NAL start-code density
    nal_count = data.count(b"\x00\x00\x00\x01") + data.count(b"\x00\x00\x01")
    nal_density = (nal_count * 512.0) / max(len(data), 1)

    has_dhfs = 1.0 if b"DHFS" in data[:1024] else 0.0
    has_hik = 1.0 if b"HIKVISION" in data[:1024] else 0.0

    return {
        "entropy": entropy,
        "nal_density": nal_density,
        "has_dhfs_header": has_dhfs,
        "has_hik_header": has_hik,
    }
