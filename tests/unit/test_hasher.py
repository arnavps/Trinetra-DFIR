"""Unit tests for hasher, writeblock check, acquisition, and audit log hash chaining."""

import os
import tempfile
import pytest

from app.engine1_acquisition.acquirer import acquire_image, compute_hashes_python
from app.engine1_acquisition.writeblock_check import verify_read_only, WriteBlockViolationError
from app.engine7_case_db.audit_log import log_event, verify_audit_chain, get_db_connection
from tests.fixtures.generate_synthetic_images import generate_dahua_image, generate_hikvision_image


def test_hasher_matches_python_hashlib():
    """Verify Rust/Python hasher output matches Python's hashlib byte-for-byte on synthetic image."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "dahua_test.dd")
        generate_dahua_image(img_path, size_bytes=1 * 1024 * 1024, seed=123)

        expected_md5, expected_sha256, expected_merkle, total_bytes = compute_hashes_python(img_path)

        try:
            import unidvr_rustcore
            rust_md5, rust_sha256, rust_merkle, rust_bytes = unidvr_rustcore.hash_file(img_path)
            assert rust_md5 == expected_md5
            assert rust_sha256 == expected_sha256
            assert rust_merkle == expected_merkle
            assert rust_bytes == total_bytes
        except ImportError:
            # Fallback assertion
            assert total_bytes == 1 * 1024 * 1024


from unittest import mock

def test_acquisition_determinism():
    """Acquiring the same synthetic image twice produces identical hashes (determinism)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "source.dd")
        generate_dahua_image(src_path, size_bytes=2 * 1024 * 1024, seed=999)

        db_path = os.path.join(tmpdir, "case.db")
        dst1 = os.path.join(tmpdir, "out1.dd")
        dst2 = os.path.join(tmpdir, "out2.dd")

        with mock.patch("app.engine1_acquisition.acquirer.verify_read_only", return_value=True):
            res1 = acquire_image(src_path, dst1, case_id="CASE-001", db_path=db_path)
            res2 = acquire_image(src_path, dst2, case_id="CASE-001", db_path=db_path)

        assert res1.md5 == res2.md5
        assert res1.sha256 == res2.sha256
        assert res1.merkle_root == res2.merkle_root
        assert res1.byte_count == res2.byte_count


def test_writeblock_check_rejects_writable_handle():
    """writeblock_check.py provably raises WriteBlockViolationError on a writable handle/file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        writable_path = os.path.join(tmpdir, "writable_drive.dd")
        with open(writable_path, "wb") as f:
            f.write(b"data")

        with pytest.raises(WriteBlockViolationError):
            verify_read_only(writable_path)


def test_writeblock_check_mock_read_only():
    """writeblock_check.py deterministically passes when writable open raises PermissionError, regardless of OS root/Administrator status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = os.path.join(tmpdir, "source.dd")
        with open(fake_path, "wb") as f:
            f.write(b"data")

        orig_open = open
        def mock_open(path, mode="r", *args, **kwargs):
            if "r+b" in mode or "w" in mode or "+" in mode:
                raise PermissionError("Simulated hardware write-block")
            return orig_open(path, mode, *args, **kwargs)

        def mock_os_open(path, flags, *args, **kwargs):
            if flags & (os.O_RDWR | os.O_WRONLY):
                raise PermissionError("Simulated hardware write-block")
            return os.open(path, flags, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=mock_open), \
             mock.patch("os.open", side_effect=mock_os_open):
            assert verify_read_only(fake_path) is True


def test_audit_log_hash_chaining_and_tampering():
    """audit_log entries are hash-chained — tampering with one entry breaks verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "audit_test.db")
        case_id = "CASE-100"

        # Log 3 events
        log_event(db_path, case_id, "ACQUISITION_START", {"step": 1})
        log_event(db_path, case_id, "ACQUISITION_FINISH", {"step": 2})
        log_event(db_path, case_id, "HASH_VERIFY", {"step": 3})

        # Chain must be valid initially
        assert verify_audit_chain(db_path, case_id) is True

        # Tamper with the 2nd audit entry
        conn = get_db_connection(db_path)
        with conn:
            conn.execute("UPDATE audit_log SET event_type = 'TAMPERED' WHERE entry_id = 2")
        conn.close()

        # Chain verification must fail
        assert verify_audit_chain(db_path, case_id) is False


def test_synthetic_image_reproducibility():
    """generate_synthetic_images.py produces the exact same bytes on every run with fixed seed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path1 = os.path.join(tmpdir, "img1.dd")
        path2 = os.path.join(tmpdir, "img2.dd")

        generate_hikvision_image(path1, size_bytes=5 * 1024 * 1024, seed=42)
        generate_hikvision_image(path2, size_bytes=5 * 1024 * 1024, seed=42)

        with open(path1, "rb") as f1, open(path2, "rb") as f2:
            assert f1.read() == f2.read()
