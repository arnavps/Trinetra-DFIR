# Tri-Netra Court Evidence Viewer (Portable Standalone Edition)

## Forensic Integrity & Legal Purpose

This standalone evidence player is bundled directly inside the **Court Evidentiary Package** to enable the judiciary, court clerks, and independent defense experts to review evidentiary video recordings in their original, unconverted byte form.

### Hard Evidentiary Guarantees
1. **Zero Re-Encoding / Zero Remuxing**: The player operates exclusively on original bitstream bytes. No MP4 remuxing, codec conversion, or transcodes are performed.
2. **Ephemeral In-Memory Decoding**: Frame buffers are decoded dynamically. No converted or derivative video files are written to the recipient machine.
3. **Live Hash Verification**: When an evidence file is loaded, its cryptographic SHA-256 and MD5 hashes are recomputed directly from the file bytes on disk and displayed in the status bar for immediate cross-referencing against the packaged `manifest.json`.

---

## Quick Launch Instructions

### Windows:
Double-click `launch_viewer.bat` or run:
```cmd
python trinetra_viewer.py
```

### Linux / macOS:
Run:
```bash
bash launch_viewer.sh
```

### Direct File Open:
You can also launch the viewer directly pointing to an evidence file:
```bash
python trinetra_viewer.py ../evidence/CH01_20260924_100000.mp4
```

---

## Keyboard Shortcuts
- **Space**: Toggle Play / Pause
- **Left Arrow**: Step Backward 1 Frame
- **Right Arrow**: Step Forward 1 Frame
- **Speed Selector**: 0.25x (frame-by-frame analysis), 0.5x, 1.0x, 2.0x

---

## Dependencies
If running on a system without the pre-installed Python virtual environment, install the minimal runtime dependencies:
```bash
pip install -r requirements.txt
```
*(Requires Python 3.10+, PySide6, OpenCV headless, and NumPy).*
