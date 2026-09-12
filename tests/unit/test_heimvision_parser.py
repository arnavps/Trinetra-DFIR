"""Unit tests for Engine 3 HeimVision filesystem parser plugin (heimvision_parser.py)."""

import os
import pytest
from app.engine3_parsers import fs_base
from app.engine3_parsers import heimvision_constants as const
from app.engine3_parsers.heimvision_parser import HeimVisionParser
from tests.fixtures.generate_synthetic_images import generate_heimvision_image


def test_heimvision_parser_superblock_validation(tmp_path):
    img_path = os.path.join(tmp_path, "heim_test.dd")
    generate_heimvision_image(img_path, size_bytes=5 * 1024 * 1024)

    parser = HeimVisionParser()
    vfs = parser.parse(img_path)

    assert isinstance(vfs, fs_base.VirtualFileSystem)
    assert vfs.oem == "HeimVision"
    assert len(vfs.channels) == 2
    assert len(vfs.files) == 2
    assert vfs.files[0].file_id == "HEIM_CH1_0001"
    assert vfs.files[0].extraction_type == "parsed"


def test_heimvision_parser_corrupt_signature_raises(tmp_path):
    img_path = os.path.join(tmp_path, "corrupt_heim.dd")
    with open(img_path, "wb") as f:
        f.write(b"BADSIGNATURE_NOT_HEIMVISION_PADDING_DATA")

    parser = HeimVisionParser()
    with pytest.raises(ValueError, match="Invalid HeimVision superblock signature"):
        parser.parse(img_path)
