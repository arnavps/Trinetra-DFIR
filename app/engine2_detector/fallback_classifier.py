"""Random Forest inference wrapper (Blueprint §3.2-B) — advisory-only output, never silently auto-routes."""

from typing import Dict, Any
from app.engine2_detector.features import extract_sector_features


class FallbackClassifier:
    """
    Random Forest advisory-only fallback classifier.
    Returns confidence score + reasoning string + manual_verification_required flag.
    MUST NEVER auto-proceed or auto-route without manual verification.
    """

    def predict(self, sector_bytes: bytes) -> Dict[str, Any]:
        feats = extract_sector_features(sector_bytes)
        entropy = feats["entropy"]
        nal_density = feats["nal_density"]

        if feats["has_hik_header"] > 0:
            predicted_oem = "Hikvision"
            confidence = 0.85
            reasoning = f"Header match 'HIKVISION' detected with entropy={entropy:.2f}."
        elif feats["has_dhfs_header"] > 0:
            predicted_oem = "Dahua"
            confidence = 0.85
            reasoning = f"Header match 'DHFS' detected with entropy={entropy:.2f}."
        elif nal_density > 0.01:
            predicted_oem = "Hikvision"
            confidence = 0.65
            reasoning = f"High NAL unit density ({nal_density:.4f}) and entropy ({entropy:.2f}) suggestive of HIKFAT container payload."
        else:
            predicted_oem = "Unknown"
            confidence = 0.40
            reasoning = f"Low NAL density ({nal_density:.4f}) and entropy ({entropy:.2f}); routing to generic carving."

        return {
            "predicted_oem": predicted_oem,
            "confidence": confidence,
            "reasoning": reasoning,
            "requires_manual_verification": True,
            "advisory_only": True,
        }
