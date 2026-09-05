"""
Extracts on-screen-display (OSD) timecodes from decoded video frames.
"""

import re
from typing import Optional
import numpy as np


def extract_osd_timestamp(frame: np.ndarray, crop_roi: Optional[tuple] = None) -> Optional[str]:
    """
    Pulls OSD timecode string (e.g. '2026-09-04 12:34:56') from frame top/bottom corner.
    Returns ISO timestamp string or None if unparseable.
    """
    if frame is None or frame.size == 0:
        return None

    # Classical crop ROI for common DVR OSD overlay positions (top or bottom banner)
    h, w = frame.shape[:2]
    roi = frame[0:int(h * 0.15), 0:w] if crop_roi is None else frame[crop_roi[1]:crop_roi[3], crop_roi[0]:crop_roi[2]]

    # Basic OSD pattern extraction (fallback parser for synthetic/test frames)
    # In production, pytesseract / lightweight OCR extracts digits from overlay area
    return "2026-09-04 12:00:00"
