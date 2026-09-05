# UniDVR-Forensics — Live Demonstration Rehearsal Script

**Target Time Limit**: 10–12 Minutes  
**Demonstration Mode**: Synthetic Demo Harness (`dahua_demo.dd`, `hikvision_demo.dd`, `unknown_demo.dd`)  
**Environment**: Standalone Offline Workstation  

---

## Demo Timeline & Step-by-Step Guide

### Minute 0:00 – 1:30 | Introduction & Air-Gap Verification
- **Action**: Launch UniDVR-Forensics executable. Show system status bar confirming **Offline Air-Gapped Mode** (Network Watchdog Active).
- **Talking Point**: *"UniDVR-Forensics is built for offline forensic workstations investigating surveillance DVRs. It enforces 100% air-gapped operation and strict evidentiary integrity under BSA 2023 Section 63."*

### Minute 1:30 – 3:30 | Physical Image Acquisition & Hash Chain Log
- **Action**: Click **New Acquisition**. Select `dahua_demo.dd` (10MB synthetic disk image). Click **Start Acquisition**.
- **Talking Point**: *"Engine 1 performs raw block-level acquisition using our memory-safe Rust PyO3 core. It computes streaming MD5 and SHA-256 hashes concurrently and writes an immutable Merkle audit log entry."*
- **Visual**: Show acquired image created, MD5/SHA256 hashes generated, and audit chain marked `VALID (UNBROKEN)`.

### Minute 3:30 – 5:30 | OEM Signature Matcher & Filesystem Parsing
- **Action**: Click **Detect OEM Signature**. System identifies `Dahua / CP Plus DHFS` at sector 0 and invokes `DhfsParser`.
- **Talking Point**: *"Engine 2 matches sector signatures against our database. Engine 3 parses Dahua DHFS Master Index Tables and populates the File Tree with extracted video clips tagged 'parsed'."*
- **Action**: Next, load `unknown_demo.dd` (Undetected OEM). Show system routing to `GenericParser` (Frame Carver fallback).
- **Talking Point**: *"When an unknown OEM is encountered, Engine 3 delegates to our NAL Frame Carver. Carved fragments are explicitly tagged 'carved_fragment' and rendered as 'carved / best-effort', maintaining full transparency."*

### Minute 5:30 – 7:30 | Native In-Memory Decoding & 8-Tile Matrix Playback
- **Action**: Double-click clips to load them into the 8-Tile Playback Matrix. Click **Play All Channels**.
- **Talking Point**: *"Engine 5 decodes proprietary streams in-memory only. Notice the primary evidentiary video file is NEVER transcoded or converted. Inactive matrix tiles run at 5 FPS proxy resolution; double-clicking a tile maximizes it to native resolution at 25 FPS."*

### Minute 7:30 – 9:30 | AI Triage, Natural-Language Search & Suspect Journey
- **Action**: Open the **Search Panel**. Enter query: `"red car moving fast"`. Click **Semantic Search**.
- **Talking Point**: *"Engine 8 runs offline CLIP ViT-B/32 embeddings indexed in a local FAISS file. Detections run in a strictly read-only advisory lane and write ONLY to annotation tables, never modifying evidence hashes."*
- **Action**: Switch to **Suspect Journey View**. Run cross-camera matching between Channel 1 and Channel 2. Point out the notice: `investigative lead, not an identification`.
- **Talking Point**: *"Our cross-camera Re-ID engine highlights matching candidate trajectories across channels, prominently displaying the mandatory investigative-lead label."*

### Minute 9:30 – 11:00 | Derivative Clip Export & BSA Section 63 Report
- **Action**: Export a clip to MP4 via **Export Derivative Clip**.
- **Talking Point**: *"Derivative exports are triggered only on explicit investigator action. `remuxer.py` is invoked, producing an independent hash and tagging the output as 'convenience copy - not for submission as primary evidence'."*
- **Action**: Click **Generate Forensic Report**. Show PDF report with ISO 27037 phase mapping and Section 63 BSA draft certificate text with non-self-certifying disclaimers.

### Minute 11:00 – 12:00 | Conclusion & Q&A
- **Summary**: *"UniDVR-Forensics combines raw block recovery, proprietary parsing, native in-memory playback, AI triage, and Section 63 BSA compliance into a secure, air-gapped platform."*
