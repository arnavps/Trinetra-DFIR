"""PySide6 main window + Fluent-Widgets navigation shell."""

import os
import tempfile
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QStackedWidget, QToolBar, QVBoxLayout, QWidget, QTreeWidget, QTreeWidgetItem
)

from app.engine2_detector.signature_matcher import match_signature
from app.engine3_parsers.dhfs_parser import DhfsParser
from app.engine3_parsers.hikfat_parser import HikFatParser
from app.engine3_parsers.generic_parser import GenericParser
from app.engine3_parsers.fs_base import VirtualFileSystem
from app.engine5_playback.decoder import StreamDecoder
from app.engine6_timeline.normalizer import TimelineNormalizer
from app.engine7_case_db.db import init_db
from app.engine7_case_db.models import ExtractedFile
from app.engine7_case_db.audit_log import log_event, record_extracted_file
from app.engine9_ui.export_module import export_derivative_clip, CONVENIENCE_COPY_LABEL
from app.engine9_ui.views.case_dashboard import CaseDashboardView
from app.engine9_ui.views.disk_hex_view import DiskHexView
from app.engine9_ui.views.playback_matrix import PlaybackMatrixView
from app.engine9_ui.views.search_panel import SearchPanelWidget
from app.engine9_ui.views.suspect_journey_view import SuspectJourneyViewWidget
from app.engine10_compliance.bsa_sec63 import SECTION_63_DISCLAIMER
from app.engine10_compliance.report_builder import generate_case_report_pdf_with_sec63
from tests.fixtures.generate_synthetic_images import generate_dahua_image, generate_hikvision_image, generate_unknown_oem_image


DARK_SLATE_STYLESHEET = """
QMainWindow {
    background-color: #0B0F19;
    color: #F8FAFC;
}
QWidget {
    background-color: #0B0F19;
    color: #F8FAFC;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QToolBar {
    background-color: #1E293B;
    border-bottom: 1px solid #334155;
    padding: 6px;
    spacing: 8px;
}
QToolButton, QPushButton {
    background-color: #0284C7;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 600;
}
QToolButton:hover, QPushButton:hover {
    background-color: #38BDF8;
    color: #0F172A;
}
QPushButton:pressed {
    background-color: #0369A1;
}
QListWidget {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px;
}
QListWidget::item {
    padding: 10px 12px;
    border-radius: 4px;
    color: #94A3B8;
    font-weight: 600;
}
QListWidget::item:selected {
    background-color: #0284C7;
    color: #FFFFFF;
}
QListWidget::item:hover:!selected {
    background-color: #334155;
    color: #F8FAFC;
}
QStackedWidget {
    background-color: #0B0F19;
}
QTreeWidget, QTableWidget, QTextEdit, QLineEdit, QComboBox {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 4px;
}
QHeaderView::section {
    background-color: #334155;
    color: #F8FAFC;
    padding: 4px;
    font-weight: bold;
    border: none;
}
"""


class MainWindow(QMainWindow):
    """Main desktop interface for UniDVR-Forensics with full engine integration."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("UniDVR-Forensics — Multi-Vendor DVR/NVR Forensic Platform (Draft 3)")
        self.resize(1280, 800)
        self.setStyleSheet(DARK_SLATE_STYLESHEET)

        self.current_image_path: Optional[str] = None
        self.current_vfs: Optional[VirtualFileSystem] = None
        self.current_case_id: str = "CASE-2026-DEMO"
        self.current_db_path: Optional[str] = None
        self.timeline_normalizer = TimelineNormalizer()

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 1. Navigation sidebar (5 Core Views)
        self.nav_list = QListWidget(self)
        self.nav_list.setFixedWidth(220)
        self.nav_list.addItem("Case Dashboard")
        self.nav_list.addItem("Native Playback")
        self.nav_list.addItem("Disk Hex View")
        self.nav_list.addItem("AI Semantic Search")
        self.nav_list.addItem("Suspect Journey Re-ID")
        self.nav_list.currentRowChanged.connect(self._change_view)
        main_layout.addWidget(self.nav_list)

        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(0, 0, 0, 0)
        right_panel.setSpacing(6)

        # 2. Top Action Toolbar
        toolbar = QToolBar("Primary Toolbar", self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self.btn_open = QPushButton("Open Evidence Image", self)
        self.btn_open.clicked.connect(self._open_image)
        toolbar.addWidget(self.btn_open)

        self.btn_synthetic = QPushButton("Load Synthetic Test Case", self)
        self.btn_synthetic.clicked.connect(self._load_synthetic_demo)
        toolbar.addWidget(self.btn_synthetic)

        self.btn_sec63 = QPushButton("Generate BSA Sec. 63 Certificate", self)
        self.btn_sec63.clicked.connect(self._generate_bsa_cert)
        toolbar.addWidget(self.btn_sec63)

        self.btn_export = QPushButton("Export Derivative Clip", self)
        self.btn_export.clicked.connect(self._export_derivative)
        toolbar.addWidget(self.btn_export)

        # 3. Stacked Views Container
        self.stack = QStackedWidget(self)
        self.view_dashboard = CaseDashboardView(self)
        self.view_playback = PlaybackMatrixView(self)
        self.view_hex = DiskHexView(self)
        self.view_search = SearchPanelWidget(parent=self)
        self.view_reid = SuspectJourneyViewWidget(parent=self)

        self.stack.addWidget(self.view_dashboard)
        self.stack.addWidget(self.view_playback)
        self.stack.addWidget(self.view_hex)
        self.stack.addWidget(self.view_search)
        self.stack.addWidget(self.view_reid)

        right_panel.addWidget(self.stack)
        main_layout.addLayout(right_panel)

        # Connect Case Dashboard Tree Double Click -> Seeks Native Playback Tile
        self.view_dashboard.file_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)

        self.nav_list.setCurrentRow(0)

    def _change_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def _open_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open DVR Image", "", "Raw DD Images (*.dd *.raw *.E01);;All Files (*)"
        )
        if file_path:
            self.load_image(file_path)

    def _load_synthetic_demo(self) -> None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        demo_dir = os.path.join(project_root, "demo_case")
        os.makedirs(demo_dir, exist_ok=True)
        demo_image_path = os.path.join(demo_dir, "hikvision_demo.dd")
        if not os.path.exists(demo_image_path):
            generate_hikvision_image(demo_image_path, size_bytes=5 * 1024 * 1024)
        self.load_image(demo_image_path, case_id="CASE-SYNTHETIC-HIKVISION")

    def load_image(self, image_path: str, case_id: str = "CASE-2026-DEMO") -> None:
        self.current_image_path = image_path
        self.current_case_id = case_id

        # Setup Case DB
        case_dir = os.path.dirname(os.path.abspath(image_path))
        self.current_db_path = os.path.join(case_dir, "case_audit.db")
        init_db(self.current_db_path)

        log_event(
            db_path=self.current_db_path,
            case_id=self.current_case_id,
            event_type="acquisition_loaded",
            details={"image_path": image_path, "status": "read_only_mounted"},
        )

        match_res = match_signature(image_path)

        if match_res.oem == "Hikvision":
            parser = HikFatParser()
            self.current_vfs = parser.parse(image_path)
        elif match_res.oem == "Dahua":
            parser = DhfsParser()
            self.current_vfs = parser.parse(image_path)
        else:
            parser = GenericParser()
            self.current_vfs = parser.parse(image_path)

        if self.current_vfs:
            self.view_dashboard.load_vfs(self.current_vfs, case_id=self.current_case_id)
            self.view_hex.set_image_path(image_path)
            self.view_search.set_db_path(self.current_db_path)
            self.view_reid.set_db_path(self.current_db_path)

            for entry in self.current_vfs.files:
                ext_file_rec = ExtractedFile(
                    file_id=entry.file_id,
                    case_id=self.current_case_id,
                    channel_id=entry.channel_id,
                    start_timestamp=entry.start_timestamp,
                    end_timestamp=entry.end_timestamp,
                    size_bytes=entry.size_bytes,
                    file_hash=getattr(entry, "file_hash", "0" * 64),
                    extraction_type=getattr(entry, "extraction_type", "parsed"),
                    storage_path=self.current_image_path,
                )
                record_extracted_file(self.current_db_path, ext_file_rec)

            if self.current_vfs.files:
                self._play_vfs_entry(self.current_vfs.files[0], tile_index=0)

    def _play_vfs_entry(self, entry, tile_index: int = 0) -> None:
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            return

        with open(self.current_image_path, "rb") as f:
            if getattr(entry, "cluster_runs", None):
                start_sec = entry.cluster_runs[0].start_sector
                sec_cnt = entry.cluster_runs[0].sector_count
                f.seek(start_sec * 512)
                stream_bytes = f.read(sec_cnt * 512)
            else:
                f.seek(0)
                stream_bytes = f.read(min(entry.size_bytes, 10 * 1024 * 1024))

        self.view_playback.load_clip(stream_bytes, oem=self.current_vfs.oem if self.current_vfs else "auto", tile_index=tile_index)

    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if not self.current_vfs:
            return
        file_id = item.text(0)
        target_entry = next((f for f in self.current_vfs.files if f.file_id == file_id), None)
        if target_entry:
            tile_idx = (target_entry.channel_id - 1) % 8
            self._play_vfs_entry(target_entry, tile_index=tile_idx)
            self.nav_list.setCurrentRow(1)  # Switch to Native Playback View

    def _generate_bsa_cert(self) -> None:
        if not self.current_db_path or not os.path.exists(self.current_db_path):
            QMessageBox.warning(self, "No Active Case", "Please open an evidence drive image before generating a certificate.")
            return

        out_pdf = os.path.join(os.path.dirname(self.current_db_path), f"BSA_Sec63_{self.current_case_id}.pdf")
        generate_case_report_pdf_with_sec63(self.current_db_path, self.current_case_id, out_pdf)

        QMessageBox.information(
            self,
            "BSA Section 63 Certificate Generated",
            f"Court-ready Section 63 BSA draft certificate generated successfully:\n\n{out_pdf}\n\nNotice: {SECTION_63_DISCLAIMER}",
        )

    def _export_derivative(self) -> None:
        if not self.current_image_path or not self.current_vfs or not self.current_vfs.files:
            QMessageBox.warning(self, "No Active Clip", "Please open an evidence drive image with loaded clips first.")
            return

        first_file = self.current_vfs.files[0]
        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tmp:
            tmp_raw = tmp.name

        try:
            with open(self.current_image_path, "rb") as f_in, open(tmp_raw, "wb") as f_out:
                if getattr(first_file, "cluster_runs", None):
                    f_in.seek(first_file.cluster_runs[0].start_sector * 512)
                    f_out.write(f_in.read(first_file.cluster_runs[0].sector_count * 512))
                else:
                    f_in.seek(0)
                    f_out.write(f_in.read(min(first_file.size_bytes, 10 * 1024 * 1024)))

            out_export = os.path.join(os.path.dirname(self.current_db_path), f"export_{first_file.file_id}.mp4")
            res = export_derivative_clip(
                db_path=self.current_db_path,
                case_id=self.current_case_id,
                input_raw_path=tmp_raw,
                output_export_path=out_export,
            )

            QMessageBox.information(
                self,
                "Derivative Export Created",
                f"Derivative clip exported successfully:\n\nPath: {res['export_path']}\nSHA-256: {res['export_hash'][:16]}...\n\nMandatory Classification: {CONVENIENCE_COPY_LABEL}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export derivative clip: {e}")
        finally:
            if os.path.exists(tmp_raw):
                try:
                    os.remove(tmp_raw)
                except Exception:
                    pass


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


