"""
Full end-to-end integration test validating the complete UniDVR-Forensics pipeline
across synthetic Dahua, Hikvision, and Unknown OEM disk images (Phases 1-7).
"""

import os
import glob
import sqlite3
import tempfile
import pytest
import numpy as np

from tests.fixtures import generate_synthetic_images as gen_synth
from app.engine1_acquisition import acquirer
from app.engine2_detector import signature_matcher
from app.engine3_parsers.dhfs_parser import DhfsParser
from app.engine3_parsers.hikfat_parser import HikFatParser
from app.engine3_parsers.generic_parser import GenericParser

from app.engine4_carver import frame_carver, gop_reconstructor
from app.engine5_playback import bitstream_preprocessor, decoder
from app.engine6_timeline import normalizer
from app.engine7_case_db import db, audit_log, models
from app.engine8_ai import detector, face, reid_person, reid_vehicle, anpr, semantic_search
from app.engine10_compliance import iso27037_mapper, bsa_sec63, report_builder
from app.engine9_ui import export_module, views


def test_full_end_to_end_forensic_pipeline(tmp_path):
    """
    Executes end-to-end forensic acquisition, detection, parsing, carving, in-memory decoding,
    AI triage, timeline normalization, compliance drafting, and derivative export across synthetic images.
    """
    case_dir = os.path.join(tmp_path, "case_e2e")
    os.makedirs(case_dir, exist_ok=True)

    db_path = os.path.join(case_dir, "case.db")
    db.init_db(db_path)
    case_id = "E2E_CASE_2026_001"

    # Step 1: Initialize Case Record
    audit_log.log_event(
        db_path=db_path,
        case_id=case_id,
        event_type="case_created",
        details={"name": "End to End Master Validation Case", "investigator": "Lead Investigator"},
    )

    # Step 2: Synthetic Image Generation
    dahua_img_path = os.path.join(tmp_path, "synthetic_dahua.dd")
    hik_img_path = os.path.join(tmp_path, "synthetic_hik.dd")
    unknown_img_path = os.path.join(tmp_path, "synthetic_unknown.dd")

    gen_synth.generate_dahua_image(dahua_img_path, size_bytes=5 * 1024 * 1024)
    gen_synth.generate_hikvision_image(hik_img_path, size_bytes=5 * 1024 * 1024)
    gen_synth.generate_unknown_oem_image(unknown_img_path, size_bytes=2 * 1024 * 1024)

    from unittest import mock

    # Step 3: Engine 1 Acquisition & Hashing

    with mock.patch("app.engine1_acquisition.acquirer.verify_read_only", return_value=True):
        acq_res = acquirer.acquire_image(
            source_path=dahua_img_path,
            dest_path=os.path.join(case_dir, "acquired_dahua.dd"),
            case_id=case_id,
            db_path=db_path,
        )
    assert os.path.exists(acq_res.path)
    assert len(acq_res.md5) == 32
    assert len(acq_res.sha256) == 64


    # Step 4: Engine 2 Signature Detection
    sig_dahua = signature_matcher.match_signature(dahua_img_path)
    sig_hik = signature_matcher.match_signature(hik_img_path)
    sig_unk = signature_matcher.match_signature(unknown_img_path)

    assert "dahua" in sig_dahua.oem.lower()
    assert "hikvision" in sig_hik.oem.lower()
    assert sig_unk.oem == "Unknown"



    # Step 5: Engine 3 Parsers (Dahua, Hikvision, Generic)
    dh_parser = DhfsParser()
    vfs_dh = dh_parser.parse(dahua_img_path)
    assert len(vfs_dh.files) > 0
    assert all(f.extraction_type == "parsed" for f in vfs_dh.files)

    hik_parser = HikFatParser()
    vfs_hik = hik_parser.parse(hik_img_path)

    assert len(vfs_hik.files) > 0
    assert all(f.extraction_type == "parsed" for f in vfs_hik.files)

    gen_parser = GenericParser()
    vfs_unk = gen_parser.parse(unknown_img_path)
    assert len(vfs_unk.files) > 0
    assert all(f.extraction_type == "carved_fragment" for f in vfs_unk.files)

    # Record Extracted Files in Engine 7 DB
    for f in vfs_dh.files:
        audit_log.record_extracted_file(
            db_path,
            models.ExtractedFile(
                file_id=f.file_id,
                case_id=case_id,
                channel_id=f.channel_id,
                start_timestamp=f.start_timestamp,
                end_timestamp=f.end_timestamp,
                size_bytes=f.size_bytes,
                file_hash="dummyhash_dh",
                extraction_type=f.extraction_type,
            ),
        )


    # Step 6: Engine 4 Carver (NAL scanning & raw GOP reassembly without repackaging)
    with open(dahua_img_path, "rb") as f:
        raw_bytes = f.read()

    nal_units = frame_carver.carve_nal_units(raw_bytes)
    gop_frags = gop_reconstructor.reassemble_gop_fragments(nal_units)
    assert len(gop_frags) > 0

    # Step 7: Engine 5 Playback & Bitstream Preprocessor
    video_stream_payload = gen_synth.create_tiny_h264_stream(num_frames=5)
    preproc = bitstream_preprocessor.BitstreamPreprocessor()
    norm_bytes, was_norm = preproc.preprocess_stream(video_stream_payload, db_path=db_path, case_id=case_id)

    stream_dec = decoder.StreamDecoder(video_stream_payload, oem="dahua")
    frame_cnt = stream_dec.get_frame_count()
    assert frame_cnt > 0



    decoded_frames = [stream_dec.read_frame(i) for i in range(frame_cnt)]
    timestamps = [f"2026-09-04 12:00:{i:02d}" for i in range(frame_cnt)]

    # Step 8: Engine 8 AI Analytics (Read-Only Advisory Lane)
    target_file_id = vfs_dh.files[0].file_id

    # 8a. YOLOv8 Object Detection
    det_engine = detector.YOLOv8Detector()
    det_ids = detector.run_detection_on_clip(db_path, target_file_id, decoded_frames, timestamps, detector=det_engine)
    assert len(det_ids) > 0

    # 8b. SCRFD Face Detection
    face_engine = face.SCRFDFaceDetector()
    face_ids = face.run_face_detection_on_clip(db_path, target_file_id, decoded_frames, timestamps, detector=face_engine)
    assert len(face_ids) > 0

    # 8c. OSNet Person Re-ID
    reid_p_engine = reid_person.PersonReID()
    reid_p_ids = reid_person.run_reid_on_detections(db_path, target_file_id, frames=decoded_frames, reid_engine=reid_p_engine)
    assert len(reid_p_ids) > 0

    # 8d. VeRi-776 Vehicle Re-ID
    reid_v_engine = reid_vehicle.VehicleReID()
    reid_v_ids = reid_vehicle.run_reid_on_vehicles(db_path, target_file_id, frames=decoded_frames, reid_engine=reid_v_engine)
    assert len(reid_v_ids) > 0

    # 8e. Two-Stage ANPR
    anpr_pipe = anpr.ANPRPipeline()
    plate_ids = anpr.run_anpr_on_clip(db_path, target_file_id, decoded_frames, timestamps, pipeline=anpr_pipe)
    assert len(plate_ids) > 0

    # 8f. CLIP FAISS Semantic Search
    index_bin = os.path.join(case_dir, "faiss_index.bin")
    meta_json = os.path.join(case_dir, "faiss_meta.json")
    clip_recs = [{"file_id": target_file_id, "timestamp": timestamps[0], "channel_id": 1, "frame": decoded_frames[0]}]
    semantic_search.build_faiss_index(clip_recs, index_bin, meta_json)

    search_res = semantic_search.query_semantic_search("vehicle", index_bin, meta_json, top_k=1)
    assert len(search_res) > 0

    # Step 9: Engine 6 Timeline Normalizer
    timeline_norm = normalizer.TimelineNormalizer()
    norm_res = timeline_norm.normalize_channel_clock(timestamps, decoded_frames)
    assert "clock_offset_seconds" in norm_res

    # Step 10: Engine 10 Compliance & Section 63 BSA Draft Certificate
    report_json = report_builder.build_json_report(db_path, case_id)
    assert report_json["audit_chain_valid"] is True

    sec63_draft = bsa_sec63.generate_bsa_sec63_cert_draft({"case_id": case_id}, report_json["extracted_files"], report_json["audit_log"])
    assert "not self-certifying" in sec63_draft["disclaimer"]

    pdf_out = os.path.join(case_dir, "report.pdf")
    report_builder.generate_case_report_pdf(db_path, case_id, pdf_out)
    assert os.path.exists(pdf_out)

    # Step 11: Investigator-Triggered Derivative Export
    raw_sample_path = os.path.join(tmp_path, "sample_clip.raw")
    with open(raw_sample_path, "wb") as f:
        f.write(b"RAW_VIDEO_BYTES_FOR_DERIVATIVE_EXPORT_TEST")

    derivatives_dir = os.path.join(case_dir, "derivatives")
    export_mp4_path = os.path.join(derivatives_dir, "clip_export.mp4")

    exp_res = export_module.export_derivative_clip(db_path, case_id, raw_sample_path, export_mp4_path)
    assert os.path.exists(export_mp4_path)
    assert exp_res["label"] == export_module.CONVENIENCE_COPY_LABEL

    # HARD ARCHITECTURE INVARIANT ASSERTION:
    # Assert no MP4/MKV file exists anywhere on the primary evidentiary path/tree.
    # Container exports exist strictly inside the separate derivatives/ directory!
    all_mp4_files = glob.glob(os.path.join(case_dir, "**", "*.mp4"), recursive=True)
    all_mkv_files = glob.glob(os.path.join(case_dir, "**", "*.mkv"), recursive=True)
    container_files = all_mp4_files + all_mkv_files

    for c_file in container_files:
        norm_c_file = os.path.normpath(c_file)
        norm_deriv_dir = os.path.normpath(derivatives_dir)
        assert norm_c_file.startswith(norm_deriv_dir), (
            f"EVIDENTIARY PATH VIOLATION: MP4/MKV container file '{c_file}' found outside derivative export directory!"
        )
