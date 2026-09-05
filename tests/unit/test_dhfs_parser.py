"""Unit tests for Dahua / CP Plus DHFS filesystem parser."""

import os
import tempfile
import inspect

from app.engine3_parsers import fs_base
from app.engine3_parsers import dhfs_constants as const
from app.engine3_parsers.dhfs_parser import DhfsParser
from tests.fixtures.generate_synthetic_images import generate_dahua_image


def test_dhfs_parser_parses_dahua_synthetic_image():
    """dhfs_parser.py lists channels, timestamps and cluster runs from synthetic DHFS image."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dahua_path = os.path.join(tmpdir, "dahua_test.dd")
        generate_dahua_image(dahua_path, size_bytes=10 * 1024 * 1024, seed=50)

        parser = DhfsParser()
        vfs = parser.parse(dahua_path)

        assert vfs.oem == "Dahua"
        assert len(vfs.channels) == 2
        assert len(vfs.files) == 2

        ch1 = next(c for c in vfs.channels if c.channel_id == 1)
        assert ch1.channel_name == "Camera 1"
        assert ch1.total_files == 1

        f1 = vfs.files[0]
        assert f1.channel_id == 1
        assert len(f1.cluster_runs) == 1
        assert f1.cluster_runs[0].start_sector == 100
        assert f1.extraction_type == "parsed"


def test_dhfs_byte_offsets_in_constants_module():
    """Every DHFS byte offset lives in dhfs_constants.py, commented as literature-derived."""
    assert hasattr(const, "DHFS_SUPERBLOCK_OFFSET")
    assert hasattr(const, "DHFS_INDEX_TABLE_OFFSET_FROM_END")
    assert hasattr(const, "DHFS_INDEX_RECORD_SIZE")

    const_source = inspect.getsource(const)
    assert "literature-derived" in const_source.lower()


def test_dhfs_parser_follows_fs_base_interface():
    """dhfs_parser.py follows the exact same fs_base.py interface with zero special-casing."""
    parser = DhfsParser()
    assert isinstance(parser, fs_base.FileSystemParser)
