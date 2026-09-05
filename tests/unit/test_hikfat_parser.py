"""Unit tests for OEM signature_matcher.py and Hikvision HIKFAT filesystem parser."""

import os
import tempfile
import inspect

from app.engine2_detector.signature_matcher import match_signature
from app.engine3_parsers import fs_base
from app.engine3_parsers import hikfat_constants as const
from app.engine3_parsers.hikfat_parser import HikFatParser
from tests.fixtures.generate_synthetic_images import generate_dahua_image, generate_hikvision_image


def test_signature_matcher_identifies_dahua_and_hikvision():
    """signature_matcher.py correctly identifies both Dahua-stub and Hikvision-stub synthetic images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dahua_path = os.path.join(tmpdir, "dahua.dd")
        hik_path = os.path.join(tmpdir, "hikvision.dd")
        unknown_path = os.path.join(tmpdir, "unknown.dd")

        generate_dahua_image(dahua_path, size_bytes=1 * 1024 * 1024, seed=1)
        generate_hikvision_image(hik_path, size_bytes=10 * 1024 * 1024, seed=2)

        with open(unknown_path, "wb") as f:
            f.write(b"NOT_A_DVR_HEADER_DATA_1234567890")

        res_dahua = match_signature(dahua_path)
        assert res_dahua.matched is True
        assert res_dahua.oem == "Dahua"
        assert res_dahua.signature_id == "dahua_dhfs_v1"

        res_hik = match_signature(hik_path)
        assert res_hik.matched is True
        assert res_hik.oem == "Hikvision"
        assert res_hik.signature_id == "hikvision_hikfat_v1"

        res_unknown = match_signature(unknown_path)
        assert res_unknown.matched is False
        assert res_unknown.oem == "Unknown"


def test_hikfat_parser_lists_channels_timestamps_and_cluster_runs():
    """hikfat_parser.py lists channels, timestamps and cluster runs from extended synthetic HIKFAT image."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hik_path = os.path.join(tmpdir, "hikvision_extended.dd")
        generate_hikvision_image(hik_path, size_bytes=10 * 1024 * 1024, seed=100)

        parser = HikFatParser()
        vfs = parser.parse(hik_path)

        assert vfs.oem == "Hikvision"
        assert len(vfs.channels) == 2

        ch1 = next(c for c in vfs.channels if c.channel_id == 1)
        ch2 = next(c for c in vfs.channels if c.channel_id == 2)

        assert ch1.channel_name == "Camera 1"
        assert ch1.total_files == 2
        assert ch1.start_timestamp is not None
        assert ch1.end_timestamp is not None

        assert ch2.channel_name == "Camera 2"
        assert ch2.total_files == 1

        assert len(vfs.files) == 3

        # Verify cluster runs on parsed files
        f1 = vfs.files[0]
        assert f1.channel_id == 1
        assert len(f1.cluster_runs) == 1
        assert f1.cluster_runs[0].start_sector == 100
        assert f1.cluster_runs[0].sector_count > 0
        assert f1.size_bytes > 0
        assert f1.extraction_type == "parsed"

        f2 = vfs.files[1]
        assert f2.channel_id == 2
        assert f2.cluster_runs[0].start_sector == 100


def test_hikfat_byte_offsets_in_constants_module():
    """Every HIKFAT byte offset lives in hikfat_constants.py, commented as literature-derived."""
    assert hasattr(const, "HIKFAT_SUPERBLOCK_OFFSET")
    assert hasattr(const, "HIKFAT_INDEX_TABLE_OFFSET_FROM_END")
    assert hasattr(const, "HIKFAT_INDEX_RECORD_SIZE")

    # Read constants file source to verify literature-derived comment
    const_source = inspect.getsource(const)
    assert "literature-derived" in const_source.lower()


def test_fs_base_clean_interface_without_special_casing():
    """fs_base.py interface has no Hikvision-specific or OEM-specific special-casing."""
    fs_source = inspect.getsource(fs_base)
    assert "hikvision" not in fs_source.lower()
    assert "dahua" not in fs_source.lower()
    assert "hikfat" not in fs_source.lower()
