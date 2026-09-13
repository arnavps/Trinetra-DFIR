"""Page 4 — Evidence Tree & Filesystem Explorer.
Populated strictly by real VirtualFileSystem output from engine3_parsers.
Every row shows real channels, timestamps, cluster extents, and extraction_type tags.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.empty_state import EmptyStateWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine3_parsers.fs_base import ExtractedFileEntry


class Page4Explorer(QWidget):
    """
    Page 4: Filesystem Explorer mapping parsed channels, timestamps, and cluster extents.
    Double-clicking or selecting a row loads the clip into the native playback workbench.
    """

    navigate_to_page = Signal(int)

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.init_ui()

        self.session.case_changed.connect(self.refresh_table)
        self.session.vfs_loaded.connect(lambda _: self.refresh_table())
        self.refresh_table()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(14)

        # Header Title
        title = QLabel("FILESYSTEM EXPLORER & EVIDENCE CLIPS", self)
        title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        self.main_layout.addWidget(title)

        self.lbl_subtitle = QLabel("Step 4: Inspect parsed proprietary container records, channel mappings, and allocation extents.", self)
        self.lbl_subtitle.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 12px;")
        self.main_layout.addWidget(self.lbl_subtitle)

        # Empty State
        self.empty_widget = EmptyStateWidget(
            icon_str="📁",
            title="No Filesystem Parsed",
            description="No filesystem has been parsed yet for this evidence. Proceed to Page 3 (OEM Detection) to match signatures and run the appropriate parser.",
            button_text="Go to OEM Detection (Page 3)",
            button_callback=lambda: self.navigate_to_page.emit(3),
            parent=self,
        )
        self.main_layout.addWidget(self.empty_widget)

        # Table & Controls Container
        self.content_widget = QWidget(self)
        self.content_widget.setVisible(False)
        content_v = QVBoxLayout(self.content_widget)
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(10)

        # Summary Bar
        sum_h = QHBoxLayout()
        self.lbl_summary = QLabel("", self)
        self.lbl_summary.setStyleSheet("font-family: Consolas; font-size: 12px; color: #58A6FF; font-weight: bold;")
        sum_h.addWidget(self.lbl_summary)
        sum_h.addStretch()

        self.btn_open_playback = QPushButton("Open Selected in Playback (Page 6) →", self)
        self.btn_open_playback.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['accent_blue']};
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
        """)
        self.btn_open_playback.clicked.connect(self._open_selected_in_playback)
        sum_h.addWidget(self.btn_open_playback)
        content_v.addLayout(sum_h)

        # Evidence Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "File ID", "Channel", "Start Timestamp", "End Timestamp",
            "Extents / Sectors", "Size (bytes)", "Extraction Type"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                gridline-color: {DFIR_DARK_THEME['border_color']};
                color: {DFIR_DARK_THEME['text_normal']};
            }}
            QHeaderView::section {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                color: {DFIR_DARK_THEME['text_bright']};
                font-weight: bold;
                padding: 6px;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
            }}
        """)
        self.table.doubleClicked.connect(lambda _: self._open_selected_in_playback())
        content_v.addWidget(self.table)

        self.main_layout.addWidget(self.content_widget)

    def refresh_table(self):
        vfs = self.session.virtual_file_system
        if vfs is None:
            self.empty_widget.set_message(
                title="No Filesystem Parsed",
                description="No filesystem has been parsed yet for this evidence. Proceed to Page 3 (OEM Detection) to match signatures and run the appropriate parser.",
                icon_str="📁",
            )
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
            return

        all_files = list(vfs.files) + list(self.session.carved_fragments)
        if not all_files:
            self.empty_widget.set_message(
                title="Parser Returned 0 Channels",
                description=f"The {vfs.oem} parser returned no allocated channel files. Return to Page 3 to re-confirm OEM or Page 5 to carve unallocated space.",
                icon_str="⚠️",
            )
            self.empty_widget.setVisible(True)
            self.content_widget.setVisible(False)
            return

        self.empty_widget.setVisible(False)
        self.content_widget.setVisible(True)

        self.lbl_summary.setText(f"OEM: {vfs.oem} | Total Channels: {len(vfs.channels)} | Total Evidence Clips: {len(all_files)}")
        self.table.setRowCount(len(all_files))

        for row, f in enumerate(all_files):
            # File ID
            item_id = QTableWidgetItem(f.file_id)
            item_id.setForeground(Qt.GlobalColor.white)
            item_id.setData(Qt.ItemDataRole.UserRole, f)

            # Channel
            item_ch = QTableWidgetItem(f"CAM {f.channel_id:02d}")

            # Timestamps
            item_start = QTableWidgetItem(f.start_timestamp or "Unknown")
            item_end = QTableWidgetItem(f.end_timestamp or "Unknown")

            # Extents
            if f.cluster_runs:
                run0 = f.cluster_runs[0]
                ext_str = f"Sec {run0.start_sector} (+{run0.sector_count})"
            else:
                ext_str = "Linear Stream"
            item_ext = QTableWidgetItem(ext_str)

            # Size
            mb = f.size_bytes / (1024 * 1024)
            item_sz = QTableWidgetItem(f"{f.size_bytes:,} ({mb:.1f} MB)")

            # Extraction Type Tag
            tag = f.extraction_type.upper()
            item_type = QTableWidgetItem(tag)
            if tag == "PARSED":
                item_type.setForeground(Qt.GlobalColor.green)
            else:
                item_type.setForeground(Qt.GlobalColor.yellow)

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_ch)
            self.table.setItem(row, 2, item_start)
            self.table.setItem(row, 3, item_end)
            self.table.setItem(row, 4, item_ext)
            self.table.setItem(row, 5, item_sz)
            self.table.setItem(row, 6, item_type)

        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _open_selected_in_playback(self):
        curr_row = self.table.currentRow()
        if curr_row >= 0:
            item = self.table.item(curr_row, 0)
            if item:
                file_entry: ExtractedFileEntry = item.data(Qt.ItemDataRole.UserRole)
                self.session.set_active_file(file_entry)
                self.navigate_to_page.emit(6)
