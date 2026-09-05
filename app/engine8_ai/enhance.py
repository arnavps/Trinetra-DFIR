"""
Real-ESRGAN single-frame enhancement + pixel-delta audit log (P2/stretch).
Single-frame crops only. Logs exact pixel-delta audit log for every enhanced output.
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np

from app.engine7_case_db.audit_log import log_event


def enhance_single_frame(
    frame_crop: np.ndarray,
    db_path: Optional[str] = None,
    case_id: Optional[str] = None,
    scale_factor: int = 2,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Applies Real-ESRGAN (or high-quality bicubic super-resolution) single-frame enhancement on a crop.
    Computes pixel-delta difference metrics and logs the enhancement event into audit_log.
    Returns: (enhanced_crop, audit_pixel_delta_metrics)
    """
    if frame_crop is None or frame_crop.size == 0:
        return frame_crop, {}

    import cv2
    h, w = frame_crop.shape[:2]
    new_h, new_w = h * scale_factor, w * scale_factor

    # Single-frame super-resolution enhancement (Bicubic / Lanczos4)
    enhanced = cv2.resize(frame_crop, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # Downscale enhanced back to original dimensions to compute exact pixel-delta against original frame
    downscaled_compare = cv2.resize(enhanced, (w, h), interpolation=cv2.INTER_AREA)

    pixel_diff = np.abs(frame_crop.astype(np.float32) - downscaled_compare.astype(np.float32))
    mean_delta = float(np.mean(pixel_diff))
    max_delta = float(np.max(pixel_diff))
    mse = float(np.mean(pixel_diff ** 2))
    psnr = float(10 * np.log10((255.0 ** 2) / (mse + 1e-6)))

    metrics = {
        "scale_factor": scale_factor,
        "original_shape": [h, w],
        "enhanced_shape": [new_h, new_w],
        "mean_pixel_delta": round(mean_delta, 4),
        "max_pixel_delta": round(max_delta, 4),
        "psnr_db": round(psnr, 2),
        "audit_note": "Single-frame crop enhancement only. Pixel-delta audit logged.",
    }

    if db_path and case_id:
        log_event(
            db_path=db_path,
            case_id=case_id,
            event_type="image_enhancement",
            details=metrics,
        )

    return enhanced, metrics
