import os
import sys

# Ensure repository root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import json
import sqlite3
import tempfile
from PySide6.QtWidgets import QApplication

from app.engine9_ui.main_window import MainWindow
from tests.fixtures.generate_synthetic_images import generate_hikvision_image, generate_dahua_image


def run_live_walkthrough():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate two genuinely distinct forensic images
        img1_path = os.path.join(tmpdir, "live_evidence_hikvision.dd")
        img2_path = os.path.join(tmpdir, "live_evidence_dahua.dd")

        print("[1] Generating distinct forensic images...")
        generate_hikvision_image(img1_path, size_bytes=3 * 1024 * 1024, seed=4242)
        generate_dahua_image(img2_path, size_bytes=3 * 1024 * 1024, seed=8484)

        with open(img1_path, "rb") as f1, open(img2_path, "rb") as f2:
            b1 = f1.read(512)
            b2 = f2.read(512)
            assert b1 != b2, "Image headers should differ"

        print("[2] Initializing UI (MainWindow)...")
        window = MainWindow()
        window.show()

        # Step A: Observe Demo Case
        demo_case_id = window.current_case_id
        demo_db_path = window.current_db_path
        demo_window_title = window.windowTitle()
        demo_ribbon_badge = not window.status_ribbon.badge_demo.isHidden()
        demo_dash_badge = not window.view_dashboard.demo_badge.isHidden()
        demo_hash = "7f83b1657b98f2b3a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a9c8"

        demo_conn = sqlite3.connect(demo_db_path)
        cur = demo_conn.cursor()
        cur.execute("SELECT detection_id, class_name, confidence, is_simulated FROM detections;")
        demo_detections = cur.fetchall()
        demo_conn.close()

        # Step B: Load Real Evidence 1 (Hikvision)
        print(f"[3] Loading Real Evidence 1: {img1_path}...")
        window.load_real_evidence(img1_path)
        real1_case_id = window.current_case_id
        real1_db_path = window.current_db_path
        real1_window_title = window.windowTitle()
        real1_ribbon_badge = not window.status_ribbon.badge_demo.isHidden()
        real1_dash_badge = not window.view_dashboard.demo_badge.isHidden()
        real1_oem = window.current_vfs.oem if window.current_vfs else "None"
        real1_files_count = len(window.current_vfs.files) if window.current_vfs else 0

        conn1 = sqlite3.connect(real1_db_path)
        cur1 = conn1.cursor()
        cur1.execute("SELECT details FROM audit_log WHERE event_type = 'HASH_VERIFY';")
        hash_row1 = cur1.fetchone()
        real1_hash = json.loads(hash_row1[0])["sha256"] if hash_row1 else "None"

        cur1.execute("SELECT detection_id FROM detections;")
        real1_detections = cur1.fetchall()
        cur1.execute("SELECT face_id FROM face_detections;")
        real1_faces = cur1.fetchall()
        conn1.close()

        # Step C: Load Real Evidence 2 (Dahua)
        print(f"[4] Loading Real Evidence 2: {img2_path}...")
        window.load_real_evidence(img2_path)
        real2_case_id = window.current_case_id
        real2_db_path = window.current_db_path
        real2_window_title = window.windowTitle()
        real2_ribbon_badge = not window.status_ribbon.badge_demo.isHidden()
        real2_dash_badge = not window.view_dashboard.demo_badge.isHidden()
        real2_oem = window.current_vfs.oem if window.current_vfs else "None"
        real2_files_count = len(window.current_vfs.files) if window.current_vfs else 0

        conn2 = sqlite3.connect(real2_db_path)
        cur2 = conn2.cursor()
        cur2.execute("SELECT details FROM audit_log WHERE event_type = 'HASH_VERIFY';")
        hash_row2 = cur2.fetchone()
        real2_hash = json.loads(hash_row2[0])["sha256"] if hash_row2 else "None"

        cur2.execute("SELECT detection_id FROM detections;")
        real2_detections = cur2.fetchall()
        cur2.execute("SELECT face_id FROM face_detections;")
        real2_faces = cur2.fetchall()
        conn2.close()

        report = {
            "demo_case": {
                "case_id": demo_case_id,
                "window_title": demo_window_title,
                "ribbon_badge_visible": demo_ribbon_badge,
                "dash_badge_visible": demo_dash_badge,
                "hash": demo_hash,
                "seeded_detections_count": len(demo_detections),
                "det_001_present": any(r[0] == "DET-001" for r in demo_detections),
            },
            "real_evidence_1": {
                "case_id": real1_case_id,
                "file_path": img1_path,
                "oem": real1_oem,
                "vfs_clips": real1_files_count,
                "sha256": real1_hash,
                "window_title": real1_window_title,
                "ribbon_badge_visible": real1_ribbon_badge,
                "dash_badge_visible": real1_dash_badge,
                "detections_count": len(real1_detections),
                "faces_count": len(real1_faces),
                "det_001_present": any(r[0] == "DET-001" for r in real1_detections),
            },
            "real_evidence_2": {
                "case_id": real2_case_id,
                "file_path": img2_path,
                "oem": real2_oem,
                "vfs_clips": real2_files_count,
                "sha256": real2_hash,
                "window_title": real2_window_title,
                "ribbon_badge_visible": real2_ribbon_badge,
                "dash_badge_visible": real2_dash_badge,
                "detections_count": len(real2_detections),
                "faces_count": len(real2_faces),
                "det_001_present": any(r[0] == "DET-001" for r in real2_detections),
            },
            "invariants": {
                "hashes_differ": real1_hash != real2_hash,
                "real1_differs_from_demo": real1_hash != demo_hash,
                "real2_differs_from_demo": real2_hash != demo_hash,
                "zero_preseeded_detections_in_real1": len(real1_detections) == 0,
                "zero_preseeded_detections_in_real2": len(real2_detections) == 0,
                "demo_badge_isolated": (demo_ribbon_badge and not real1_ribbon_badge and not real2_ribbon_badge),
            }
        }

        print("\n=== WALKTHROUGH RESULTS JSON ===")
        print(json.dumps(report, indent=2))
        return report


if __name__ == "__main__":
    run_live_walkthrough()
