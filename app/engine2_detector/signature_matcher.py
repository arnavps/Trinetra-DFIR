"""Deterministic primary-path detector (Blueprint §3.2-A) — scans known offsets against signatures.json."""

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class MatchResult:
    oem: str
    signature_id: str
    matched_offset: int
    matched: bool
    description: str = ""


DEFAULT_SIGNATURES_PATH = os.path.join(
    os.path.dirname(__file__), "signatures.json"
)


def load_signatures(signatures_path: Optional[str] = None) -> list:
    path = signatures_path or DEFAULT_SIGNATURES_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("signatures", [])


def match_signature(image_path: str, signatures_path: Optional[str] = None) -> MatchResult:
    """
    Scans known offsets from signatures.json against an image file read-only.
    Returns MatchResult indicating OEM and signature details if matched,
    or oem='Unknown', matched=False if no signature matches.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image path '{image_path}' does not exist.")

    signatures = load_signatures(signatures_path)

    with open(image_path, "rb") as f:
        file_size = f.seek(0, os.SEEK_END)

        for sig in signatures:
            offset = sig["offset"]
            pattern = bytes.fromhex(sig["pattern_hex"])
            pattern_len = len(pattern)

            if offset + pattern_len > file_size:
                continue

            f.seek(offset)
            read_bytes = f.read(pattern_len)

            if read_bytes == pattern:
                return MatchResult(
                    oem=sig["oem"],
                    signature_id=sig["signature_id"],
                    matched_offset=offset,
                    matched=True,
                    description=sig.get("description", ""),
                )

    return MatchResult(
        oem="Unknown",
        signature_id="none",
        matched_offset=-1,
        matched=False,
        description="No deterministic OEM signature matched.",
    )
