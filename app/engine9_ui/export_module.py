"""
Investigator-triggered export of a case clip to MP4/MKV via engine5_playback.remuxer.
HARD EVIDENTIARY BOUNDARY:
- Computes an independent hash for the derivative export file (never equivalent to original evidence hash)
- Logs an audit entry explicitly tagged as a non-evidentiary derivative export
- Surfaces the mandatory label 'convenience copy - not for submission as primary evidence'
"""

import hashlib
import os
from typing import Dict, Any

from app.engine5_playback.remuxer import remux_to_mp4
from app.engine7_case_db.audit_log import log_event


CONVENIENCE_COPY_LABEL: str = "convenience copy - not for submission as primary evidence"


def compute_file_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def export_derivative_clip(
    db_path: str,
    case_id: str,
    input_raw_path: str,
    output_export_path: str,
) -> Dict[str, Any]:
    """
    Executes investigator-triggered export of a clip into MP4/MKV container.
    Computes an independent hash and logs a non-evidentiary derivative export audit event.
    """
    if not os.path.exists(input_raw_path):
        raise FileNotFoundError(f"Input stream file not found: {input_raw_path}")

    # Remux stream via remuxer.py (the single authorized caller site)
    remux_to_mp4(input_raw_path, output_export_path)

    # Compute independent hash for the newly generated derivative file
    export_hash = compute_file_sha256(output_export_path)
    file_size = os.path.getsize(output_export_path)

    # Log non-evidentiary derivative export audit entry
    log_event(
        db_path=db_path,
        case_id=case_id,
        event_type="derivative_export",
        details={
            "output_path": output_export_path,
            "export_hash": export_hash,
            "size_bytes": file_size,
            "label": CONVENIENCE_COPY_LABEL,
            "notice": "Derivative export file created on explicit investigator action. Non-evidentiary copy.",
        },
    )

    return {
        "export_path": output_export_path,
        "export_hash": export_hash,
        "size_bytes": file_size,
        "label": CONVENIENCE_COPY_LABEL,
    }
