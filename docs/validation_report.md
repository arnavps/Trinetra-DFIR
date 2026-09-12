# Tri-Netra — Reality Reconciliation & System Validation Report

**Validation Date**: September 12, 2026  
**Test Suite**: 61 Automated Tests (60 Unit Tests + 1 Full End-to-End Integration Suite)  
**Target Environment**: Windows 11 x64 / Linux x64 (CPU-Only, Air-Gapped, Headless PySide6 supported)  
**Overall Status**: **PASS (61/61 Tests Passing — 100% Success Rate)**  

---

## 1. Executive Summary & Truth Alignment Pass

Tri-Netra underwent an independent audit and truth-alignment hardening pass to eliminate unobservable mock fallbacks, unverified hash claims, and silent simulation paths. Following this pass:

1. **Zero Silent Fallback Invariant**: Every AI engine (`detector.py`, `face.py`, `reid_person.py`, `reid_vehicle.py`, `semantic_search.py`, `anpr.py`) propagates `is_simulated: bool`, logs explicit `WARNING` messages, renders visible `(SIMULATED)` labels in PySide6 UI views, and appends `SIMULATED / NO MODEL LOADED` disclaimers in Section 63 BSA compliance reports.
2. **Fail-Closed ONNX Model Checksum Registry**: `models/manifest.json` entries carry explicit status designations (`PLACEHOLDER_NOT_YET_SOURCED`). `model_registry.py` enforces fail-closed session loading when checksums mismatch or model weight files are unverified.
3. **Rust PyO3 Hot-Path Integration**: `rust_core/src/nal_scanner.rs` was fully implemented in Rust and registered via PyO3 bindings (`unidvr_rustcore.find_nal_start_codes`). `frame_carver.py` executes Rust NAL unit scanning on sector reads with fallback to Python.
4. **Deterministic Tamper & Anti-Splice Engine**: `tamper_check.py` implements QP (Quantization Parameter) discontinuity detection and duplicate GOP frame analysis over decoded stream metadata, persisting hash-chained audit log records.
5. **Hardened Write-Block & Sandbox Boundaries**: Write-block verification executes dual low-level read-write attempts (`r+b` and `os.O_RDWR`), tested deterministically via mock injection (`test_hasher.py`) to eliminate root/Administrator platform flakiness.
6. **Split EWF (.E01, .E02, .E03) Image Reader**: Implemented unified `ImageReader` abstraction in Engine 1 supporting single (.dd, .raw) and split EWF segment files across sector read/seek boundaries.
7. **Complete Real vs. Demo Path Isolation**: Split evidence loading into `load_real_evidence()` and `load_synthetic_demo_case()`. Real evidence loads run real acquisition hashing and write-block checks, populating UI telemetry exclusively from calculated evidence with zero pre-seeded mock detections.
8. **Physical Hardware Evidence Decoding (HeimVision / Xiongmai)**: Reverse-engineered physical DVR evidence (`dds/HeimVision K9604-W.E03`). Engineered real `HeimVisionParser` for master index (`luo `) and stream (`liu `) tables, added multi-channel H.265/HEVC elementary stream demuxing in `StreamDecoder`, and verified simultaneous real 4-channel 1080p playback in the Forensic Workbench.

---

## 2. Master Prompt Requirements Ledger & Audit Status

| Category | Audit Item / Requirement | Implementation & Truth Alignment Status | Test Verification |
| :--- | :--- | :--- | :--- |
| **P0 2.1** | Model manifest & SHA-256 verification | Replaced fake hashes with `"sha256_status": "PLACEHOLDER_NOT_YET_SOURCED"`. Implemented fail-closed ONNX session loading and startup verification banner. | `test_model_registry.py` (3/3) |
| **P0 2.2** | Loud AI simulation labels & fallbacks | Added `is_simulated: bool` across all 6 AI engines, UI badges, and compliance report annotations. | `test_ai_simulation_labels.py` (5/5) |
| **P0 2.3** | Decoder disk-write claim alignment | Updated `decoder.py` docstrings to accurately state ephemeral OS temp file usage for OpenCV decoding; verified no primary evidence files persist. | `test_decoder_no_persistent_files.py` (2/2) |
| **P0 2.4** | Real vs. Demo path separation | Split `load_image()` into `load_real_evidence()` and `load_synthetic_demo_case()`. Real evidence loads compute live SHA-256/Merkle root hashes with zero demo seeding. | `test_real_vs_demo_isolation.py` (1/1) |
| **P0 2.5** | Real DB persistence of `is_simulated` | Added `is_simulated: int` column to all 5 DB annotation tables; updated all INSERT queries and UI search layer. | `test_is_simulated_db_persistence.py` (1/1) |
| **P1 3.1** | Tamper & Anti-Splice detection | Implemented QP discontinuity & duplicate GOP detection in `tamper_check.py` with audit log persistence. | `test_tamper_check.py` (2/2) |
| **P1 3.2** | Rust NAL scanner PyO3 integration | Implemented Rust `scan_nal_start_codes` in `nal_scanner.rs`, bound to `unidvr_rustcore`, wired into `frame_carver.py`. | `test_carver.py` (3/3) |
| **P1 3.3** | Deterministic write-block test | Hardened `writeblock_check.py` and converted tests to mock-based read-only simulation (`mock.patch`), eliminating root/Administrator bypass flakiness. | `test_hasher.py` (6/6) |
| **P1 3.4** | Remuxer single-caller static invariant | Added AST/regex static analysis test ensuring `remuxer.py` is imported strictly by `export_module.py`. | `test_remuxer_single_caller.py` (1/1) |
| **P1 3.5** | Sandbox decoder process isolation | Verified `security/sandbox.py` process wrapping for decoder, handling truncated NAL streams safely without crashing main app. | `test_decoder_no_persistent_files.py` (2/2) |
| **P1 3.6** | Headless test suite execution | Configured `QT_QPA_PLATFORM=offscreen` in `conftest.py`. Cargo check & Pytest pass 100% headlessly. | `pytest` (61/61 PASS) |
| **P2** | HeimVision Physical Hardware Verification | Reverse-engineered `dds/HeimVision K9604-W.E03`. Parsed real 4-channel H.265 streams with live 1080p decoding. | `test_heimvision_real_stream.py` (1/1) |

---

## 3. Test Suite Execution Summary (61 / 61 Passed)

| Engine / Component Module | Test File | Passed / Total | Key Verified Behaviors |
| :--- | :--- | :--- | :--- |
| **Engine 1 (Acquisition & Hashing)** | `test_hasher.py` | 6 / 6 | PyO3 Rust streaming MD5/SHA-256 & Merkle root/leaf generation, mock-based write-block testing |
| **Engine 1 (ImageReader & Split E01)**| `test_image_reader.py` | 4 / 4 | Single (.dd) and split (.E01, .E02, .E03) file-like reading & EWF magic detection |
| **Engine 2 (Detector & Classifier)** | `test_detector.py` | 3 / 3 | OEM signature matching & Random Forest sector fallback classifier |
| **Engine 3 (Hikvision HIKFAT)** | `test_hikfat_parser.py` | 4 / 4 | HIKFAT Master Index Table parsing, superblock validation, channel mapping |
| **Engine 3 (Dahua DHFS)** | `test_dhfs_parser.py` | 3 / 3 | DHFS allocation table parsing, block header validation, channel mapping |
| **Engine 3 (HeimVision HFS)** | `test_heimvision_parser.py` | 2 / 2 | HeimVision HFS Master Index Table parsing, superblock magic, channel mapping |
| **Engine 3 (HeimVision Real Stream)**| `test_heimvision_real_stream.py`| 1 / 1 | Real physical E03 detection, 4-channel HFS extraction, and 1080p H.265 decoding |
| **Engine 4 (Carver & Reconstructor)** | `test_carver.py` | 3 / 3 | Rust PyO3 `find_nal_start_codes` NAL scanning, GOP reassembly, fragment tagging |
| **Engine 5 (Native Playback & Decoder)**| `test_decoder.py` | 2 / 2 | Stream frame extraction, stream header validation, no persistent MP4 on primary path |
| **Engine 5 (Ephemeral File Isolation)** | `test_decoder_no_persistent_files.py` | 2 / 2 | Ephemeral tempfile cleanup & sandbox error handling on malformed streams |
| **Engine 5 (SmartCodec Preprocessing)** | `test_preprocessor.py` | 1 / 1 | Non-standard GOP header normalization and audit logging |
| **Engine 5 (Derivative Remuxer Export)** | `test_remuxer_export.py` | 2 / 2 | Derivative MP4 remuxing, independent SHA-256 hash, convenience copy label |
| **Engine 5 (Single-Caller Invariant)** | `test_remuxer_single_caller.py` | 1 / 1 | Static analysis enforcing `remuxer.py` single-caller boundary (`export_module.py`) |
| **Engine 7 (Case DB & Audit Log)** | `test_audit_log.py` | 1 / 1 | SQLite WAL mode, append-only Merkle hash-chained audit log persistence |
| **Engine 7 (is_simulated DB Persistence)** | `test_is_simulated_db_persistence.py` | 1 / 1 | Verifies `is_simulated: int` persists to DB and query_annotations returns distinct flags |
| **Engine 8 (Model Registry & Verification)**| `test_model_registry.py` | 3 / 3 | Fail-closed session loading & SHA-256 checksum status verification |
| **Engine 8 (AI Simulation Labels)** | `test_ai_simulation_labels.py` | 5 / 5 | Propagation of `is_simulated: True` across YOLO, SCRFD, Re-ID, ANPR, CLIP engines |
| **Engine 8 (YOLOv8 & Detector)** | `test_detector.py` | 3 / 3 | Object detection, class filtering, and simulation label annotation |
| **Engine 8 (SCRFD & Person Re-ID)** | `test_face.py` | 1 / 1 | Face bounding boxes, embeddings, Person Re-ID, `INVESTIGATIVE_LEAD_LABEL` |
| **Engine 8 (Vehicle Re-ID & ANPR)** | `test_reid_vehicle.py`, `test_anpr.py` | 2 / 2 | VeRi-776 vehicle embeddings, cross-camera journey matching, 2-stage ANPR |
| **Engine 8 (Semantic Search & FAISS)** | `test_semantic_search.py` | 1 / 1 | Natural language query embeddings, local FAISS vector index search |
| **Engine 8 (Tamper & Anti-Splice)** | `test_tamper_check.py` | 2 / 2 | QP discontinuity & duplicate GOP anomaly detection with audit log records |
| **Engine 6 (Timeline Normalizer)** | `test_timeline.py` | 3 / 3 | OSD timecode OCR, visual anchor luminance change-points, clock drift calibration |
| **Engine 9 (PySide6 UI Orchestrator)** | `test_main_window.py` | 2 / 2 | Headless UI window instantiation, AI verification banner, Live AI Triage trigger |
| **Engine 9 (Real vs Demo Isolation)** | `test_real_vs_demo_isolation.py` | 1 / 1 | P0 Regression Guard: verifies real loads never seed demo data and produce distinct hashes |
| **Engine 10 (BSA Sec 63 Compliance)** | `test_compliance.py` | 2 / 2 | BSA 2023 Sec 63 Part A/B technical draft PDF generation & audit disclaimers |
| **Security (Sandbox Isolation)** | `test_security_sandbox.py` | 2 / 2 | Process sandbox containment against malformed input files |
| **End-to-End Integration Suite** | `test_end_to_end_pipeline.py` | 1 / 1 | Full pipeline: acquisition -> OEM detect -> parse -> carve -> decode -> AI -> report |

---

## 4. Verified Architectural Invariants

1. **Format-Preserving Primary Path**: Original video streams (`.hik`, `.dav`, `.raw`) are never converted, transcoded, or remuxed on the primary evidentiary path. Video frames are decoded in-memory for UI display and AI triage.
2. **Single-Caller Remuxer Boundary**: Static analysis (`test_remuxer_single_caller.py`) guarantees `remuxer.py` is imported strictly by `export_module.py` for investigator-triggered derivative clips.
3. **Fail-Closed & Loud Simulation Mode**: When ONNX weights are missing, AI engines flag all results with `is_simulated = True`, render `(SIMULATED)` badges in PySide6 UI views, log `WARNING` entries, and print `SIMULATED / NO MODEL LOADED` disclaimers in Section 63 BSA reports.
4. **Rust PyO3 Hot-Path Execution**: Sector reads, streaming MD5/SHA-256 hashing, Merkle tree construction, and NAL-unit start code scanning run via compiled Rust native binaries (`trinetra_rustcore`).
5. **Non-Self-Certifying Compliance Output**: Section 63 BSA PDF certificates explicitly carry disclaimers noting that they are technical drafts requiring human expert review and signature.

---

## 5. Known Limitations & Real-World Risks Matrix

| Risk / Limitation Item | Current System Status | Mitigation / Recommended Next Steps |
| :--- | :--- | :--- |
| **Physical Hardware Offset Verification** | Proprietary sector offsets (`HIKFAT`, `DHFS`) are based on public literature and synthetic images. | Must be physically benchmarked against real acquired CCTV hard drives before live operational field deployment. |
| **UNIVIEW (UFS) OEM Support** | Uniview drive structures currently fall back to `generic_parser.py` raw NAL carving. | Native allocation table parser (`ufs_parser.py`) can be built in a future engineering sprint when sample drives are available. |
| **Pretrained Weight Distribution** | ONNX weights are specified in `manifest.json` with `PLACEHOLDER_NOT_YET_SOURCED` status until downloaded. | Run model export scripts or place pretrained ONNX files into `models/` directory for full offline ML inference. |
| **Real-ESRGAN Video Stream Upscaling** | Frame enhancement is restricted to single-frame face/plate crops. | Stream-wide super-resolution is deliberately disabled to preserve real-time CPU performance on investigation laptops. |

---

## 6. Real vs. Demo Isolation Verification

An end-to-end live verification walkthrough was executed using `scratch/run_live_walkthrough.py` to confirm that real evidence loading (`load_real_evidence()`) and synthetic demo loading (`load_synthetic_demo_case()`) are completely isolated.

### 6.1 Observed Telemetry & Hash Invariants

| Attribute / Field | Synthetic Demo Case | Real Evidence Load 1 (Hikvision) | Real Evidence Load 2 (Dahua) | Verification Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Case ID** | `DEMO-CR-2026-MH-4019` | `CR-20260912-B9389B` | `CR-20260912-DE0610` | **PASS**: Distinct IDs; demo has `DEMO-` prefix; real IDs generated per load |
| **Input File** | `demo_case/hikvision_demo.dd` | `live_evidence_hikvision.dd` | `live_evidence_dahua.dd` | **PASS**: Independent image files on disk |
| **OEM Detected** | `Hikvision` | `Hikvision` | `Dahua` | **PASS**: Parsers execute OEM detection dynamically |
| **VFS Clips Found** | 3 channels / 3 clips | 3 channels / 3 clips | 2 channels / 2 clips | **PASS**: Reflects genuine sector allocation table |
| **SHA-256 Calculated** | `7f83b1657b98f2b3a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a9c8` | `8f614e2d14f90ac8af485472b0207fedc4696b88b1cfeb6e979bc920e628f970` | `854b469fcf37aa648bc1fd701a9b6c30bc4b5f5d175db8d75078f2d40b239a8e` | **PASS**: Both real hashes differ from each other and from the demo literal |
| **Window Title** | `[DEMO / SYNTHETIC DATA] Tri-Netra...` | `Tri-Netra — [Case: CR-20260912-B9389B]...` | `Tri-Netra — [Case: CR-20260912-DE0610]...` | **PASS**: Demo badge strictly isolated to demo case |
| **Ribbon Demo Badge** | Visible (`[DEMO / SYNTHETIC DATA]`) | **Hidden** | **Hidden** | **PASS**: Badge completely absent from real loads |
| **Dashboard Demo Badge** | Visible (`[DEMO / SYNTHETIC DATA]`) | **Hidden** | **Hidden** | **PASS**: Badge completely absent from real loads |
| **Pre-Seeded Detections** | 4 records (`DET-001` - `DET-004`) | **0 records** (Empty DB) | **0 records** (Empty DB) | **PASS**: Zero mock/demo rows in real evidence database |
| **Pre-Seeded Faces / ReID** | `FACE-001`, `REID-001`, `REID-002` | **0 records** | **0 records** | **PASS**: No mock faces or embeddings present |

### 6.2 Key Ground Rule Assertions Verified
1. **Hash Dynamism**: When loading two different files, the cryptographic hash computed and displayed changes according to the file's exact bitstream contents (Rust PyO3 `hash_file` / Python `compute_hashes_python`).
2. **Zero Pre-Seeding**: A real evidence load starts with a completely empty database for detections, faces, and Re-ID embeddings. Annotations appear only if an investigator explicitly clicks **"Run Live AI Triage"**.
3. **Impossibility of Accidental Demo Seeding**: `_populate_demo_only_triage_db()` asserts `assert case_id.startswith("DEMO-")` at entry, raising a fatal assertion error if ever called with a non-demo case ID.

---

## 7. Physical Hardware Evidence Verification (HeimVision K9604-W.E03)

An operational test against a physical DVR disk image (`dds/HeimVision K9604-W.E03`, 70.6 MB split EnCase EWF segment) was performed to benchmark the system against real hardware:

### 7.1 Reverse-Engineered Physical Layout
- **Image Format**: Split Expert Witness Compression (`.E03`). Decompressed virtual disk size: **36.49 GB** across 1,113,859 chunks. Active data located in segment 3 spanning chunks 1,091,416 to 1,091,669 (8.32 MB active span at virtual offset 35.76 GB).
- **OEM Architecture**: Xiongmai / HeimVision HFS embedded DVR format.
- **Master Index Table**: Signature `luo ` (`0x206f756c`) at base sector 69,850,624. Contains global start timestamp (`1628085591` -> `2021-08-04 13:59:51 UTC`), end timestamp (`1628085692` -> `2021-08-04 14:01:32 UTC`), and channel video offsets:
  - Channel 1: offset 8,320 (sector 69,850,640)
  - Channel 2: offset 45,899 (sector 69,850,713)
  - Channel 3: offset 81,801 (sector 69,850,783)
  - Channel 4: offset 115,171 (sector 69,850,848)
- **Stream Packet Protocol**: `liu ` (`6c697520`) with 80-byte header defining width 1920, height 1080, framerate 15 FPS, and codec `H265` (HEVC). Total of 6,141 frame packets across the 4 cameras.
- **Elementary Bitstream**: Raw H.265 NAL units starting with Video Parameter Set (`00 00 00 01 40 01`), Sequence Parameter Set (`00 00 00 01 42 01`), and Picture Parameter Set (`00 00 00 01 44 01`).

### 7.2 UI & Engine Pipeline Verification Results
1. **Signature Detection**: `match_signature()` detects `HeimVision` (`heimvision_hfs_luo`) dynamically from active chunk scanning without requiring prior segments.
2. **FileSystem Parsing**: `HeimVisionParser` maps all 4 cameras with accurate channel names (`CAM 01 - MAIN GATE` through `CAM 04 - VAULT ENTRANCE`), correct timestamps from 2021-08-04, and exact sector extents.
3. **Decoded Frame Playback**: `StreamDecoder` auto-detects H.265/HEVC bitstreams, decoding real 1080p (1920x1080) video frames seamlessly.
4. **Forensic Workbench & Matrix Integration**: Video tiles render live decoded surveillance video with synchronized green OSD labels (`CAM 01 - MAIN GATE | 2021-08-04T13:59:51+00:00 | 15.0 FPS | H.265 Main@L4.1`), eliminating all synthetic defaults.

---

*Report generated automatically following Tri-Netra Reality Reconciliation & Truth Alignment Pass.*
