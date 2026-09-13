"""Unit tests verifying that all AI engines flag is_simulated=True when model weights are unverified/missing."""

import numpy as np
from app.engine8_ai.detector import YOLOv8Detector
from app.engine8_ai.face import SCRFDFaceDetector
from app.engine8_ai.reid_person import PersonReID
from app.engine8_ai.reid_vehicle import VehicleReID
from app.engine8_ai.anpr import ANPRPipeline, PlateDetector, PlateRecognizer


def test_yolo_detector_flags_simulated():
    detector = YOLOv8Detector(model_name="missing_yolo.onnx")
    assert detector.is_simulated is True
    dummy_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    results = detector.detect_frame(dummy_frame)
    assert len(results) > 0
    for res in results:
        assert res.get("is_simulated") is True


def test_scrfd_face_detector_flags_simulated():
    detector = SCRFDFaceDetector(model_name="missing_scrfd.onnx")
    assert detector.is_simulated is True
    dummy_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    faces = detector.detect_faces(dummy_frame)
    assert len(faces) > 0
    for f in faces:
        assert f.get("is_simulated") is True


def test_person_reid_flags_simulated():
    reid = PersonReID(model_name="missing_osnet.onnx")
    assert reid.is_simulated is True
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    emb, is_sim = reid.extract_embedding(dummy_crop)
    assert is_sim is True
    assert len(emb) == 256


def test_vehicle_reid_flags_simulated():
    reid = VehicleReID(model_name="missing_veri.onnx")
    assert reid.is_simulated is True
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    emb, is_sim = reid.extract_embedding(dummy_crop)
    assert is_sim is True
    assert len(emb) == 256


def test_anpr_flags_simulated():
    anpr = ANPRPipeline(
        detector=PlateDetector(model_name="missing_plate.onnx"),
        recognizer=PlateRecognizer(model_name="missing_ocr.onnx")
    )
    dummy_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    plates = anpr.process_frame(dummy_frame)
    assert len(plates) > 0
    for p in plates:
        assert p.get("is_simulated") is True
