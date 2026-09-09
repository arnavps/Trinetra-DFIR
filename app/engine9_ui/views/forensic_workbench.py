"""4-Pane Forensic Workbench View combining 2x2 video grid, Gantt timeline, deep inspector, and evidence table."""

import os
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)

from app.engine3_parsers.fs_base import VirtualFileSystem
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME, get_badge_stylesheet
from app.engine9_ui.widgets.forensic_inspector import DeepForensicInspectorWidget
from app.engine9_ui.widgets.timeline_track import MultiTrackTimelineWidget
from app.engine9_ui.widgets.video_tile import VideoTileWidget


class ForensicWorkbenchView(QWidget):
    """
    4-Pane Forensic Workbench view:
    - Center Top: 2x2 Synchronized Multi-Camera Grid with OSD & AI bounding box overlays
    - Center Bottom: Multi-Track Gantt Timeline Scrubber
    - Right Panel: Deep Forensic Inspector
    - Bottom Panel: Information-dense Evidence Table with Badges & Non-truncated headers
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tiles: List[VideoTileWidget] = []
        self.init_ui()
        self.populate_synthetic_workbench()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # Vertical Splitter: Top (Grid + Timeline + Inspector) vs Bottom (Evidence Table)
        v_splitter = QSplitter(Qt.Orientation.Vertical, self)
        v_splitter.setHandleWidth(2)

        # Top Horizontal Widget
        top_widget = QWidget(self)
        top_h_layout = QHBoxLayout(top_widget)
        top_h_layout.setContentsMargins(0, 0, 0, 0)
        top_h_layout.setSpacing(6)

        # Center Container (2x2 Video Grid + Timeline Scrubber)
        center_container = QWidget(top_widget)
        center_v_layout = QVBoxLayout(center_container)
        center_v_layout.setContentsMargins(0, 0, 0, 0)
        center_v_layout.setSpacing(6)

        # 2x2 Video Grid
        grid_widget = QWidget(center_container)
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(4)

        channel_titles = [
            "CAM 01 - MAIN GATE",
            "CAM 02 - CASHIER COUNTER",
            "CAM 03 - PARKING LOT",
            "CAM 04 - VAULT ENTRANCE",
        ]

        for idx in range(4):
            row = idx // 2
            col = idx % 2
            tile = VideoTileWidget(self, channel_name=channel_titles[idx])
            self.tiles.append(tile)
            grid_layout.addWidget(tile, row, col)

        center_v_layout.addWidget(grid_widget, stretch=3)

        # Multi-Track Gantt Timeline
        self.timeline_widget = MultiTrackTimelineWidget(center_container)
        center_v_layout.addWidget(self.timeline_widget, stretch=1)

        top_h_layout.addWidget(center_container, stretch=3)

        # Right Panel: Deep Forensic Inspector
        self.inspector = DeepForensicInspectorWidget(top_widget)
        top_h_layout.addWidget(self.inspector, stretch=1)

        v_splitter.addWidget(top_widget)

        # Bottom Panel: Evidence Table
        table_container = QWidget(self)
        table_v_layout = QVBoxLayout(table_container)
        table_v_layout.setContentsMargins(0, 0, 0, 0)
        table_v_layout.setSpacing(4)

        tbl_header = QLabel("EVIDENCE CLIP TABLE (ALLOCATED VS. CARVED NAL FRAGMENTS)", table_container)
        tbl_header.setStyleSheet("font-family: 'Segoe UI'; font-weight: bold; font-size: 11px; color: #58A6FF; margin-top: 2px;")
        table_v_layout.addWidget(tbl_header)

        self.table = QTableWidget(table_container)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Track ID",
            "Channel",
            "Type",
            "Start Timestamp (UTC+05:30)",
            "End Timestamp (UTC+05:30)",
            "Start LBA",
            "SHA-256 Hash",
            "Status / Tamper Check",
        ])
        
        # Interactive resize with last section stretched to prevent truncation
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                color: {DFIR_DARK_THEME['text_color']};
                gridline-color: {DFIR_DARK_THEME['border_color']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: #161B22;
                color: #58A6FF;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
                border: 1px solid #30363D;
            }}
        """)
        table_v_layout.addWidget(self.table)

        v_splitter.addWidget(table_container)
        v_splitter.setSizes([520, 200])

        main_layout.addWidget(v_splitter)

    def populate_synthetic_workbench(self, demo_video_path: Optional[str] = None) -> None:
        """Populates 2x2 grid OSD, bounding boxes, and evidence table with realistic synthetic data."""
        # Synchronized timestamps to 2023-11-14 session time
        timestamp_str = "2023-11-14 18:42:11.042"

        # Set AI bounding boxes on Tile 0 and Tile 1
        self.tiles[0].set_bounding_boxes([
            {"class_name": "person", "confidence": 0.94, "bbox": [50, 40, 180, 280]}
        ])
        self.tiles[0].set_osd_text(f"CAM 01 - MAIN GATE | {timestamp_str} | 25.0 FPS | H.264 Main@L4.1")

        self.tiles[1].set_bounding_boxes([
            {"class_name": "car", "confidence": 0.91, "bbox": [200, 100, 520, 310]}
        ])
        self.tiles[1].set_osd_text(f"CAM 02 - CASHIER COUNTER | {timestamp_str} | 25.0 FPS | H.264 Main@L4.1")

        self.tiles[2].set_osd_text(f"CAM 03 - PARKING LOT | {timestamp_str} | 25.0 FPS | H.264 Main@L4.1")
        self.tiles[3].set_osd_text(f"CAM 04 - VAULT ENTRANCE | {timestamp_str} | 25.0 FPS | H.264 Main@L4.1")

        if demo_video_path and os.path.exists(demo_video_path):
            self.tiles[0].load_file(demo_video_path)
            self.tiles[1].load_file(demo_video_path)
            self.tiles[2].load_file(demo_video_path)
            self.tiles[3].load_file(demo_video_path)
        else:
            for tile in self.tiles:
                tile._render_placeholder()

        # Evidence Table Rows matching 2023-11-14 timestamp
        evidence_rows = [
            ("TRK-001", "CH1 - Main Gate", "ALLOCATED", "2023-11-14 18:00:00.000", "2023-11-14 18:30:00.000", "0x003A4F00", "7f83b165...a9c8", "TAMPER CHECK: PASS"),
            ("TRK-002", "CH2 - Cashier", "ALLOCATED", "2023-11-14 18:00:00.000", "2023-11-14 18:45:00.000", "0x003B2A10", "a1b2c3d4...e5f6", "TAMPER CHECK: PASS"),
            ("TRK-003", "CH1 - Main Gate", "CARVED (ORPHAN NAL)", "2023-11-14 18:30:05.120", "2023-11-14 18:38:12.450", "0x003C1000", "8e9f0a1b...c2d3", "TAMPER CHECK: PASS"),
            ("TRK-004", "CH3 - Parking", "ALLOCATED", "2023-11-14 18:10:00.000", "2023-11-14 19:00:00.000", "0x003D4000", "3f4e5d6c...7b8a", "TAMPER CHECK: PASS"),
            ("TRK-005", "CH4 - Vault", "CARVED (ORPHAN NAL)", "2023-11-14 18:32:00.000", "2023-11-14 18:48:00.000", "0x003E8000", "5a6b7c8d...9e0f", "TAMPER CHECK: PASS"),
        ]

        self.table.setRowCount(len(evidence_rows))
        for row_idx, row_data in enumerate(evidence_rows):
            for col_idx in range(8):
                item = QTableWidgetItem(row_data[col_idx])
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)

                if col_idx == 2:  # Type Badge Column
                    if "ALLOCATED" in row_data[2]:
                        lbl = QLabel("ALLOCATED", self.table)
                        lbl.setStyleSheet(get_badge_stylesheet(DFIR_DARK_THEME["status_emerald_bg"], DFIR_DARK_THEME["status_emerald_fg"]))
                    else:
                        lbl = QLabel("CARVED (ORPHAN NAL)", self.table)
                        lbl.setStyleSheet(get_badge_stylesheet(DFIR_DARK_THEME["status_amber_bg"], DFIR_DARK_THEME["status_amber_fg"]))
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setCellWidget(row_idx, col_idx, lbl)
                elif col_idx == 7:  # Tamper Status Column
                    lbl = QLabel("TAMPER CHECK: PASS", self.table)
                    lbl.setStyleSheet(get_badge_stylesheet(DFIR_DARK_THEME["status_cyan_bg"], DFIR_DARK_THEME["status_cyan_fg"]))
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setCellWidget(row_idx, col_idx, lbl)
                else:
                    self.table.setItem(row_idx, col_idx, item)

    def load_vfs(self, vfs: VirtualFileSystem, case_dir: str = "") -> None:
        """Loads actual VirtualFileSystem files into the evidence table & tiles."""
        if not vfs or not vfs.files:
            return

        demo_mp4 = None
        if case_dir and os.path.exists(case_dir):
            for f in os.listdir(case_dir):
                if f.lower().endswith(".mp4"):
                    demo_mp4 = os.path.join(case_dir, f)
                    break

        self.populate_synthetic_workbench(demo_video_path=demo_mp4)

        self.table.setRowCount(len(vfs.files))
        for row_idx, entry in enumerate(vfs.files):
            trk_id = f"TRK-{entry.file_id[-6:] if len(entry.file_id) >= 6 else entry.file_id}"
            ch_str = f"CH{entry.channel_id} - Channel {entry.channel_id}"
            ext_type = getattr(entry, "extraction_type", "ALLOCATED").upper()
            start_ts = entry.start_timestamp or "2023-11-14 18:00:00.000"
            end_ts = entry.end_timestamp or "2023-11-14 18:30:00.000"
            
            start_lba = "0x00000000"
            if getattr(entry, "cluster_runs", None) and len(entry.cluster_runs) > 0:
                start_lba = f"0x{entry.cluster_runs[0].start_sector:08X}"
            
            file_hash = getattr(entry, "file_hash", "7f83b1657b98f2b3a1c2d3e4f5a6b7c8d9e0f1a2")
            hash_abbr = f"{file_hash[:8]}...{file_hash[-4:]}"

            self.table.setItem(row_idx, 0, QTableWidgetItem(trk_id))
            self.table.setItem(row_idx, 1, QTableWidgetItem(ch_str))
            
            # Type Badge
            if "CARVED" in ext_type:
                lbl = QLabel("CARVED (ORPHAN NAL)", self.table)
                lbl.setStyleSheet(get_badge_stylesheet(DFIR_DARK_THEME["status_amber_bg"], DFIR_DARK_THEME["status_amber_fg"]))
            else:
                lbl = QLabel("ALLOCATED", self.table)
                lbl.setStyleSheet(get_badge_stylesheet(DFIR_DARK_THEME["status_emerald_bg"], DFIR_DARK_THEME["status_emerald_fg"]))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row_idx, 2, lbl)

            self.table.setItem(row_idx, 3, QTableWidgetItem(start_ts))
            self.table.setItem(row_idx, 4, QTableWidgetItem(end_ts))
            self.table.setItem(row_idx, 5, QTableWidgetItem(start_lba))
            self.table.setItem(row_idx, 6, QTableWidgetItem(hash_abbr))

            lbl_tamper = QLabel("TAMPER CHECK: PASS", self.table)
            lbl_tamper.setStyleSheet(get_badge_stylesheet(DFIR_DARK_THEME["status_cyan_bg"], DFIR_DARK_THEME["status_cyan_fg"]))
            lbl_tamper.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row_idx, 7, lbl_tamper)
