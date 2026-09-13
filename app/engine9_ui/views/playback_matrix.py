"""
Multi-channel playback grid (8 synchronized tiles).
Inactive background tiles decode at 5-10 FPS downscaled proxy resolution;
maximizing a tile switches it to full frame rate and native resolution.
"""

import os
from typing import List, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

from app.engine9_ui.widgets.video_tile import VideoTileWidget
from app.engine3_parsers.fs_base import VirtualFileSystem


class PlaybackMatrixView(QWidget):
    """Multi-channel synchronized 8-tile playback matrix view."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tiles: List[VideoTileWidget] = []
        self.maximized_tile: Optional[VideoTileWidget] = None
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("Multi-Channel Playback Matrix (8-Tile Synchronized Grid)")
        header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 4px; color: #58A6FF;")
        self.main_layout.addWidget(header)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(4)

        channel_labels = [
            "CAM 01 - MAIN GATE",
            "CAM 02 - CASHIER COUNTER",
            "CAM 03 - PARKING LOT",
            "CAM 04 - VAULT ENTRANCE",
            "CAM 05 - REAR PERIMETER",
            "CAM 06 - SERVER ROOM",
            "CAM 07 - LOADING DOCK",
            "CAM 08 - EXECUTIVE LOBBY",
        ]

        # Create 8 tiles in a 2x4 grid
        for idx in range(8):
            row = idx // 4
            col = idx % 4
            ch_name = channel_labels[idx]
            tile = VideoTileWidget(self, channel_name=ch_name)
            tile.set_osd_text(f"{ch_name}")
            tile.setToolTip(f"Camera Channel {idx + 1}")
            self.tiles.append(tile)
            self.grid_layout.addWidget(tile, row, col)

        self.main_layout.addWidget(self.grid_widget)

        # Matrix Controls
        controls = QHBoxLayout()
        self.btn_play_all = QPushButton("Play All Channels")
        self.btn_play_all.clicked.connect(self.play_all)
        controls.addWidget(self.btn_play_all)

        self.btn_stop_all = QPushButton("Stop All Channels")
        self.btn_stop_all.clicked.connect(self.stop_all)
        controls.addWidget(self.btn_stop_all)

        self.btn_reset_grid = QPushButton("Reset Grid View")
        self.btn_reset_grid.clicked.connect(self.restore_grid)
        controls.addWidget(self.btn_reset_grid)

        self.main_layout.addLayout(controls)

    def load_clip(self, stream_buffer: bytes, oem: str = "auto", tile_index: int = 0) -> int:
        if 0 <= tile_index < len(self.tiles):
            return self.tiles[tile_index].load_stream(stream_buffer, oem=oem)
        return 0

    def load_case_video_file(self, file_path: str, tile_index: int = 0) -> bool:
        """Loads a real video clip file directly into a specified tile."""
        if 0 <= tile_index < len(self.tiles):
            res = self.tiles[tile_index].load_file(file_path)
            self.tiles[tile_index].set_osd_text(
                f"CAM {tile_index + 1:02d} - {os.path.basename(file_path)}"
            )
            return res
        return False

    def load_vfs(self, vfs: VirtualFileSystem, case_dir: str = "") -> None:
        """Loads VFS channel videos and directory files across matrix tiles."""
        if not vfs:
            return

        # Check for demo mp4 file in case_dir if available
        mp4_files = []
        if case_dir and os.path.exists(case_dir):
            for f in os.listdir(case_dir):
                if f.lower().endswith(".mp4"):
                    mp4_files.append(os.path.join(case_dir, f))

        is_h265 = "HFS" in getattr(vfs, "oem", "") or "HeimVision" in getattr(vfs, "oem", "")
        codec_name = "H.265" if is_h265 else "H.264"
        fps_val = "15.0 FPS" if is_h265 else "25.0 FPS"

        for idx in range(8):
            ch_id = idx + 1
            ch_name = f"CAM {ch_id:02d} - CHANNEL {ch_id}"
            start_ts = ""
            if idx < len(vfs.channels):
                ch_name = f"CAM {ch_id:02d} - {vfs.channels[idx].channel_name}"
                if vfs.channels[idx].start_timestamp:
                    start_ts = vfs.channels[idx].start_timestamp
            elif idx < len(vfs.files):
                if vfs.files[idx].start_timestamp:
                    start_ts = vfs.files[idx].start_timestamp

            self.tiles[idx].channel_name = ch_name
            osd_label = f"{ch_name} | {start_ts} | {fps_val} | {codec_name}" if start_ts else f"{ch_name} | {fps_val} | {codec_name}"
            self.tiles[idx].set_osd_text(osd_label)

            if mp4_files:
                sample_file = mp4_files[idx % len(mp4_files)]
                self.tiles[idx].load_file(sample_file)
            else:
                self.tiles[idx]._render_placeholder()

    def play_all(self):
        for idx, tile in enumerate(self.tiles):
            # Inactive tiles run in proxy mode (10 FPS, downscaled), active/maximized runs full speed
            if self.maximized_tile and tile != self.maximized_tile:
                tile.set_proxy_mode(True, target_fps=5)
            else:
                tile.set_proxy_mode(False, target_fps=25)
            tile.play()

    def stop_all(self):
        for tile in self.tiles:
            tile.stop()

    def maximize_tile(self, tile: VideoTileWidget):
        self.maximized_tile = tile
        for t in self.tiles:
            if t == tile:
                t.show()
                t.set_proxy_mode(False, target_fps=25)
            else:
                t.hide()
                t.set_proxy_mode(True, target_fps=5)

    def restore_grid(self):
        self.maximized_tile = None
        for tile in self.tiles:
            tile.show()
            tile.set_proxy_mode(False, target_fps=25)
