"""Case list/overview screen."""

from PySide6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget
from app.engine3_parsers.fs_base import VirtualFileSystem


class CaseDashboardView(QWidget):
    """Case summary dashboard and VirtualFileSystem file tree viewer."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.title_label = QLabel("Case Overview Dashboard", self)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(self.title_label)

        self.info_label = QLabel("No active case loaded.", self)
        self.layout.addWidget(self.info_label)

        self.file_tree = QTreeWidget(self)
        self.file_tree.setHeaderLabels(["File ID / Channel", "Start Timestamp", "End Timestamp", "Size (bytes)"])
        self.layout.addWidget(self.file_tree)

    def load_vfs(self, vfs: VirtualFileSystem, case_id: str = "CASE-DEMO") -> None:
        self.info_label.setText(f"Case ID: {case_id} | OEM Detected: {vfs.oem} | Total Channels: {len(vfs.channels)} | Total Files: {len(vfs.files)}")
        self.file_tree.clear()

        channel_nodes = {}
        for ch in vfs.channels:
            ch_item = QTreeWidgetItem(self.file_tree, [ch.channel_name, ch.start_timestamp or "", ch.end_timestamp or "", f"{ch.total_files} files"])
            channel_nodes[ch.channel_id] = ch_item

        for entry in vfs.files:
            parent_item = channel_nodes.get(entry.channel_id, self.file_tree)
            QTreeWidgetItem(parent_item, [entry.file_id, entry.start_timestamp, entry.end_timestamp, str(entry.size_bytes)])

        self.file_tree.expandAll()
