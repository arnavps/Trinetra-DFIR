"""Tri-Netra Forensic Workstation — Main Window Shell.
Persistent Magnet AXIOM / DVR Examiner layout:
- Top Bar: Live Case Identity, Write-Block Verification, AI Models Checksum Status, Air-Gap Watchdog
- Left Sidebar: 10 Page Navigation + Real Evidence Tree Navigator
- Center: 10 Dedicated Forensic Pages (QStackedWidget)
- Bottom Status Bar: Live Proof-of-Life Scrolling Engine Event Feed

STRICT FORENSIC INTEGRITY: Zero demo modes, zero seeded mock rows, zero hardcoded telemetry literals.
Every value rendered is traceable directly to real backend engine calls against loaded evidence.
"""

import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QLabel, QSplitter,
    QMenuBar, QMenu, QStatusBar, QMessageBox
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine9_ui.widgets.status_ribbon import StatusRibbon

# 10 Dedicated Forensic Pages
from app.engine9_ui.pages.page1_intake import Page1Intake
from app.engine9_ui.pages.page2_acquisition import Page2Acquisition
from app.engine9_ui.pages.page3_oem_detect import Page3OemDetect
from app.engine9_ui.pages.page4_explorer import Page4Explorer
from app.engine9_ui.pages.page5_carver import Page5Carver
from app.engine9_ui.pages.page6_playback import Page6Playback
from app.engine9_ui.pages.page7_timeline import Page7Timeline
from app.engine9_ui.pages.page8_ai_triage import Page8AiTriage
from app.engine9_ui.pages.page9_audit_log import Page9AuditLog
from app.engine9_ui.pages.page10_reporting import Page10Reporting

from app.engine3_parsers.fs_base import ExtractedFileEntry


class MainWindow(QMainWindow):
    """
    Magnet AXIOM / DVR Examiner grade multi-page forensic workstation.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Tri-Netra — Digital Video Forensic Workstation (DFIR)")
        self.resize(1600, 960)
        self.setMinimumSize(1200, 720)

        # Single source of truth
        self.session = CaseSession(self)

        self._init_ui()
        self._init_menu()

        # Connect session signals
        self.session.case_changed.connect(self._update_evidence_tree)
        self.session.vfs_loaded.connect(lambda _: self._update_evidence_tree())
        self.session.fragments_updated.connect(lambda _: self._update_evidence_tree())
        self.session.event_logged.connect(self._on_event_logged)

        self._update_evidence_tree()

    def _init_ui(self):
        # Global Dark Theme
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DFIR_DARK_THEME['bg_dark']};
                color: {DFIR_DARK_THEME['text_normal']};
            }}
            QMenuBar {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                color: {DFIR_DARK_THEME['text_bright']};
                border-bottom: 1px solid {DFIR_DARK_THEME['border_color']};
                font-size: 11px;
            }}
            QMenuBar::item:selected {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                color: {DFIR_DARK_THEME['accent_blue']};
            }}
            QMenu {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                color: {DFIR_DARK_THEME['text_normal']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
            }}
            QMenu::item:selected {{
                background-color: {DFIR_DARK_THEME['accent_blue']};
                color: #FFFFFF;
            }}
            QSplitter::handle {{
                background-color: {DFIR_DARK_THEME['border_color']};
            }}
            QStatusBar {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                color: {DFIR_DARK_THEME['text_muted']};
                border-top: 1px solid {DFIR_DARK_THEME['border_color']};
                font-family: Consolas;
                font-size: 11px;
            }}
        """)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        root_v_layout = QVBoxLayout(central_widget)
        root_v_layout.setContentsMargins(0, 0, 0, 0)
        root_v_layout.setSpacing(0)

        # 1. Persistent Top Status Ribbon
        self.top_ribbon = StatusRibbon(self.session, self)
        root_v_layout.addWidget(self.top_ribbon)

        # 2. Main Horizontal Splitter: Left Sidebar vs Main Page Area
        main_splitter = QSplitter(Qt.Orientation.Horizontal, central_widget)
        main_splitter.setHandleWidth(2)

        # Left Sidebar Container
        sidebar_widget = QWidget(main_splitter)
        sidebar_widget.setMinimumWidth(280)
        sidebar_widget.setMaximumWidth(360)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)
        sidebar_layout.setSpacing(10)

        # 2a. Page Navigation List
        lbl_nav = QLabel("WORKFLOW NAVIGATION", sidebar_widget)
        lbl_nav.setStyleSheet("font-family: 'Segoe UI'; font-weight: bold; font-size: 10px; color: #8B949E; margin-left: 4px;")
        sidebar_layout.addWidget(lbl_nav)

        self.nav_list = QListWidget(sidebar_widget)
        self.nav_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 6px;
                color: {DFIR_DARK_THEME['text_normal']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                padding: 4px;
            }}
            QListWidget::item {{
                height: 32px;
                padding-left: 8px;
                border-radius: 4px;
                margin-bottom: 2px;
            }}
            QListWidget::item:hover {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                color: {DFIR_DARK_THEME['text_bright']};
            }}
            QListWidget::item:selected {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                color: {DFIR_DARK_THEME['accent_blue']};
                font-weight: bold;
                border-left: 3px solid {DFIR_DARK_THEME['accent_blue']};
            }}
        """)

        pages_meta = [
            "1. Case Intake & Acquisition",
            "2. Acquisition & Hashes",
            "3. OEM & Signature Detect",
            "4. Filesystem Explorer",
            "5. Carve Deleted NALs",
            "6. Native Video Playback",
            "7. Timeline Synchronization",
            "8. AI Analytics & Triage",
            "9. Chain-of-Custody Log",
            "10. Export & BSA Reports",
        ]
        for p in pages_meta:
            self.nav_list.addItem(QListWidgetItem(p))
        self.nav_list.currentRowChanged.connect(self._on_page_nav_changed)
        sidebar_layout.addWidget(self.nav_list, stretch=2)

        # 2b. Evidence Navigator Tree
        lbl_tree = QLabel("EVIDENCE NAVIGATOR", sidebar_widget)
        lbl_tree.setStyleSheet(lbl_nav.styleSheet())
        sidebar_layout.addWidget(lbl_tree)

        self.evidence_tree = QTreeWidget(sidebar_widget)
        self.evidence_tree.setHeaderHidden(True)
        self.evidence_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 6px;
                color: {DFIR_DARK_THEME['text_normal']};
                font-family: Consolas, monospace;
                font-size: 11px;
                padding: 4px;
            }}
            QTreeWidget::item {{
                height: 26px;
                border-radius: 3px;
            }}
            QTreeWidget::item:hover {{
                background-color: {DFIR_DARK_THEME['card_bg']};
            }}
            QTreeWidget::item:selected {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                color: {DFIR_DARK_THEME['accent_blue']};
                font-weight: bold;
            }}
        """)
        self.evidence_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        sidebar_layout.addWidget(self.evidence_tree, stretch=3)

        main_splitter.addWidget(sidebar_widget)

        # 3. Center Stacked Pages
        self.stack = QStackedWidget(main_splitter)

        self.page1 = Page1Intake(self.session, self.stack)
        self.page2 = Page2Acquisition(self.session, self.stack)
        self.page3 = Page3OemDetect(self.session, self.stack)
        self.page4 = Page4Explorer(self.session, self.stack)
        self.page5 = Page5Carver(self.session, self.stack)
        self.page6 = Page6Playback(self.session, self.stack)
        self.page7 = Page7Timeline(self.session, self.stack)
        self.page8 = Page8AiTriage(self.session, self.stack)
        self.page9 = Page9AuditLog(self.session, self.stack)
        self.page10 = Page10Reporting(self.session, self.stack)

        # Connect inter-page navigation signals
        for p in [self.page1, self.page2, self.page3, self.page4, self.page5, self.page6, self.page7, self.page8, self.page9, self.page10]:
            p.navigate_to_page.connect(self.go_to_page)

        self.stack.addWidget(self.page1)
        self.stack.addWidget(self.page2)
        self.stack.addWidget(self.page3)
        self.stack.addWidget(self.page4)
        self.stack.addWidget(self.page5)
        self.stack.addWidget(self.page6)
        self.stack.addWidget(self.page7)
        self.stack.addWidget(self.page8)
        self.stack.addWidget(self.page9)
        self.stack.addWidget(self.page10)

        main_splitter.addWidget(self.stack)
        main_splitter.setStretchFactor(1, 4)

        root_v_layout.addWidget(main_splitter)

        # 4. Persistent Bottom Status & Event Log Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.lbl_event_ticker = QLabel("Proof-of-Life: Waiting for engine operations...", self)
        self.lbl_event_ticker.setStyleSheet("color: #58A6FF; font-family: Consolas; font-size: 11px;")
        self.status_bar.addWidget(self.lbl_event_ticker, 1)

        # Set default page to Page 1
        self.nav_list.setCurrentRow(0)

    def _init_menu(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")
        new_case_act = file_menu.addAction("New Case (Intake)...")
        new_case_act.triggered.connect(lambda: self.go_to_page(1))

        open_acq_act = file_menu.addAction("Acquisition & Hashes...")
        open_acq_act.triggered.connect(lambda: self.go_to_page(2))

        file_menu.addSeparator()
        exit_act = file_menu.addAction("Exit")
        exit_act.triggered.connect(self.close)

        # Navigation Menu
        nav_menu = menubar.addMenu("&View")
        for idx in range(1, 11):
            act = nav_menu.addAction(f"Page {idx}: {self.nav_list.item(idx - 1).text()}")
            act.triggered.connect(lambda _, p=idx: self.go_to_page(p))

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        about_act = help_menu.addAction("About Tri-Netra DFIR...")
        about_act.triggered.connect(self._show_about)

    def _on_page_nav_changed(self, row: int):
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)

    def go_to_page(self, page_num: int):
        """Navigates to 1-indexed page."""
        idx = page_num - 1
        if 0 <= idx < self.nav_list.count():
            self.nav_list.setCurrentRow(idx)

    def _update_evidence_tree(self):
        """
        Reconstructs the Evidence Navigator tree live from CaseSession.
        Before any case is loaded, displays: 'No case loaded — File → New Case.'
        """
        self.evidence_tree.clear()

        if not self.session.has_case:
            item_empty = QTreeWidgetItem(self.evidence_tree, ["No case loaded — File → New Case."])
            item_empty.setForeground(0, Qt.GlobalColor.gray)
            return

        # Case Root
        root_text = f"Case: {self.session.case_id}"
        case_root = QTreeWidgetItem(self.evidence_tree, [root_text])
        case_root.setForeground(0, Qt.GlobalColor.white)
        font = case_root.font(0)
        font.setBold(True)
        case_root.setFont(0, font)

        # Evidence Source Node
        source_name = os.path.basename(self.session.image_path or self.session.evidence_source or "Evidence Source Pending")
        src_node = QTreeWidgetItem(case_root, [f"Evidence: {source_name}"])
        src_node.setForeground(0, Qt.GlobalColor.cyan)

        # Parsed Channels (if VFS parsed)
        if self.session.virtual_file_system and self.session.virtual_file_system.files:
            for f in self.session.virtual_file_system.files:
                ch_name = f"CAM {f.channel_id:02d} - {f.file_id} [parsed]"
                ch_node = QTreeWidgetItem(src_node, [ch_name])
                ch_node.setForeground(0, Qt.GlobalColor.green)
                ch_node.setData(0, Qt.ItemDataRole.UserRole, f)

        # Carved Fragments (if any)
        if self.session.carved_fragments:
            for frag in self.session.carved_fragments:
                frag_name = f"Frag {frag.file_id} ({frag.size_bytes}B) [carved_fragment]"
                frag_node = QTreeWidgetItem(src_node, [frag_name])
                frag_node.setForeground(0, Qt.GlobalColor.yellow)
                frag_node.setData(0, Qt.ItemDataRole.UserRole, frag)

        # Unallocated Scan Node
        frag_count = len(self.session.carved_fragments)
        scan_label = f"Unallocated Space Scan ({frag_count} fragments)" if frag_count > 0 else "Unallocated Space Scan (not yet run)"
        scan_node = QTreeWidgetItem(src_node, [scan_label])
        scan_node.setForeground(0, Qt.GlobalColor.gray if frag_count == 0 else Qt.GlobalColor.yellow)
        scan_node.setData(0, Qt.ItemDataRole.UserRole, "GOTO_PAGE_5")

        self.evidence_tree.expandAll()

    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, ExtractedFileEntry):
            self.session.set_active_file(data)
            self.go_to_page(6)  # Playback
        elif data == "GOTO_PAGE_5":
            self.go_to_page(5)  # Carver

    def _on_event_logged(self, event_data: dict):
        ts = event_data.get("timestamp", "")[:19]
        evt = event_data.get("event_type", "")
        msg = event_data.get("message", "")
        self.lbl_event_ticker.setText(f"[{ts}] {evt}: {msg}")

    def _show_about(self):
        QMessageBox.information(
            self,
            "About Tri-Netra DFIR",
            "Tri-Netra — Digital Video Forensic Workstation (DFIR)\n"
            "Compliant with Bharatiya Sakshya Adhiniyam (BSA 2023) Section 63.\n"
            "Air-Gapped, Offline, Multi-Vendor Video Recovery & Analysis Platform."
        )
