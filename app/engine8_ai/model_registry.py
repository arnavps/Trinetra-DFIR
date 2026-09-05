"""
Loads ONNX weights and verifies each against models/manifest.json checksums before use;
refuses to load anything unverified or mismatched. Completely offline.
"""

import hashlib
import json
import os
from typing import Optional, Dict, Any
import onnxruntime as ort


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
    manifest = load_manifest()
    models_dict = manifest.get("models", {})
    if model_name not in models_dict:
        raise ValueError(f"Model '{model_name}' is not registered in models/manifest.json")
    
    expected_sha256 = models_dict[model_name].get("sha256")
    actual_sha256 = compute_file_sha256(model_file_path)
    return actual_sha256.lower() == expected_sha256.lower()


def load_onnx_session(model_name: str, custom_path: Optional[str] = None) -> ort.InferenceSession:
    """
    Verifies model against models/manifest.json checksum and loads ONNX InferenceSession (CPU execution provider only).
    Refuses to load unverified or checksum-mismatched weights. Never makes network requests.
    """
    if custom_path:
        model_path = custom_path
    else:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        model_path = os.path.join(root_dir, "models", model_name)
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file does not exist on disk: {model_path}")
    
    if not verify_model_checksum(model_name, model_path):
        raise RuntimeError(
            f"Checksum verification failed for model '{model_name}'. File at {model_path} does not match manifest.json!"
        )
    
    opts = ort.SessionOptions()
    opts.inter_op_num_threads = 1
    opts.intra_op_num_threads = 2
    session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
    return session
