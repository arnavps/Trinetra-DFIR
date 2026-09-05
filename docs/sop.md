# UniDVR-Forensics — Standard Operating Procedures (SOP)

## Document ID: SOP-DFIR-DVR-001
**Target System**: Multi-Vendor DVR/NVR Surveillance Disk Acquisition & Forensic Analysis  
**Compliance Standard**: Bharatiya Sakshya Adhiniyam (BSA 2023 Section 63) & ISO/IEC 27037  

---

## 1. Pre-Acquisition Requirements & Hardware Setup

1. **Hardware Write-Blocker Mandatory Requirement (§5.1)**:
   - Physical DVR/NVR hard disk drives (SATA/SAS/IDE) **MUST** be connected to the forensic workstation via a certified hardware write-blocker (e.g. Tableau/CRU).
   - In environments where hardware write-blocking is unavailable, software write-blocking must be explicitly verified using `ReadOnlyHandle` checks before opening physical device handles.
   - **NEVER** boot the DVR hardware with the evidence drive connected if the system is suspected of overwriting circular sector logs.

2. **RTSP Live-Stream vs Raw Disk Evidence Boundary (§9.3)**:
   - **RTSP Network Live Streams**: Network camera feeds captured over RTSP represent live transmission data, NOT raw disk evidence. RTSP streams are prone to packet loss, variable bitrates, and transport jitter. They **MUST NOT** be substituted for physical disk evidence.
   - **Raw Physical Disk Evidence**: The primary evidentiary source is the bit-stream image (`.dd` / `.raw`) acquired directly from the physical storage medium. All legal reports and Section 63 BSA certificates must reference the physical disk image hash.

3. **Air-Gap Verification**:
   - The forensic workstation must be physically disconnected from all networks (Ethernet, Wi-Fi, Bluetooth).
   - Verify air-gap status before launching UniDVR-Forensics via `network_watchdog.assert_offline_environment()`.

---

## 2. Forensic Acquisition Procedure

1. Launch UniDVR-Forensics and select **New Case Acquisition**.
2. Input Case Reference ID, Investigator Name, and Target Case Folder.
3. Select Source Storage Device (`\\.\PhysicalDriveX` or image file path).
4. Click **Start Block-Level Acquisition**:
   - Engine 1 will stream raw sectors in 4–16MB chunks.
   - Streaming MD5 and SHA-256 hashes are computed simultaneously via `unidvr_rustcore`.
   - The acquired raw image is saved as `<case_dir>/acquired_image.dd`.
   - Initial acquisition event is permanently written to `audit_log` with Merkle hash-chaining.

---

## 3. OEM Detection & Filesystem Parsing

1. Navigate to **Analysis Dashboard**.
2. Click **Detect OEM Signature**:
   - Signature matcher scans sector offsets for known signatures (`HIKVISION` for Hikvision HIKFAT, `DHFS` for Dahua/CP Plus).
   - If an OEM signature matches, the system routes the image to the dedicated parser (`HikfatParser` or `DhfsParser`). Extracted files are tagged `extraction_type='parsed'`.
   - If no signature matches, the system routes the image to `GenericParser` (Frame Carver fallback). Extracted files are tagged `extraction_type='carved_fragment'` and rendered as "carved / best-effort".

---

## 4. Native In-Memory Playback & AI Triage

1. Select clips from the File Tree to view native video stream playback.
2. Video frames are decoded **in-memory only** via OpenCV/PyO3 (`decoder.py`). Primary evidentiary video files are **NEVER converted or remuxed**.
3. Run AI Analytics (YOLOv8n object detection, SCRFD face detection, Person/Vehicle Re-ID, ANPR, CLIP semantic search):
   - AI outputs write strictly to read-only annotation tables in `engine7_case_db`.
   - Person and Vehicle Re-ID outputs MUST be interpreted as **investigative leads, not definitive identifications**.

---

## 5. Non-Evidentiary Clip Derivative Export

1. If court presentation or investigator convenience requires an MP4 file, click **Export Derivative Clip**.
2. System executes `export_module.py` via `remuxer.py` (`ffmpeg -c:v copy`).
3. Output file is stored in `<case_dir>/derivatives/export_<id>.mp4`.
4. Independent SHA-256 hash is computed for the export file, a `derivative_export` audit log entry is written, and the label `"convenience copy - not for submission as primary evidence"` is applied to UI and reports.

---

## 6. Report Generation & Compliance Drafting

1. Select **Generate Forensic Report**.
2. System compiles JSON metadata, audit log verification chain, ISO/IEC 27037 phase mapping, and Section 63 BSA draft certificates (Part A & B).
3. Review draft text in `bsa_sec63.py` output. Note mandatory legal disclaimer: *"Expert-ready technical draft — requires human investigator signature; not self-certifying"*.
4. Export finalized PDF report to `<case_dir>/report.pdf`.
