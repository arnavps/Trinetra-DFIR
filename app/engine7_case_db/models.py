"""Case + AuditEntry tables in Phase 1; ExtractedFile (+ extraction_type field) added in Phase 4."""

import json
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Case:
    case_id: str
    name: str
    investigator: Optional[str]
    created_at: str


@dataclass
class AuditEntry:
    entry_id: Optional[int]
    case_id: str
    timestamp: str
    event_type: str
    details: Dict[str, Any]
    previous_hash: str
    entry_hash: str

    def details_json(self) -> str:
        return json.dumps(self.details, sort_keys=True)


@dataclass
class ExtractedFile:
    file_id: str
    case_id: str
    channel_id: int
    start_timestamp: str
    end_timestamp: str
    size_bytes: int
    file_hash: str
    extraction_type: str  # 'parsed' | 'carved_fragment'
    storage_path: Optional[str] = None


INVESTIGATIVE_LEAD_LABEL: str = "investigative lead, not an identification"


@dataclass
class Detection:
    detection_id: str
    file_id: str
    timestamp: str
    frame_index: int
    class_name: str
    confidence: float
    bbox_json: str  # "[x1, y1, x2, y2]"


@dataclass
class FaceDetection:
    face_id: str
    file_id: str
    timestamp: str
    frame_index: int
    confidence: float
    bbox_json: str  # "[x1, y1, x2, y2]"
    landmarks_json: Optional[str] = None


@dataclass
class PersonReIDEmbedding:
    reid_id: str
    detection_id: str
    file_id: str
    embedding_json: str
    label: str = INVESTIGATIVE_LEAD_LABEL


@dataclass
class PlateDetection:
    plate_id: str
    file_id: str
    timestamp: str
    frame_index: int
    plate_text: str
    confidence: float
    bbox_json: str  # "[x1, y1, x2, y2]"


@dataclass
class VehicleReIDEmbedding:
    reid_id: str
    detection_id: str
    file_id: str
    embedding_json: str
    label: str = INVESTIGATIVE_LEAD_LABEL


