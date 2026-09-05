"""
Unit tests for SandboxRunner subprocess isolation wrapping parsers, carvers, and video decoders.
Verifies main application process remains intact when handling crafted or malformed streams.
"""

import os
import pytest

from app.security import sandbox


def test_sandbox_isolated_parser_execution(tmp_path):
    """
    Tests running parser inside sandbox.py subprocess with a malformed image.
    """
    malformed_image = os.path.join(tmp_path, "corrupted_disk.dd")
    with open(malformed_image, "wb") as f:
        f.write(b"CORRUPTED_MALFORMED_HEADER_BYTES_RANDOM_GARBAGE" * 100)

    runner = sandbox.SandboxRunner(timeout_sec=5)

    # Subprocess safely handles malformed image or carving fallback without crashing main process
    try:
        res = runner.run_parser_in_sandbox("GenericParser", malformed_image)
        assert "status" in res
        assert res["status"] == "ok"
    except sandbox.MalformedDataError as e:
        assert isinstance(e, sandbox.MalformedDataError)


def test_sandbox_isolated_decoder_execution():
    """
    Tests running decoder inside sandbox.py subprocess with a malformed video stream.
    """
    malformed_stream = b"\x00\x00\x00\x01\xefCRAFTED_MALFORMED_VIDEO_STREAM_ATTACK_VECTOR_GARBAGE"

    runner = sandbox.SandboxRunner(timeout_sec=5)

    # Subprocess safely intercepts malformed video stream without crashing main process
    try:
        res = runner.run_decoder_in_sandbox(malformed_stream)
        assert "status" in res
    except sandbox.MalformedDataError as e:
        assert isinstance(e, sandbox.MalformedDataError)
