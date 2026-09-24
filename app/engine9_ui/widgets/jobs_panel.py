"""Processing / Jobs Queue Panel for Tri-Netra.
Upgrades the persistent bottom status/log bar into an expandable forensic jobs & proof-of-life workstation.
Displays live background jobs, individual progress bars, proof-of-life event ticker & live event stream,
and forensic status across all active operations.
Vertically resizable via QSplitter handle or expand/collapse toggle.
"""

from datetime import datetime
from typing import Optional, Dict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFrame, QSplitter, QTabWidget, QCheckBox, QApplication
)

from app.engine9_ui.job_manager import JobManager, ForensicJob, JobStatus
from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME


class JobsPanel(QWidget):
    """
    Expandable bottom shell widget combining:
    1. Single-line collapsed bar with proof-of-life event ticker and active jobs badge.
    2. Expandable multi-tab workstation showing:
       - Tab 0: Forensic Background Jobs queue with live progress bars and status.
       - Tab 1: Real-time Proof-of-Life live operation stream with timestamps and copy/clear.
    Vertically resizable via QSplitter handle or expandable toggle button.
    """

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.job_manager = JobManager.instance()
        self._is_expanded = False
        self._last_expanded_height = 240
        self._row_map: Dict[str, int] = {}  # job_id -> table row
        self.setMinimumHeight(44)

        self.init_ui()
        self._wire_signals()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 4, 6, 4)
        self.layout.setSpacing(4)

        # 1. Collapsed Bar (always visible)
        self.bar_frame = QFrame(self)
        self.bar_frame.setFixedHeight(36)
        self.bar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 4px;
            }}
        """)
        bar_layout = QHBoxLayout(self.bar_frame)
        bar_layout.setContentsMargins(8, 2, 8, 2)
        bar_layout.setSpacing(10)

        # Proof-of-life ticker
        self.lbl_ticker = QLabel("Proof-of-Life: Waiting for engine operations...", self.bar_frame)
        self.lbl_ticker.setStyleSheet("color: #58A6FF; font-family: Consolas, monospace; font-size: 11px;")
        bar_layout.addWidget(self.lbl_ticker, stretch=1)

        # Active jobs summary badge
        self.lbl_jobs_summary = QLabel("Jobs: Idle", self.bar_frame)
        self.lbl_jobs_summary.setStyleSheet("""
            color: #8B949E;
            font-family: Consolas, monospace;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 8px;
            background-color: #161B22;
            border-radius: 3px;
            border: 1px solid #30363D;
        """)
        bar_layout.addWidget(self.lbl_jobs_summary)

        # Mini global progress bar (visible when any job is running)
        self.mini_progress = QProgressBar(self.bar_frame)
        self.mini_progress.setRange(0, 100)
        self.mini_progress.setValue(0)
        self.mini_progress.setFixedHeight(12)
        self.mini_progress.setFixedWidth(100)
        self.mini_progress.setTextVisible(False)
        self.mini_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #21262D;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {DFIR_DARK_THEME['accent_blue']};
            }}
        """)
        self.mini_progress.setVisible(False)
        bar_layout.addWidget(self.mini_progress)

        # Expand / Collapse toggle button
        self.btn_toggle = QPushButton("▲ Proof-of-Life & Jobs (0)", self.bar_frame)
        self.btn_toggle.setMinimumWidth(170)
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 3px;
                padding: 3px 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #30363D;
                color: #FFFFFF;
            }}
        """)
        self.btn_toggle.clicked.connect(self._toggle_expand)
        bar_layout.addWidget(self.btn_toggle)

        self.layout.addWidget(self.bar_frame)

        # 2. Expanded Queue Table & Proof-of-Life Tabs (collapsible & vertically resizable)
        self.queue_frame = QFrame(self)
        self.queue_frame.setMinimumHeight(150)
        self.queue_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 4px;
            }}
        """)
        queue_layout = QVBoxLayout(self.queue_frame)
        queue_layout.setContentsMargins(4, 4, 4, 4)
        queue_layout.setSpacing(4)

        # Tabs for Jobs Queue vs Proof-of-Life Event Stream
        self.tabs = QTabWidget(self.queue_frame)
        self.tabs.setMinimumHeight(140)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                background-color: #0D1117;
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background-color: #161B22;
                color: #8B949E;
                padding: 4px 12px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: #21262D;
                color: {DFIR_DARK_THEME['accent_blue']};
                border-bottom: 2px solid {DFIR_DARK_THEME['accent_blue']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #21262D;
                color: #C9D1D9;
            }}
        """)

        # Tab 0: Forensic Jobs Queue
        tab_jobs = QWidget()
        tab_jobs_layout = QVBoxLayout(tab_jobs)
        tab_jobs_layout.setContentsMargins(2, 2, 2, 2)
        tab_jobs_layout.setSpacing(0)

        self.table = QTableWidget(0, 7, tab_jobs)
        self.table.setHorizontalHeaderLabels([
            "Job ID", "Type", "Description", "Status", "Progress", "Start Time", "Details / Error"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 140)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #0D1117;
                color: {DFIR_DARK_THEME['text_normal']};
                gridline-color: {DFIR_DARK_THEME['border_color']};
                border: none;
                font-family: Consolas, monospace;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: #161B22;
                color: #8B949E;
                font-weight: bold;
                border: 1px solid #30363D;
                padding: 4px;
            }}
        """)
        self.table.setMinimumHeight(100)
        tab_jobs_layout.addWidget(self.table)
        self.tabs.addTab(tab_jobs, "⚡ Jobs Queue (0)")

        # Tab 1: Proof-of-Life Live Event Stream
        tab_log = QWidget()
        tab_log_layout = QVBoxLayout(tab_log)
        tab_log_layout.setContentsMargins(4, 4, 4, 4)
        tab_log_layout.setSpacing(4)

        # Toolbar above live log table
        log_toolbar = QHBoxLayout()
        log_toolbar.setContentsMargins(2, 0, 2, 0)
        log_toolbar.setSpacing(8)

        lbl_log_hint = QLabel("Live Proof-of-Life forensic operation stream emitted by engine subsystems:")
        lbl_log_hint.setStyleSheet("color: #8B949E; font-size: 10px; font-family: 'Segoe UI', sans-serif;")
        log_toolbar.addWidget(lbl_log_hint)
        log_toolbar.addStretch()

        self.chk_log_autoscroll = QCheckBox("Auto-scroll")
        self.chk_log_autoscroll.setChecked(True)
        self.chk_log_autoscroll.setStyleSheet("color: #C9D1D9; font-size: 10px;")
        log_toolbar.addWidget(self.chk_log_autoscroll)

        self.btn_copy_log = QPushButton("Copy Stream")
        self.btn_copy_log.setStyleSheet(f"""
            QPushButton {{
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #30363D;
                color: #FFFFFF;
            }}
        """)
        self.btn_copy_log.clicked.connect(self._copy_log_to_clipboard)
        log_toolbar.addWidget(self.btn_copy_log)

        self.btn_clear_log = QPushButton("Clear")
        self.btn_clear_log.setStyleSheet(f"""
            QPushButton {{
                background-color: #21262D;
                color: #8B949E;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: #30363D;
                color: #F85149;
            }}
        """)
        self.btn_clear_log.clicked.connect(self._clear_log)
        log_toolbar.addWidget(self.btn_clear_log)

        tab_log_layout.addLayout(log_toolbar)

        self.log_table = QTableWidget(0, 3, tab_log)
        self.log_table.setHorizontalHeaderLabels(["Timestamp", "Event Type", "Operation / Proof-of-Life Message"])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #0D1117;
                color: {DFIR_DARK_THEME['text_normal']};
                gridline-color: {DFIR_DARK_THEME['border_color']};
                border: none;
                font-family: Consolas, monospace;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: #161B22;
                color: #8B949E;
                font-weight: bold;
                border: 1px solid #30363D;
                padding: 4px;
            }}
        """)
        self.log_table.setMinimumHeight(100)
        tab_log_layout.addWidget(self.log_table)

        self.tabs.addTab(tab_log, "📜 Proof-of-Life Stream (0)")

        queue_layout.addWidget(self.tabs)

        self.queue_frame.setVisible(False)
        self.layout.addWidget(self.queue_frame, stretch=1)

    def _wire_signals(self):
        # Case session event logged -> updates ticker & stream
        self.session.event_logged.connect(self._on_event_logged)

        # Job Manager signals
        self.job_manager.job_added.connect(self._on_job_added)
        self.job_manager.job_updated.connect(self._on_job_updated)

    def _toggle_expand(self):
        self.set_expanded(not self._is_expanded, adjust_splitter=True)

    def set_expanded(self, expanded: bool, adjust_splitter: bool = True):
        self._is_expanded = expanded
        self.queue_frame.setVisible(self._is_expanded)
        self._update_toggle_button_text()

        if expanded:
            self.setMinimumHeight(180)
            self.setMaximumHeight(16777215)
        else:
            self.setMinimumHeight(44)

        if adjust_splitter:
            splitter = self.parentWidget()
            if isinstance(splitter, QSplitter):
                sizes = splitter.sizes()
                if len(sizes) == 2:
                    total_h = sum(sizes)
                    if expanded:
                        target_bottom = max(240, self._last_expanded_height)
                        if total_h - target_bottom < 150:
                            target_bottom = max(180, total_h - 150)
                        target_top = max(100, total_h - target_bottom)
                        splitter.setSizes([target_top, target_bottom])
                    else:
                        if sizes[1] >= 150:
                            self._last_expanded_height = sizes[1]
                        collapsed_h = 44
                        splitter.setSizes([total_h - collapsed_h, collapsed_h])

    def _update_toggle_button_text(self):
        arrow = "▼" if self._is_expanded else "▲"
        total = len(self.job_manager.jobs)
        self.btn_toggle.setText(f"{arrow} Proof-of-Life & Jobs ({total})")

    def _update_tab_titles(self):
        total_jobs = len(self.job_manager.jobs)
        total_logs = self.log_table.rowCount()
        self.tabs.setTabText(0, f"⚡ Jobs Queue ({total_jobs})")
        self.tabs.setTabText(1, f"📜 Proof-of-Life Stream ({total_logs})")

    def _copy_log_to_clipboard(self):
        lines = []
        for r in range(self.log_table.rowCount()):
            ts = self.log_table.item(r, 0).text() if self.log_table.item(r, 0) else ""
            etype = self.log_table.item(r, 1).text() if self.log_table.item(r, 1) else ""
            msg = self.log_table.item(r, 2).text() if self.log_table.item(r, 2) else ""
            lines.append(f"{ts}\t{etype}\t{msg}")
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        self.btn_copy_log.setText("Copied!")
        QTimer.singleShot(1500, lambda: self.btn_copy_log.setText("Copy Stream"))

    def _clear_log(self):
        self.log_table.setRowCount(0)
        self._update_tab_titles()

    def _on_event_logged(self, event_data: dict):
        etype = event_data.get("event_type", "EVENT")
        msg = event_data.get("message", "")
        ts = event_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if isinstance(ts, str) and "T" in ts:
            ts = ts.replace("T", " ").split(".")[0]

        self.lbl_ticker.setText(f"Proof-of-Life: [{etype}] {msg}")

        # Append to live event stream table
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)

        ts_item = QTableWidgetItem(str(ts))
        ts_item.setForeground(Qt.gray)

        type_item = QTableWidgetItem(f"[{etype}]")
        etype_upper = etype.upper()
        if any(k in etype_upper for k in ["FAIL", "ERR", "TAMPER"]):
            type_item.setForeground(Qt.red)
        elif any(k in etype_upper for k in ["WARN", "SIMULAT"]):
            type_item.setForeground(Qt.yellow)
        elif any(k in etype_upper for k in ["SUCCESS", "DONE", "VERIF", "MATCH"]):
            type_item.setForeground(Qt.green)
        else:
            type_item.setForeground(Qt.cyan)

        msg_item = QTableWidgetItem(str(msg))
        msg_item.setForeground(Qt.white)

        self.log_table.setItem(row, 0, ts_item)
        self.log_table.setItem(row, 1, type_item)
        self.log_table.setItem(row, 2, msg_item)

        self._update_tab_titles()

        if self.chk_log_autoscroll.isChecked():
            self.log_table.scrollToBottom()

    def _on_job_added(self, job: ForensicJob):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._row_map[job.job_id] = row

        id_item = QTableWidgetItem(job.job_id)
        type_item = QTableWidgetItem(job.job_type)
        desc_item = QTableWidgetItem(job.description)
        status_item = QTableWidgetItem(job.status)
        start_item = QTableWidgetItem(job.start_time or "Just now")
        details_item = QTableWidgetItem(job.status_message)

        # Progress Bar Widget in Column 4
        pbar = QProgressBar()
        pbar.setRange(0, 100)
        pbar.setValue(job.progress)
        pbar.setAlignment(Qt.AlignCenter)
        pbar.setStyleSheet("""
            QProgressBar {
                background-color: #21262D;
                color: #FFFFFF;
                border: 1px solid #30363D;
                border-radius: 2px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #1F6FEB;
            }
        """)

        self.table.setItem(row, 0, id_item)
        self.table.setItem(row, 1, type_item)
        self.table.setItem(row, 2, desc_item)
        self.table.setItem(row, 3, status_item)
        self.table.setCellWidget(row, 4, pbar)
        self.table.setItem(row, 5, start_item)
        self.table.setItem(row, 6, details_item)

        # Connect individual job signals
        job.progress_changed.connect(lambda p, m, j=job: self._on_job_progress(j, p, m))
        job.status_changed.connect(lambda s, j=job: self._on_job_status_changed(j, s))

        self._refresh_summary()
        self._update_toggle_button_text()
        self._update_tab_titles()

    def _on_job_updated(self, job: ForensicJob):
        self._refresh_job_row(job)
        self._refresh_summary()
        self._update_tab_titles()

    def _on_job_progress(self, job: ForensicJob, progress: int, message: str):
        row = self._row_map.get(job.job_id)
        if row is not None and row < self.table.rowCount():
            pbar = self.table.cellWidget(row, 4)
            if isinstance(pbar, QProgressBar):
                pbar.setValue(progress)
            details_item = self.table.item(row, 6)
            if details_item:
                details_item.setText(message)
        self._refresh_summary()

    def _on_job_status_changed(self, job: ForensicJob, status: str):
        row = self._row_map.get(job.job_id)
        if row is not None and row < self.table.rowCount():
            status_item = self.table.item(row, 3)
            if status_item:
                status_item.setText(status)
                if status == JobStatus.COMPLETED:
                    status_item.setForeground(Qt.green)
                elif status == JobStatus.FAILED:
                    status_item.setForeground(Qt.red)
                elif status == JobStatus.RUNNING:
                    status_item.setForeground(Qt.cyan)

            details_item = self.table.item(row, 6)
            if details_item:
                if status == JobStatus.FAILED and job.error_message:
                    details_item.setText(f"Error: {job.error_message}")
                    details_item.setForeground(Qt.red)
                else:
                    details_item.setText(job.status_message)

        self._refresh_summary()

    def _refresh_job_row(self, job: ForensicJob):
        row = self._row_map.get(job.job_id)
        if row is not None and row < self.table.rowCount():
            self._on_job_status_changed(job, job.status)
            self._on_job_progress(job, job.progress, job.status_message)

    def _refresh_summary(self):
        running = sum(1 for j in self.job_manager.jobs if j.status == JobStatus.RUNNING)
        completed = sum(1 for j in self.job_manager.jobs if j.status == JobStatus.COMPLETED)
        failed = sum(1 for j in self.job_manager.jobs if j.status == JobStatus.FAILED)

        if running > 0:
            self.lbl_jobs_summary.setText(f"Jobs: {running} Running | {completed} Done")
            self.lbl_jobs_summary.setStyleSheet("""
                color: #58A6FF;
                font-family: Consolas, monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                background-color: #1F2D40;
                border-radius: 3px;
                border: 1px solid #1F6FEB;
            """)
            self.mini_progress.setVisible(True)
            # Compute average progress of running jobs
            active_progs = [j.progress for j in self.job_manager.jobs if j.status == JobStatus.RUNNING]
            avg = sum(active_progs) // max(1, len(active_progs))
            self.mini_progress.setValue(avg)
        elif failed > 0:
            self.lbl_jobs_summary.setText(f"Jobs: {failed} Failed | {completed} Done")
            self.lbl_jobs_summary.setStyleSheet("""
                color: #F85149;
                font-family: Consolas, monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                background-color: #2D1A1E;
                border-radius: 3px;
                border: 1px solid #DA3633;
            """)
            self.mini_progress.setVisible(False)
        elif completed > 0:
            self.lbl_jobs_summary.setText(f"Jobs: {completed} Completed")
            self.lbl_jobs_summary.setStyleSheet("""
                color: #3FB950;
                font-family: Consolas, monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                background-color: #16241D;
                border-radius: 3px;
                border: 1px solid #238636;
            """)
            self.mini_progress.setVisible(False)
        else:
            self.lbl_jobs_summary.setText("Jobs: Idle")
            self.lbl_jobs_summary.setStyleSheet("""
                color: #8B949E;
                font-family: Consolas, monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                background-color: #161B22;
                border-radius: 3px;
                border: 1px solid #30363D;
            """)
            self.mini_progress.setVisible(False)
