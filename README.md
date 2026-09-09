# Tri-Netra 
### Multi-Vendor DVR/NVR Forensic Analysis Platform for Standardized Acquisition, Recovery, and Analysis of Surveillance Evidence

**Problem Statement:** SIH26150  
**Sponsoring Organisation:** National Technical Research Organisation (NTRO)  
**Theme:** Blockchain & Cybersecurity — Digital Forensics & Data Sanitization  

---

## 📌 Executive Summary & Architectural Shift 

Modern CCTV digital forensics faces a major legal and technical challenge: converting proprietary DVR/NVR video streams into standard containers like MP4 or MKV for viewing — even losslessly (`-c:v copy`) — alters file hashes. Courts regularly reject converted video files as primary evidentiary artifacts.

**Tri-Netra** addresses this through an architectural, format-preserving design:
1. **Zero Primary Conversion**: Footage is parsed, carved, and decoded **in-memory only** directly from original proprietary bitstreams (`.dav`, `.hik`, `.raw`). No converted files are ever written to disk on the primary evidentiary path.
2. **Strict Derivative Isolation**: Derivative MP4/MKV exports exist strictly via an investigator-triggered export module (`export_module.py`). Derivative files receive independent SHA-256 hashes, distinct audit entries, and the mandatory label: `"convenience copy - not for submission as primary evidence"`.
3. **Read-Only AI Advisory Lane**: All AI-assisted triage outputs (YOLOv8n detection, SCRFD face crops, FastReID suspect tracking, ANPR, OpenCLIP semantic search) are tagged with `INVESTIGATIVE_LEAD_LABEL` ("investigative lead, not an identification") and write strictly to annotation tables.
4. **Legal Defensibility & BSA 2023 Compliance**: Auto-drafts Section 63 Bharatiya Sakshya Adhiniyam (BSA 2023) Part A/B technical certificates containing full sector offsets, pre/post read hashes, and audit chain verification — explicitly framed as human-signed, non-self-certifying technical drafts.

---

## 🏛️ 10-Engine System Architecture

UniDVR-Forensics is organized into 10 decoupled engine modules under `app/`:

```
                           ┌─────────────────────────────────────────────────────────┐
                           │          EVIDENCE SOURCE (Write-Blocked HDD / .dd)     │
                           └────────────────────────────┬────────────────────────────┘
                                                        │
                                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ EVIDENTIARY PIPELINE (Sequential & Deterministic)                                                            │
│                                                                                                               │
│ ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐  │
│ │ Engine 1:            │───►│ Engine 2:            │───►│ Engine 3:            │───►│ Engine 4:            │  │
│ │ Acquisition & Hash   │    │ OEM Detector         │    │ Filesystem Parsers   │    │ Fragment Carver      │  │
│ └──────────────────────┘    └──────────────────────┘    └──────────────────────┘    └──────────────────────┘  │
│            │                           │                           │                           │              │
│            ▼                           ▼                           ▼                           ▼              │
│ ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ Engine 7: Case DB & Hash-Chained Merkle Audit Log (SQLite WAL)                                           │ │
│ └──────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                        │                                                      │
│                                                        ▼                                                      │
│                             ┌─────────────────────────────────────────────────────┐                          │
│                             │ Engine 5: Native Playback & In-Memory Decode        │                          │
│                             └──────────────────────────┬──────────────────────────┘                          │
└────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┘
                                                         │ (Decoded Ephemeral Frames)
                                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ READ-ONLY ADVISORY & USER INTERFACE LANES                                                                    │
│                                                                                                               │
│ ┌──────────────────────────────────┐   ┌──────────────────────────────────┐   ┌────────────────────────────┐ │
│ │ Engine 6: Timeline Normalizer    │   │ Engine 8: AI Analytics Lane      │   │ Engine 10: Compliance      │ │
│ │ (OSD + Visual Anchor Calibration)│   │ (YOLOv8, Re-ID, ANPR, CLIP FAISS)│   │ (BSA Sec. 63 / ISO 27037)  │ │
│ └──────────────────────────────────┘   └──────────────────────────────────┘   └────────────────────────────┘ │
│                  │                                      │                                    │               │
│                  └──────────────────────────────────────┴────────────────────────────────────┘               │
│                                                         │                                                     │
│                                                         ▼                                                     │
│ ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ Engine 9: PySide6 UI & Case Orchestrator (5 Stacked Views + Toolbar)                                     │ │
│ └──────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Engine Summary
- **Engine 1 — Acquisition & Hashing**: Block-level read-only imaging with streaming MD5/SHA-256 hashing and Merkle tree generation using PyO3 Rust extensions (`rust_core`).
- **Engine 2 — OEM & Filesystem Detector**: Magic-byte signature detector for Hikvision (`HIKVISION`) & Dahua (`DHFS`), with a Random Forest sector classifier fallback.
- **Engine 3 — Filesystem Parser Plugins**: Dedicated allocation table parsers for Hikvision (`hikfat_parser.py`) and Dahua/CP Plus (`dhfs_parser.py`) producing in-memory virtual file trees.
- **Engine 4 — Fragmented Frame Carver**: Sector NAL-unit scanner (`frame_carver.py`) and GOP reconstructor (`gop_reconstructor.py`) for deleted/corrupted space.
- **Engine 5 — Native Playback & In-Memory Decode Engine**: In-memory ephemeral stream pre-processing and frame decoding (`decoder.py`) without file conversion; single-caller isolated MP4 exporter (`export_module.py`).
- **Engine 6 — Timeline Normalizer**: OSD timecode extraction and visual anchor luminance change-point drift calibration (`normalizer.py`).
- **Engine 7 — Case DB & Chain-of-Custody Log**: SQLite WAL database with hash-chained append-only Merkle audit log (`audit_log.py`).
- **Engine 8 — AI Analytics Lane**: Offline ONNX model execution for object detection, SCRFD face detection, FastReID person/vehicle Re-ID, two-stage ANPR, OpenCLIP + FAISS semantic search, and Real-ESRGAN enhancement.
- **Engine 9 — UI & Case Orchestrator**: Native PySide6 Dark Slate Fluent interface with 5 core views + top action toolbar (`main_window.py`).
- **Engine 10 — Compliance & Report Engine**: ISO/IEC 27037 audit mapping and BSA 2023 Section 63 Part A/B certificate PDF auto-drafter.

---

## 🔒 Architectural Constraints & Invariants

1. **100% Offline Air-Gapped Operation**: Zero runtime network calls, zero telemetry, zero phone-home licensing checks. ONNX weight files are verified against `models/manifest.json` SHA-256 checksums before loading.
2. **CPU-Only Optimization**: INT8 quantized ONNX models and C-accelerated vector search (`bytes.find()`) optimized for standard investigation laptops.
3. **Format-Preserving Primary Path**: Original video streams are decoded in-memory only. Primary evidentiary files are never transcoded or remuxed.
4. **Non-Self-Certifying Compliance**: All Section 63 BSA certificate drafts explicitly bear the disclaimer: *"Expert-ready technical draft — requires human investigator signature; not self-certifying"*.

---

## 🚀 Quick Start & Installation

### Prerequisites
- **OS**: Windows 10/11, Linux, or macOS
- **Python**: Python 3.11 or 3.13
- **Rust**: Cargo/Rust toolchain (for building `rust_core` PyO3 extension)

### 1. Clone & Setup Environment
```bash
git clone https://github.com/your-org/Tri-Netra.git
cd Tri-Netra

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Build Rust Core Extension
```bash
# Build Rust block IO extension
maturin develop --manifest-path rust_core/Cargo.toml
```

### 3. Launch Desktop Application
```bash
python main.py
```

---

## 🖥️ Using the Application

1. **Load Synthetic Test Case**: Click **`Load Synthetic Test Case`** on the top toolbar. This instantly mounts a pre-built Hikvision DVR demo drive (`demo_case/hikvision_demo.dd`) complete with camera channels, index tables, and playable H.264 video streams.
2. **Open Evidence Image**: Click **`Open Evidence Image`** to load any `.dd`, `.raw`, or `.E01` drive image.
3. **Navigate Core Views**:
   - **Case Dashboard**: Browse VirtualFileSystem camera channels and file trees. Double-clicking any file seeks and plays the clip in the Native Player.
   - **Native Playback**: 8-tile synchronized multi-channel playback matrix.
   - **Disk Hex View**: Inspect raw sector bytes and ASCII representations at any byte offset.
   - **AI Semantic Search**: Search by class, camera channel, time range, or natural language (e.g., *"person with blue backpack"*).
   - **Suspect Journey Re-ID**: Cross-reference candidate suspect matches across camera channels.
4. **Generate Court Certificate**: Click **`Generate BSA Sec. 63 Certificate`** to produce the court-ready PDF report saved in `demo_case/BSA_Sec63_CASE-SYNTHETIC-HIKVISION.pdf`.
5. **Export Convenience Copy**: Click **`Export Derivative Clip`** to generate an isolated, separately-hashed MP4 convenience copy.

---

## 🧪 Test Suite & Verification

Run the full automated test suite (unit + end-to-end integration tests):

```bash
# Run Python test suite (38 tests)
pytest

# Run Rust core tests
cargo test --manifest-path rust_core/Cargo.toml
```

All 38 test suites pass with 100% success across acquisition, parsing, carving, in-memory decoding, AI triage, timeline normalizer, compliance report generation, and derivative export boundaries.

---

## 📁 Repository Structure

```
Tri-Netra/
├── main.py                         # Desktop application entrypoint
├── CLAUDE.md                       # Architectural invariants & coding guidelines
├── pyproject.toml                  # Package configuration & build settings
├── requirements.txt                # Python dependencies
│
├── app/                            # Decoupled Engine Architecture
│   ├── engine1_acquisition/        # Write-block check & raw imaging
│   ├── engine2_detector/           # Sector magic-byte detector & RF classifier
│   ├── engine3_parsers/            # Hikvision HIKFAT & Dahua DHFS parsers
│   ├── engine4_carver/             # Sector NAL-unit carver & GOP reconstructor
│   ├── engine5_playback/           # Ephemeral decoder & derivative exporter
│   ├── engine6_timeline/           # OSD extractor & visual anchor normalizer
│   ├── engine7_case_db/            # SQLite WAL DB & hash-chained audit log
│   ├── engine8_ai/                 # ONNX model registry, YOLOv8, SCRFD, Re-ID, CLIP
│   ├── engine9_ui/                 # PySide6 desktop UI, toolbar, and 5 stacked views
│   ├── engine10_compliance/        # ISO 27037 mapper & BSA Sec. 63 PDF generator
│   └── security/                   # Process sandbox & network watchdog
│
├── rust_core/                      # PyO3 Rust Crate for Raw Sector IO & Hashing
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── raw_io.rs               # Streaming sector MD5/SHA256 & Merkle tree
│       └── nal_scanner.rs          # Rust NAL-unit sector scanner
│
├── models/                         # Local AI ONNX Weight Registry
│   └── manifest.json               # SHA-256 checksum manifest of model weights
│
├── docs/                           # Technical Specifications & Documentation
│   ├── architecture.md             # System architecture specification
│   ├── sop.md                      # Standard operating procedures
│   ├── user_manual.md              # User operational manual
│   ├── validation_report.md        # Test suite validation report
│   └── demo_script.md              # Timed live demo walkthrough
│
└── tests/                          # Comprehensive Unit & Integration Tests
    ├── integration/
    │   └── test_end_to_end_pipeline.py
    └── unit/                       # 37 unit tests covering all engine modules
```

---

## 📜 Compliance & Legal References

- **Bharatiya Sakshya Adhiniyam (BSA 2023), Section 63**: Admissibility of electronic records in Indian courts; Part A/B certificate specifications.
- **ISO/IEC 27037:2012**: Information technology — Security techniques — Guidelines for identification, collection, acquisition and preservation of digital evidence.

---

## 📄 License

Developed for **SIH26150** sponsored by the **National Technical Research Organisation (NTRO)**. All rights reserved.
