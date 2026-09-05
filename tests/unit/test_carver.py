"""Unit tests for frame carver, generic parser, fallback classifier, and no-repackaging assertions."""

import os
import tempfile
from app.engine2_detector.signature_matcher import match_signature
from app.engine2_detector.fallback_classifier import FallbackClassifier
from app.engine3_parsers.generic_parser import GenericParser
from app.engine4_carver.frame_carver import carve_nal_units, find_nal_start_codes
from app.engine4_carver.gop_reconstructor import reassemble_gop_fragments
from tests.fixtures.generate_synthetic_images import generate_unknown_oem_image, create_tiny_h264_stream


def test_generic_parser_routes_unknown_oem_and_tags_carved_fragment():
    """A third, undetected-OEM synthetic image is routed to generic_parser.py and tagged extraction_type='carved_fragment'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        unknown_img = os.path.join(tmpdir, "unknown_oem.dd")
        generate_unknown_oem_image(unknown_img, size_bytes=5 * 1024 * 1024, seed=88)

        match_res = match_signature(unknown_img)
        assert match_res.matched is False
        assert match_res.oem == "Unknown"

        parser = GenericParser()
        vfs = parser.parse(unknown_img)

        assert "Carved" in vfs.oem
        assert len(vfs.files) > 0
        assert vfs.files[0].extraction_type == "carved_fragment"
        assert "Carved / Best-Effort" in vfs.channels[0].channel_name


def test_carver_output_byte_identical_no_repackaging():
    """Carved output is verified byte-identical to what frame_carver scanned — no container repackaging step exists."""
    raw_payload = create_tiny_h264_stream(num_frames=3)
    
    offsets = find_nal_start_codes(raw_payload)
    assert len(offsets) > 0
    scanned_nal_stream = raw_payload[offsets[0]:]

    # Run NAL carving and GOP reassembly
    nal_units = carve_nal_units(scanned_nal_stream)
    assert len(nal_units) > 0

    gop_fragments = reassemble_gop_fragments(nal_units)
    assert len(gop_fragments) > 0

    reconstructed_bytes = b"".join(gop_fragments)

    # Verify carved elementary stream output matches input scanned NAL bytes with zero container repackaging
    assert reconstructed_bytes == scanned_nal_stream


def test_fallback_classifier_returns_reasoning_and_manual_flag():
    """fallback_classifier.py always returns confidence + reasoning string and requires_manual_verification flag."""
    classifier = FallbackClassifier()
    dummy_sector = b"DHFS" + b"\x00" * 508

    res = classifier.predict(dummy_sector)
    assert "confidence" in res
    assert isinstance(res["confidence"], float)
    assert "reasoning" in res
    assert isinstance(res["reasoning"], str) and len(res["reasoning"]) > 0
    assert res.get("requires_manual_verification") is True
