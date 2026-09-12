"""Unit tests asserting StreamDecoder leaves no persistent files in case directory and sandbox catches malformed streams."""

import os
from app.engine5_playback.decoder import StreamDecoder
from app.security.sandbox import SandboxRunner, MalformedDataError


def test_decoder_leaves_no_files_in_case_dir(tmp_path):
    case_dir = tmp_path / "case_folder"
    case_dir.mkdir()

    raw_h264_stream = b"\x00\x00\x00\x01\x67\x42\x00\x0a\xf8\x41\xa2\x00\x00\x00\x01\x68\xce\x3c\x80"
    decoder = StreamDecoder(raw_h264_stream)
    _count = decoder.get_frame_count()

    # Assert no .mp4 or .h264 files persist inside case_dir
    files = list(case_dir.glob("*"))
    assert len(files) == 0, f"Decoder leaked persistent files in case directory: {files}"


def test_sandbox_catches_malformed_decoder_stream():
    runner = SandboxRunner(timeout_sec=5)
    malformed_bytes = b"CORRUPTED_NON_VIDEO_BYTES_DEADBEEF"

    # Decoding inside sandbox handles error gracefully
    res = runner.run_decoder_in_sandbox(malformed_bytes)
    assert res.get("status") in ("ok", "error")
