"""Unit tests for native StreamDecoder, depacketizer, PySide6 VideoTileWidget, and no-mp4/mkv file assertion."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import glob
import tempfile
import numpy as np
import pytest

from app.engine5_playback.decoder import StreamDecoder
from app.engine5_playback.depacketizer import depacketize_stream
from app.engine3_parsers.hikfat_parser import HikFatParser
from app.engine3_parsers.dhfs_parser import DhfsParser
from tests.fixtures.generate_synthetic_images import generate_dahua_image, generate_hikvision_image

try:
    from PySide6.QtWidgets import QApplication
    from app.engine9_ui.widgets.video_tile import VideoTileWidget
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False


@pytest.fixture(scope="module")
def qapp():
    """Provides a singleton QApplication instance for PySide6 widget tests."""
    if not PYSIDE6_AVAILABLE:
        return None
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_native_playback_and_decode_dahua_and_hikvision(qapp):
    """A synthetic clip from BOTH Hikvision and Dahua images can be played back directly in original format via decoder.py and VideoTileWidget."""
    with tempfile.TemporaryDirectory() as case_dir:
        dahua_img = os.path.join(case_dir, "dahua_case.dd")
        hik_img = os.path.join(case_dir, "hik_case.dd")

        generate_dahua_image(dahua_img, size_bytes=10 * 1024 * 1024, seed=12)
        generate_hikvision_image(hik_img, size_bytes=10 * 1024 * 1024, seed=34)

        # 1. Test Dahua decoding
        dh_vfs = DhfsParser().parse(dahua_img)
        assert len(dh_vfs.files) > 0
        dh_file = dh_vfs.files[0]
        start_sec = dh_file.cluster_runs[0].start_sector
        sec_cnt = dh_file.cluster_runs[0].sector_count

        with open(dahua_img, "rb") as f:
            f.seek(start_sec * 512)
            dh_stream_bytes = f.read(sec_cnt * 512)

        dh_decoder = StreamDecoder(dh_stream_bytes, oem="Dahua")
        assert dh_decoder.get_frame_count() > 0
        frame0 = dh_decoder.read_frame(0)
        assert isinstance(frame0, np.ndarray)
        assert frame0.shape[2] == 3

        # 2. Test Hikvision decoding
        hik_vfs = HikFatParser().parse(hik_img)
        assert len(hik_vfs.files) > 0
        hik_file = hik_vfs.files[0]
        start_sec_h = hik_file.cluster_runs[0].start_sector
        sec_cnt_h = hik_file.cluster_runs[0].sector_count

        with open(hik_img, "rb") as f:
            f.seek(start_sec_h * 512)
            hik_stream_bytes = f.read(sec_cnt_h * 512)

        hik_decoder = StreamDecoder(hik_stream_bytes, oem="Hikvision")
        assert hik_decoder.get_frame_count() > 0
        frame_hik0 = hik_decoder.read_frame(0)
        assert isinstance(frame_hik0, np.ndarray)

        # 3. Test VideoTileWidget native UI rendering if PySide6 is available
        if PYSIDE6_AVAILABLE:
            tile = VideoTileWidget()
            count = tile.load_stream(dh_stream_bytes, oem="Dahua")
            assert count > 0
            assert tile.render_frame_at(0) is True

        # 4. EXPLICIT ASSERTION: No *.mp4 or *.mkv files exist anywhere in the case directory
        mp4_files = glob.glob(os.path.join(case_dir, "**", "*.mp4"), recursive=True)
        mkv_files = glob.glob(os.path.join(case_dir, "**", "*.mkv"), recursive=True)
        assert len(mp4_files) == 0
        assert len(mkv_files) == 0


def test_no_mp4_mkv_in_workspace():
    """Asserts no *.mp4 or *.mkv file exists on primary evidentiary path (excluding derivative export folders)."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    all_mp4 = glob.glob(os.path.join(repo_root, "**", "*.mp4"), recursive=True)
    all_mkv = glob.glob(os.path.join(repo_root, "**", "*.mkv"), recursive=True)

    primary_mp4 = [f for f in all_mp4 if "demo_case" not in f and "derivatives" not in f and not os.path.basename(f).startswith("export_")]
    primary_mkv = [f for f in all_mkv if "demo_case" not in f and "derivatives" not in f and not os.path.basename(f).startswith("export_")]

    assert len(primary_mp4) == 0, f"Found unexpected MP4 files on primary path: {primary_mp4}"
    assert len(primary_mkv) == 0, f"Found unexpected MKV files on primary path: {primary_mkv}"
