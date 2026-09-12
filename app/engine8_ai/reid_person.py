"""
OSNet person Re-ID via FastReID/torchreid conventions, warm-started from Market-1501.
Extracts feature embeddings for detected persons and annotates them into engine7_case_db.
Any UI or report surface showing a Re-ID result MUST label it as an investigative lead, never an identification.
"""

import json
import logging
import os
import sqlite3
import uuid
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from app.engine8_ai import model_registry
from app.engine7_case_db.models import INVESTIGATIVE_LEAD_LABEL

logger = logging.getLogger(__name__)


class PersonReID:
    def __init__(self, model_name: str = "osnet_x0_25.onnx", custom_path: Optional[str] = None):
        self.model_name = model_name
        self.label = INVESTIGATIVE_LEAD_LABEL
        self.session = None
        self.is_simulated = True
        try:
            self.session = model_registry.load_onnx_session(model_name, custom_path=custom_path)
            self.is_simulated = False
        except Exception as e:
            logger.warning(f"SIMULATION FALLBACK: Model '{model_name}' could not be loaded ({e}). Person Re-ID embeddings will be marked is_simulated=True.")
            self.is_simulated = True

    def extract_embedding(self, crop: np.ndarray) -> Tuple[List[float], bool]:
        """
        Extracts a normalized 256-d feature vector embedding for a person crop image.
        Returns tuple: (embedding_list, is_simulated)
        """
        if self.session is None:
            seed_val = int(np.sum(crop)) % 10000 if crop is not None and crop.size > 0 else 42
            rng = np.random.RandomState(seed_val)
            vec = rng.randn(256).astype(np.float32)
            norm = np.linalg.norm(vec)
            vec = vec / (norm + 1e-6)
            return vec.tolist(), True

        import cv2
        resized = cv2.resize(crop, (128, 256))
        input_data = resized.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        input_data = (input_data - mean) / std
        input_data = np.transpose(input_data, (2, 0, 1))[np.newaxis, ...]

        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: input_data})
        embedding = outputs[0][0]
        norm = np.linalg.norm(embedding)
        embedding = embedding / (norm + 1e-6)
        return embedding.tolist(), False


def run_reid_on_detections(
    db_path: str,
    file_id: str,
    frames: Optional[List[np.ndarray]] = None,
    reid_engine: Optional[PersonReID] = None,
) -> List[str]:
    """
    Runs Person Re-ID on existing person detections for a given file_id.
    Stores embeddings in `person_reid_embeddings` annotation table with label=INVESTIGATIVE_LEAD_LABEL.
    READ-ONLY ADVISORY LANE: Writes ONLY to `person_reid_embeddings`. Returns list of reid_ids.
    """
    if reid_engine is None:
        reid_engine = PersonReID()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    inserted_ids = []

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT detection_id, file_id, frame_index, bbox_json
            FROM detections
            WHERE file_id = ? AND class_name = 'person';
            """,
            (file_id,),
        )
        person_dets = cur.fetchall()

        with conn:
            for det in person_dets:
                det_id = det["detection_id"]
                f_idx = det["frame_index"]

                crop = None
                if frames and 0 <= f_idx < len(frames):
                    frame = frames[f_idx]
                    bbox = json.loads(det["bbox_json"])
                    x1, y1, x2, y2 = bbox
                    h, w = frame.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    if x2 > x1 and y2 > y1:
                        crop = frame[y1:y2, x1:x2]

                emb, _is_sim = reid_engine.extract_embedding(crop)
                reid_id = str(uuid.uuid4())
                emb_json = json.dumps(emb)
                is_sim = 1 if (_is_sim or reid_engine.is_simulated) else 0

                label_text = reid_engine.label
                if reid_engine.is_simulated:
                    label_text += " (SIMULATED)"

                conn.execute(
                    """
                    INSERT INTO person_reid_embeddings (reid_id, detection_id, file_id, embedding_json, label, is_simulated)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        reid_id,
                        det_id,
                        file_id,
                        emb_json,
                        label_text,
                        is_sim,
                    ),
                )
                inserted_ids.append(reid_id)
    finally:
        conn.close()

    return inserted_ids
