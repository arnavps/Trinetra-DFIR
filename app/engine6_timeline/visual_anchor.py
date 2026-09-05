"""
Frame-differencing / histogram change-point detector for ambient-light drift calibration
(classical CV, not ML — Blueprint §3.2-K).
"""

from typing import List
import numpy as np


def detect_luminance_anchors(frames: List[np.ndarray], threshold: float = 0.15) -> List[int]:
    """
    Analyzes ambient scene luminance across consecutive frames using mean luminance diffs
    and HSV histogram correlation to identify visual anchor change-points (e.g. light switches, flashes).
    Returns a list of frame indices corresponding to visual change-point anchors.
    """
    if not frames or len(frames) < 2:
        return []

    import cv2
    anchors = []
    prev_lum = None
    prev_hist = None

    for idx, frame in enumerate(frames):
        if frame is None or frame.size == 0:
            continue

        # Convert to HSV and extract V (luminance/value) channel
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        mean_lum = float(np.mean(v_channel))

        # Compute 1D luminance histogram
        hist = cv2.calcHist([v_channel], [0], None, [32], [0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

        if prev_lum is not None and prev_hist is not None:
            lum_diff = abs(mean_lum - prev_lum) / 255.0
            hist_sim = float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL))
            hist_diff = 1.0 - max(0.0, hist_sim)

            # Combined change-point metric
            change_score = (lum_diff * 0.6) + (hist_diff * 0.4)
            if change_score >= threshold:
                anchors.append(idx)

        prev_lum = mean_lum
        prev_hist = hist

    return anchors
