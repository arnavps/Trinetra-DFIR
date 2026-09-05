"""
Unit tests for Engine 6 timeline normalizer, OSD timecode extraction, and visual anchor change-points.
"""

import pytest
import numpy as np

from app.engine6_timeline import osd_extractor, visual_anchor, normalizer


def test_visual_anchor_ambient_change_detection():
    """
    Tests classical CV ambient luminance frame differencing for change-point detection.
    """
    dark_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    bright_frame = np.ones((100, 100, 3), dtype=np.uint8) * 255

    frames = [dark_frame, dark_frame, bright_frame, bright_frame]
    anchors = visual_anchor.detect_luminance_anchors(frames, threshold=0.15)

    assert len(anchors) == 1
    assert anchors[0] == 2, f"Expected visual anchor at frame index 2, got {anchors}"


def test_timeline_normalizer_with_visual_anchor():
    """
    Tests TimelineNormalizer computing unified per-channel clock offset using visual anchor.
    """
    norm = normalizer.TimelineNormalizer(fps=25.0)

    raw_osd = [
        "2026-09-04 12:00:00",
        "2026-09-04 12:00:01",
        "2026-09-04 12:00:02",  # Anchor frame index 2 (OSD reads 12:00:02)
        "2026-09-04 12:00:03",
    ]

    dark_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    bright_frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
    frames = [dark_frame, dark_frame, bright_frame, bright_frame]

    # Ground truth reference at anchor frame 2 is 12:05:02 (out of sync by +300 seconds)
    result = norm.normalize_channel_clock(
        raw_osd_stamps=raw_osd,
        frames=frames,
        reference_anchor_frame=2,
        reference_real_timestamp="2026-09-04 12:05:02",
    )

    assert result["mode"] == "visual_anchor"
    assert result["clock_offset_seconds"] == 300.0
    assert len(result["normalized_timestamps"]) == 4
    assert result["normalized_timestamps"][2] == "2026-09-04 12:05:02"


def test_timeline_normalizer_degrade_to_osd_only():
    """
    Tests TimelineNormalizer degrading gracefully to OSD-only when no visual anchor is present.
    """
    norm = normalizer.TimelineNormalizer(fps=25.0)

    raw_osd = [
        "2026-09-04 12:00:00",
        "2026-09-04 12:00:01",
        "2026-09-04 12:00:02",
    ]

    # Flat luminance frames (no change-point)
    flat_frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
    frames = [flat_frame, flat_frame, flat_frame]

    result = norm.normalize_channel_clock(
        raw_osd_stamps=raw_osd,
        frames=frames,
    )

    assert result["mode"] == "osd_only"
    assert result["clock_offset_seconds"] == 0.0
    assert len(result["normalized_timestamps"]) == 3
    assert result["normalized_timestamps"][0] == "2026-09-04 12:00:00"
