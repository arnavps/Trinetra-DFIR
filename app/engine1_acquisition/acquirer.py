"""Orchestrates unidvr_rustcore to image a drive/existing file; writes AcquisitionResult (path, md5, sha256, merkle_root, timestamps) to the case DB via audit_log."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from app.engine1_acquisition.image_formats import write_dd_image
from app.engine1_acquisition.writeblock_check import verify_read_only
from app.engine7_case_db.audit_log import log_event


@dataclass
class AcquisitionResult:
    path: str
    md5: str
    sha256: str
    merkle_root: str
    byte_count: int
    started_at: str
    finished_at: str


def compute_hashes_python(filepath: str, chunk_size: int = 4 * 1024 * 1024):
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    leaf_hashes = []
    total_bytes = 0

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)
            sha256.update(chunk)
            leaf_hashes.append(hashlib.sha256(chunk).digest())
            total_bytes += len(chunk)

    if not leaf_hashes:
        merkle_root = hashlib.sha256(b"").hexdigest()
    else:
        current_layer = leaf_hashes
        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                if i + 1 < len(current_layer):
                    h = hashlib.sha256(current_layer[i] + current_layer[i + 1]).digest()
                else:
                    h = hashlib.sha256(current_layer[i] + current_layer[i]).digest()
                next_layer.append(h)
            current_layer = next_layer
        merkle_root = current_layer[0].hex()

    return md5.hexdigest(), sha256.hexdigest(), merkle_root, total_bytes


def acquire_image(source_path: str, dest_path: str, case_id: str, db_path: str = "case.db") -> AcquisitionResult:
    # 1. Verify source handle is read-only
    verify_read_only(source_path)

    started_at = datetime.now(timezone.utc).isoformat()

    # 2. Log ACQUISITION_START
    log_event(
        db_path=db_path,
        case_id=case_id,
        event_type="ACQUISITION_START",
        details={"source_path": source_path, "dest_path": dest_path, "started_at": started_at}
    )

    # 3. Write .dd raw image
    write_dd_image(source_path, dest_path)

    # 4. Compute hashes via Rust core if available, or Python fallback
    try:
        import unidvr_rustcore
        md5_hex, sha256_hex, merkle_root_hex, total_bytes = unidvr_rustcore.hash_file(dest_path)
    except (ImportError, Exception):
        md5_hex, sha256_hex, merkle_root_hex, total_bytes = compute_hashes_python(dest_path)

    finished_at = datetime.now(timezone.utc).isoformat()

    # 5. Log ACQUISITION_FINISH
    log_event(
        db_path=db_path,
        case_id=case_id,
        event_type="ACQUISITION_FINISH",
        details={
            "source_path": source_path,
            "dest_path": dest_path,
            "finished_at": finished_at,
            "byte_count": total_bytes,
        }
    )

    # 6. Log HASH_VERIFY
    log_event(
        db_path=db_path,
        case_id=case_id,
        event_type="HASH_VERIFY",
        details={
            "dest_path": dest_path,
            "md5": md5_hex,
            "sha256": sha256_hex,
            "merkle_root": merkle_root_hex,
        }
    )

    return AcquisitionResult(
        path=dest_path,
        md5=md5_hex,
        sha256=sha256_hex,
        merkle_root=merkle_root_hex,
        byte_count=total_bytes,
        started_at=started_at,
        finished_at=finished_at,
    )
