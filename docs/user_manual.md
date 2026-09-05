# UniDVR-Forensics — User Manual & Operational Walkthrough

## 1. Introduction

Welcome to **UniDVR-Forensics**, an advanced desktop workstation platform for surveillance DVR/NVR acquisition, unallocated space carving, video decoding, AI analytics, and legal compliance reporting.

---

## 2. Interface Layout & Navigation

The application user interface is organized into five main views accessible via the left-hand Fluent navigation bar:

1. **Case Dashboard**: Overview of case metadata, acquired drive statistics, audit log verification status, and extracted file tree.
2. **Playback Matrix**: 8-tile multi-channel video playback grid. Double-click any tile to maximize it for full resolution and frame rate.
3. **Hex Viewer**: Block-level sector hex inspection tool for reviewing raw drive headers, superblock signatures, and unallocated sector boundaries.
4. **Search Panel**: AI-powered natural-language semantic query box (CLIP ViT-B/32) alongside structured filters (Class, Channel ID, Time Range).
5. **Suspect Journey View**: 2-camera trajectory cross-reference panel matching Person and Vehicle Re-ID feature embeddings across channels.

---

## 3. Step-by-Step Investigator Workflow

### Step 1: Create Case & Acquire Physical Drive / Image
1. Click **File -> New Case**.
2. Enter Case Name, Reference ID, and Investigator Name.
3. Select source physical drive (`PhysicalDrive1`) or existing raw disk image (`.dd` / `.raw`).
4. Click **Start Acquisition**. Progress bar indicates block reading and streaming MD5/SHA256 hash generation.

### Step 2: OEM Signature Detection & Filesystem Parsing
1. Click **Detect OEM Signature**.
2. System automatically scans sector headers for Dahua (`DHFS`) or Hikvision (`HIKFAT`) signatures.
3. Extracted files are populated into the File Tree:
   - Structured filesystem files are labeled **parsed**.
   - Sector-carved fragments are labeled **carved / best-effort**.

### Step 3: Stream Decoding & Native Playback
1. Double-click any clip in the File Tree to load it into the Playback Matrix.
2. Streams are decoded in-memory without saving temporary video files to disk.
3. Use the playback controls (Play, Pause, Step Frame, Maximize Tile) to inspect video feeds.

### Step 4: AI Analytics & Natural Language Search
1. Open the **Search Panel**.
2. Enter natural-language search queries (e.g. `"red car moving fast"` or `"person in blue jacket"`).
3. System searches local FAISS index embeddings and displays matching clip segments with confidence scores.
4. Filter detections by Class (Person, Vehicle, Face, ANPR Plate), Channel ID, or Time Range.

### Step 5: Cross-Camera Suspect Trajectory Matching
1. Open **Suspect Journey View**.
2. Select Source Camera (e.g. Channel 1) and Target Camera (e.g. Channel 2).
3. Click **Run Cross-Camera Match**.
4. System compares Re-ID feature vectors and displays candidate matches tagged with the mandatory notice: `investigative lead, not an identification`.

### Step 6: Non-Evidentiary Derivative Export
1. Right-click any clip in the File Tree and select **Export Derivative Clip (MP4)**.
2. System remuxes the stream into an MP4 container in `<case_dir>/derivatives/`.
3. Independent SHA-256 hash is generated and logged. The exported file receives the label `"convenience copy - not for submission as primary evidence"`.

### Step 7: Compliance Report Generation
1. Click **Tools -> Generate Forensic Report**.
2. System verifies append-only audit chain integrity, maps events to ISO/IEC 27037 phases, and drafts BSA 2023 Section 63 Part A & B technical certificates.
3. Click **Save PDF Report** to produce `<case_dir>/report.pdf`.
