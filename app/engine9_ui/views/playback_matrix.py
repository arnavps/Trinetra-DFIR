"""
Multi-channel playback grid (8 synchronized tiles).
Inactive background tiles decode at 5-10 FPS downscaled proxy resolution;
maximizing a tile switches it to full frame rate and native resolution.
"""

from typing import List, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

from app.engine9_ui.widgets.video_tile import VideoTileWidget


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
        header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 4px;")
        self.main_layout.addWidget(header)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(4)

        # Create 8 tiles in a 2x4 grid
        for idx in range(8):
            row = idx // 4
            col = idx % 4
            tile = VideoTileWidget(self)
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
