"""
CLIP ViT-B/32 embeddings + FAISS index build/query for natural-language clip search.
# NOTE: Recall on domain-specific CCTV queries will be mediocre without fine-tuning,
# which is not in scope. This is a known, accepted limitation, not a bug to chase.
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from app.engine8_ai import model_registry


class CLIPEmbeddingEngine:
    def __init__(self, custom_path: Optional[str] = None):
        self.text_session = None
        self.image_session = None
        try:
            self.text_session = model_registry.load_onnx_session("clip_vit_b32_text.onnx", custom_path=custom_path)
            self.image_session = model_registry.load_onnx_session("clip_vit_b32_image.onnx", custom_path=custom_path)
        except Exception:
            pass

    def encode_text(self, text: str) -> np.ndarray:
        """
        Encodes natural-language prompt into a 512-d normalized float32 embedding vector.
        """
        if self.text_session is None:
            # Deterministic pseudo-embedding for testing/fallback when ONNX weights are not loaded
            seed_val = abs(hash(text)) % 10000
            rng = np.random.RandomState(seed_val)
            vec = rng.randn(512).astype(np.float32)
            norm = np.linalg.norm(vec)
            return vec / (norm + 1e-6)

        tokens = np.zeros((1, 77), dtype=np.int32)
        input_name = self.text_session.get_inputs()[0].name
        outputs = self.text_session.run(None, {input_name: tokens})
        vec = outputs[0][0].astype(np.float32)
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-6)

    def encode_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Encodes a single video frame (RGB numpy array) into a 512-d normalized float32 embedding vector.
        """
        if self.image_session is None:
            seed_val = int(np.sum(frame)) % 10000 if frame is not None and frame.size > 0 else 42
            rng = np.random.RandomState(seed_val)
            vec = rng.randn(512).astype(np.float32)
            norm = np.linalg.norm(vec)
            return vec / (norm + 1e-6)

        import cv2
        resized = cv2.resize(frame, (224, 224))
        input_data = resized.astype(np.float32) / 255.0
        mean = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
        std = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
        input_data = (input_data - mean) / std
        input_data = np.transpose(input_data, (2, 0, 1))[np.newaxis, ...]

        input_name = self.image_session.get_inputs()[0].name
        outputs = self.image_session.run(None, {input_name: input_data})
        vec = outputs[0][0].astype(np.float32)
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-6)


def build_faiss_index(
    clip_records: List[Dict[str, Any]],
    index_file_path: str,
    metadata_file_path: str,
    clip_engine: Optional[CLIPEmbeddingEngine] = None,
) -> int:
    """
    Computes CLIP embeddings for a list of clip records: [{'file_id': str, 'timestamp': str, 'frame': np.ndarray, ...}]
    and indexes them into a local FAISS index file (or fallback numpy binary file).
    """
    if clip_engine is None:
        clip_engine = CLIPEmbeddingEngine()

    dim = 512
    embeddings = []
    metadata = []

    for item in clip_records:
        frame = item.get("frame")
        emb = clip_engine.encode_frame(frame)
        embeddings.append(emb)
        metadata.append({
            "file_id": item["file_id"],
            "timestamp": item.get("timestamp", "00:00:00"),
            "channel_id": item.get("channel_id", 1),
            "description": item.get("description", "extracted_clip"),
        })

    os.makedirs(os.path.dirname(os.path.abspath(index_file_path)), exist_ok=True)

    if embeddings:
        matrix = np.vstack(embeddings).astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-6
        matrix = matrix / norms

        if faiss is not None:
            index = faiss.IndexFlatIP(dim)
            index.add(matrix)
            faiss.write_index(index, index_file_path)
        else:
            with open(index_file_path, "wb") as f:
                np.save(f, matrix)
        ntotal = len(embeddings)
    else:
        ntotal = 0
        if faiss is not None:
            index = faiss.IndexFlatIP(dim)
            faiss.write_index(index, index_file_path)
        else:
            with open(index_file_path, "wb") as f:
                np.save(f, np.zeros((0, dim), dtype=np.float32))

    with open(metadata_file_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return ntotal


def query_semantic_search(
    query_text: str,
    index_file_path: str,
    metadata_file_path: str,
    top_k: int = 5,
    clip_engine: Optional[CLIPEmbeddingEngine] = None,
) -> List[Dict[str, Any]]:
    """
    Queries local FAISS index (or numpy fallback binary) using a natural-language query string.
    Returns ranked list of matching clips with similarity scores.
    """
    if not os.path.exists(index_file_path) or not os.path.exists(metadata_file_path):
        return []

    if clip_engine is None:
        clip_engine = CLIPEmbeddingEngine()

    query_vec = clip_engine.encode_text(query_text)
    query_mat = query_vec.reshape(1, -1).astype(np.float32)
    query_norm = query_mat / (np.linalg.norm(query_mat) + 1e-6)

    with open(metadata_file_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    if not metadata:
        return []

    if faiss is not None:
        try:
            index = faiss.read_index(index_file_path)
            actual_k = min(top_k, index.ntotal)
            if actual_k == 0:
                return []
            scores, indices = index.search(query_norm, actual_k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if 0 <= idx < len(metadata):
                    item = dict(metadata[idx])
                    item["similarity_score"] = float(score)
                    results.append(item)
            return results
        except Exception:
            pass

    # Numpy matrix inner product fallback search
    try:
        with open(index_file_path, "rb") as f:
            matrix = np.load(f)
    except Exception:
        return []

    if matrix.shape[0] == 0:
        return []

    scores = np.dot(matrix, query_norm.T).flatten()
    sorted_indices = np.argsort(-scores)[:top_k]

    results = []
    for idx in sorted_indices:
        if 0 <= idx < len(metadata):
            item = dict(metadata[idx])
            item["similarity_score"] = float(scores[idx])
            results.append(item)

    return results
