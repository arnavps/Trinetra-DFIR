"""
QP-discontinuity / duplicate-GOP statistical anomaly checks (deterministic, not ML — Blueprint §3.2-J).
Exposes clip-level video frame tampering analysis and logs flagged anomalies to audit_log.
"""

import hashlib
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from app.engine7_case_db.audit_log import log_event


def calculate_frame_hash(frame: np.ndarray) -> str:
    """Computes SHA-256 digest of raw frame buffer."""
    if frame is None or frame.size == 0:
        return "empty"
    return hashlib.sha256(frame.tobytes()).hexdigest()


def analyze_tamper_and_discontinuities(
    frames: List[np.ndarray],
    qp_values: Optional[List[int]] = None,
    db_path: Optional[str] = None,
    case_id: Optional[str] = None,
    qp_threshold: int = 15,
) -> Dict[str, Any]:
    """
    Performs deterministic anti-splicing analysis on video frame sequence:
    1. QP (Quantization Parameter) Discontinuity Detection (delta > qp_threshold).
    2. Duplicate GOP / Duplicate Frame Anomaly Detection.
    Logs flagged discontinuities to audit_log with frame indices and numeric thresholds.
    Returns audit metrics dictionary.
    """
    flagged_anomalies: List[Dict[str, Any]] = []
    
    # 1. Duplicate Frame & Duplicate GOP Detection
    seen_hashes: Dict[str, int] = {}
    duplicate_frames: List[Tuple[int, int]] = []
    
    for idx, frame in enumerate(frames):
        f_hash = calculate_frame_hash(frame)
        if f_hash in seen_hashes:
            prev_idx = seen_hashes[f_hash]
            duplicate_frames.append((prev_idx, idx))
            flagged_anomalies.append({
                "type": "DUPLICATE_FRAME_GOP_ANOMALY",
                "original_frame_index": prev_idx,
                "duplicate_frame_index": idx,
                "description": f"Identical frame payload detected at frame {idx} (matches frame {prev_idx}). Possible GOP duplication or video splicing.",
            })
        else:
            seen_hashes[f_hash] = idx

    # 2. QP Discontinuity Detection
    qp_discontinuities: List[Dict[str, Any]] = []
    if qp_values and len(qp_values) > 1:
        for idx in range(1, len(qp_values)):
            delta = abs(qp_values[idx] - qp_values[idx - 1])
            if delta >= qp_threshold:
                anom = {
                    "type": "QP_DISCONTINUITY",
                    "frame_index": idx,
                    "previous_qp": qp_values[idx - 1],
                    "current_qp": qp_values[idx],
                    "qp_delta": delta,
                    "threshold": qp_threshold,
                    "description": f"QP jump of {delta} at frame {idx} exceeds threshold {qp_threshold}. Potential compression seam or spliced segment.",
                }
                qp_discontinuities.append(anom)
                flagged_anomalies.append(anom)

    is_tampered = len(flagged_anomalies) > 0

    metrics = {
        "is_tampered": is_tampered,
        "total_frames_analyzed": len(frames),
        "flagged_anomalies_count": len(flagged_anomalies),
        "duplicate_frame_pairs": duplicate_frames,
        "qp_discontinuities": qp_discontinuities,
        "anomalies_list": flagged_anomalies,
    }

    if db_path and case_id and is_tampered:
        log_event(
            db_path=db_path,
            case_id=case_id,
            event_type="tamper_discontinuity_detected",
            details=metrics,
        )

    return metrics
