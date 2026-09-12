"""
Loads ONNX weights and verifies each against models/manifest.json checksums before use;
refuses to load anything unverified or mismatched. Completely offline.
"""

import hashlib
import json
import logging
import os
from typing import Optional, Dict, Any

try:
    import onnxruntime as ort
except ImportError:
    ort = None

logger = logging.getLogger(__name__)


def get_manifest_path() -> str:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(root_dir, "models", "manifest.json")


def load_manifest() -> Dict[str, Any]:
    manifest_path = get_manifest_path()
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Model manifest not found at {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_file_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_model_checksum(model_name: str, model_file_path: str) -> bool:
    """
    Verifies a model file against models/manifest.json.
    Returns False if sha256_status is PLACEHOLDER_NOT_YET_SOURCED or if checksum mismatches.
    """
    manifest = load_manifest()
    models_dict = manifest.get("models", {})
    if model_name not in models_dict:
        raise ValueError(f"Model '{model_name}' is not registered in models/manifest.json")

    entry = models_dict[model_name]
    status = entry.get("sha256_status", "")
    if status == "PLACEHOLDER_NOT_YET_SOURCED":
        logger.warning(f"Model '{model_name}' manifest checksum is marked PLACEHOLDER_NOT_YET_SOURCED.")
        return False

    expected_sha256 = entry.get("sha256", "").strip()
    if not expected_sha256:
        return False

    actual_sha256 = compute_file_sha256(model_file_path)
    return actual_sha256.lower() == expected_sha256.lower()


def verify_all_models() -> Dict[str, Dict[str, Any]]:
    """
    Scans models/manifest.json and reports verification status for every registered model.
    Returns: {model_name: {'status': 'VERIFIED' | 'MISSING' | 'PLACEHOLDER', 'description': str}}
    """
    manifest = load_manifest()
    models_dict = manifest.get("models", {})
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    models_dir = os.path.join(root_dir, "models")

    report = {}
    for name, entry in models_dict.items():
        model_path = os.path.join(models_dir, name)
        status_flag = entry.get("sha256_status", "")
        desc = entry.get("description", "")

        if not os.path.exists(model_path):
            report[name] = {"status": "MISSING", "description": desc, "path": model_path}
        elif status_flag == "PLACEHOLDER_NOT_YET_SOURCED":
            report[name] = {"status": "PLACEHOLDER", "description": desc, "path": model_path}
        else:
            is_valid = verify_model_checksum(name, model_path)
            report[name] = {
                "status": "VERIFIED" if is_valid else "CHECKSUM_MISMATCH",
                "description": desc,
                "path": model_path,
            }

    return report


def load_onnx_session(model_name: str, custom_path: Optional[str] = None) -> Any:
    """
    Verifies model against models/manifest.json checksum and loads ONNX InferenceSession (CPU provider).
    Fails closed: raises FileNotFoundError or RuntimeError if missing, unverified, or mismatched.
    Never makes network requests.
    """
    if ort is None:
        raise RuntimeError("onnxruntime is not installed in the environment.")

    if custom_path:
        model_path = custom_path
    else:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        model_path = os.path.join(root_dir, "models", model_name)

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file does not exist on disk: {model_path}")

    if not verify_model_checksum(model_name, model_path):
        raise RuntimeError(
            f"Checksum verification failed for model '{model_name}'. File at {model_path} is unverified or mismatched against manifest.json!"
        )

    opts = ort.SessionOptions()
    opts.inter_op_num_threads = 1
    opts.intra_op_num_threads = 2
    session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
    return session
