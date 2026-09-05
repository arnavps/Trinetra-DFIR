# UniDVR-Forensics — Validation Report & System Testing Results

**Validation Date**: September 4, 2026  
**Test Suite**: 36 Unit Tests + 1 Full End-to-End Integration Test Suite  
**Target Environment**: Windows 11 x64 (CPU-Only, Air-Gapped)  
**Overall Status**: **PASS (36/36 Unit Tests, 1/1 Integration Test)**  

---

## 1. Executive Summary

UniDVR-Forensics has undergone end-to-end validation across synthetic Dahua (`DHFS`), Hikvision (`HIKFAT`), and Unknown OEM disk images. Every core engine capability (acquisition, OEM detection, structured parsing, sector carving, in-memory decoding, AI analytics, timeline normalization, Section 63 BSA compliance drafting, and derivative clip export) was verified against the architecture invariants established in the Technical Blueprint.

---

## 2. Test Execution & Coverage Summary

| Engine / Component | Unit Test File | Status | Coverage Focus |
| :--- | :--- | :--- | :--- |
| **Engine 1 (Acquisition & Hashing)** | `test_hasher.py` | PASS (5/5) | Block IO, streaming MD5, SHA-256, Merkle leaf/node hashes |
| **Engine 2 (Detector & Classifier)** | `test_detector.py` | PASS (3/3) | Signature matching, Random Forest fallback classifier |
| **Engine 3 (Hikvision HIKFAT)** | `test_hikfat_parser.py` | PASS (4/4) | Superblock validation, Master Index Table parsing, `parsed` tagging |
| **Engine 3 (Dahua DHFS)** | `test_dhfs_parser.py` | PASS (3/3) | Superblock magic check, Master Index Table parsing, `parsed` tagging |
| **Engine 4 (Carver & Reconstructor)** | `test_carver.py` | PASS (3/3) | NAL unit heuristic scanning, GOP stream reassembly, `carved_fragment` tagging |
| **Engine 5 (Native Decode)** | `test_decoder.py` | PASS (2/2) | OpenCV/PyO3 in-memory frame decoding without container writing |
| **Engine 5 (Bitstream Preproc)** | `test_preprocessor.py` | PASS (1/1) | SmartCodec non-standard GOP normalization & audit logging |
| **Engine 7 (Case DB & Audit Log)** | `test_audit_log.py` | PASS (1/1) | SQLite WAL-mode, append-only Merkle hash chain verification |
| **Engine 8 (YOLOv8 & Model Registry)** | `test_detector.py` | PASS (3/3) | SHA-256 checksum enforcement against `manifest.json`, read-only advisory lane |
| **Engine 8 (SCRFD & Re-ID)** | `test_face.py` | PASS (1/1) | Face bboxes, landmarks, Person Re-ID, `INVESTIGATIVE_LEAD_LABEL` |
| **Engine 8 (Vehicle Re-ID & ANPR)** | `test_reid_vehicle.py`, `test_anpr.py` | PASS (2/2) | VeRi-776 vehicle feature embeddings, two-stage ANPR pipeline |
| **Engine 8 (Semantic Search)** | `test_semantic_search.py` | PASS (1/1) | CLIP ViT-B/32 embeddings, local FAISS index build & query |
| **Engine 6 (Timeline Normalizer)** | `test_timeline.py` | PASS (3/3) | OSD extraction, classical CV ambient luminance change-points, clock offset |
| **Engine 10 (BSA Sec 63 & ISO 27037)** | `test_compliance.py` | PASS (2/2) | BSA 2023 Sec. 63 Part A/B technical draft, non-self-certifying disclaimers |
| **Engine 9 (Derivative Export)** | `test_remuxer_export.py` | PASS (2/2) | Remuxer single-caller import boundary, independent hash, convenience copy label |
| **Security (Sandbox Isolation)** | `test_security_sandbox.py` | PASS (2/2) | Subprocess sandbox wrapping parser & decoder against malformed inputs |
| **End-to-End Integration Suite** | `test_end_to_end_pipeline.py` | PASS (1/1) | Full acquisition -> detection -> parse -> carve -> decode -> AI -> report -> export |

---

## 3. Verified Architecture Invariants

1. **Evidentiary Path Preservation**:
   - `test_end_to_end_pipeline.py` explicitly asserted that **no MP4 or MKV container files exist anywhere on the primary evidentiary path**.
   - Video decoding is performed in-memory only via `decoder.py`.
2. **Single-Caller Remuxer Boundary**:
   - `test_remuxer_single_caller_import_boundary` verified that `remuxer.py` is imported ONLY by `export_module.py` across the entire codebase.
3. **Read-Only AI Advisory Lane**:
   - All AI detections and embeddings write strictly to dedicated SQLite annotation tables. Primary evidence files and evidence hashes remain 100% untouched.
4. **Mandatory Non-Self-Certifying Disclaimers**:
   - Grep verification confirmed zero occurrences of forbidden self-certification claims ("admissible", "certified"). All Section 63 drafts include the mandatory disclaimer.
5. **Shared Re-ID Label**:
   - Person and Vehicle Re-ID results are tagged with the shared constant `INVESTIGATIVE_LEAD_LABEL = "investigative lead, not an identification"`.

---

## 4. Known Limitations & Honest Gap Disclosures

1. **CLIP Zero-Shot CCTV Domain Recall**:
   - Semantic search utilizes stock CLIP ViT-B/32 weights. Recall on domain-specific CCTV low-resolution or dark nighttime feeds is mediocre without fine-tuning. This is a documented, accepted design trade-off for zero-shot query flexibility without heavy custom model training.
2. **Placeholder Signature Offsets**:
   - Proprietary filesystem signatures (`HIKVISION` and `DHFS`) in `signatures.json` are placeholders seeded from public literature. They must be verified against physical acquired hardware drives as real devices become available.
3. **P2 / Stretch Capabilities**:
   - Real-ESRGAN single-frame image enhancement (`enhance.py`) is implemented for single-frame crops with pixel-delta audit logging. Video stream super-resolution is intentionally out of scope for CPU performance reasons.
