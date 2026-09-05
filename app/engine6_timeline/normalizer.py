"""
Combines OSD timestamps and visual anchor change-points into one unified per-channel case clock;
degrades gracefully to OSD-only when no visual anchor exists in frame.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np

from app.engine6_timeline.osd_extractor import extract_osd_timestamp
from app.engine6_timeline.visual_anchor import detect_luminance_anchors


class TimelineNormalizer:
    """Per-channel clock synchronization and timestamp drift normalizer."""

    def __init__(self, fps: float = 25.0):
        self.fps = fps

    def parse_iso_timestamp(self, ts_str: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                pass
        return None

    def normalize_channel_clock(
        self,
        raw_osd_stamps: List[Optional[str]],
        frames: Optional[List[np.ndarray]] = None,
        reference_anchor_frame: Optional[int] = None,
        reference_real_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates unified per-channel case clock offsets.
        Uses visual anchor change-points when available; degrades gracefully to OSD-only when no anchor exists.
        Returns: {
            'clock_offset_seconds': float,
            'anchors_found': List[int],
            'normalized_timestamps': List[str],
            'mode': 'visual_anchor' | 'osd_only' | 'frame_count_fallback'
        }
        """
        anchors = []
        if frames and len(frames) >= 2:
            anchors = detect_luminance_anchors(frames)

        mode = "osd_only"
        clock_offset_sec = 0.0

        # Check if reference visual anchor is provided and present in anchors
        if anchors and reference_anchor_frame is not None and reference_real_timestamp:
            ref_dt = self.parse_iso_timestamp(reference_real_timestamp)
            if ref_dt and 0 <= reference_anchor_frame < len(raw_osd_stamps):
                osd_at_anchor = raw_osd_stamps[reference_anchor_frame]
                osd_dt = self.parse_iso_timestamp(osd_at_anchor) if osd_at_anchor else None
                if osd_dt:
                    clock_offset_sec = (ref_dt - osd_dt).total_seconds()
                    mode = "visual_anchor"

        # If visual anchor calculation didn't apply, inspect OSD drift
        valid_osd = [(idx, self.parse_iso_timestamp(ts)) for idx, ts in enumerate(raw_osd_stamps) if ts]
        valid_osd = [(idx, dt) for idx, dt in valid_osd if dt is not None]

        if not valid_osd and not raw_osd_stamps:
            mode = "frame_count_fallback"

        # Generate normalized timestamps
        normalized_stamps = []
        base_dt = valid_osd[0][1] if valid_osd else datetime(2026, 9, 4, 12, 0, 0)
        base_idx = valid_osd[0][0] if valid_osd else 0

        for frame_idx in range(len(raw_osd_stamps) if raw_osd_stamps else (len(frames) if frames else 0)):
            if frame_idx < len(raw_osd_stamps) and raw_osd_stamps[frame_idx]:
                parsed = self.parse_iso_timestamp(raw_osd_stamps[frame_idx])
                if parsed:
                    adjusted = parsed + timedelta(seconds=clock_offset_sec)
                    normalized_stamps.append(adjusted.strftime("%Y-%m-%d %H:%M:%S"))
                    continue
            
            # Fallback interpolation based on frame index delta from base
            delta_frames = frame_idx - base_idx
            delta_sec = delta_frames / self.fps + clock_offset_sec
            adjusted = base_dt + timedelta(seconds=delta_sec)
            normalized_stamps.append(adjusted.strftime("%Y-%m-%d %H:%M:%S"))

        return {
            "clock_offset_seconds": float(clock_offset_sec),
            "anchors_found": anchors,
            "normalized_timestamps": normalized_stamps,
            "mode": mode,
        }
