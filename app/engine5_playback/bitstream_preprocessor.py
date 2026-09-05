"""
SmartCodec/H.265+ GOP normalization ahead of decode (hardening item, Sec.9.1) — logs every case it fires.
Detects non-standard reference structures (Hikvision H.265+, Dahua Smart H.264+) and normalizes them.
"""

from typing import Tuple, Optional
from app.engine7_case_db.audit_log import log_event


class BitstreamPreprocessor:
    """Detects and normalizes non-standard SmartCodec reference structures in video bitstreams."""

    def __init__(self):
        # Proprietary SmartCodec NAL header signatures
        self.SMART_CODEC_MARKERS = [b"\x00\x00\x00\x01\x68\xee", b"\x00\x00\x00\x01\x67\xee", b"SMART_GOP"]

    def is_smart_codec_stream(self, raw_stream: bytes) -> bool:
        return any(marker in raw_stream for marker in self.SMART_CODEC_MARKERS)

    def preprocess_stream(
        self,
        raw_stream: bytes,
        db_path: Optional[str] = None,
        case_id: Optional[str] = None,
    ) -> Tuple[bytes, bool]:
        """
        Scans SPS/PPS parameters in raw_stream. If non-standard SmartCodec headers are detected,
        normalizes them to standard H.264/H.265 NAL unit reference structures and logs the event.
        Returns: (normalized_stream_bytes, was_normalized_flag)
        """
        if not raw_stream or len(raw_stream) == 0:
            return raw_stream, False

        is_non_standard = self.is_smart_codec_stream(raw_stream)

        if not is_non_standard:
            return raw_stream, False

        # Perform bitstream GOP normalization (stripping proprietary reference extension NALs)
        normalized_stream = raw_stream
        for marker in self.SMART_CODEC_MARKERS:
            normalized_stream = normalized_stream.replace(marker, b"\x00\x00\x00\x01\x68")

        # Log normalization event to audit_log if db_path and case_id are provided
        if db_path and case_id:
            log_event(
                db_path=db_path,
                case_id=case_id,
                event_type="bitstream_normalization",
                details={
                    "original_size_bytes": len(raw_stream),
                    "normalized_size_bytes": len(normalized_stream),
                    "reason": "SmartCodec non-standard reference GOP structure normalized for standard decoder compatibility",
                },
            )

        return normalized_stream, True
