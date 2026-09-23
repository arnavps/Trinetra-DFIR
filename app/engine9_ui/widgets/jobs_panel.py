"""Processing / Jobs Queue Panel for Tri-Netra.
Upgrades the persistent bottom status/log bar into an expandable forensic jobs panel.
Displays live background jobs, individual progress bars, proof-of-life event ticker,
and forensic status across all active operations.
"""

from datetime import datetime
from typing import Optional, Dict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFrame
)

from app.engine9_ui.job_manager import JobManager, ForensicJob, JobStatus
from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME


class JobsPanel(QWidget):
    """
    Expandable bottom shell widget combining:
    1. Single-line collapsed bar with proof-of-life event ticker and active jobs badge.
    2. Expandable multi-row queue showing all forensic background jobs with progress.
    """

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.job_manager = JobManager.instance()
        self._is_expanded = False
        self._row_map: Dict[str, int] = {}  # job_id -> table row

        self.init_ui()
        self._wire_signals()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 4, 6, 4)
        self.layout.setSpacing(4)

        # 1. Collapsed Bar (always visible)
        self.bar_frame = QFrame(self)
        self.bar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 4px;
            }}
        """)
        bar_layout = QHBoxLayout(self.bar_frame)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.setSpacing(12)

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
        self.btn_toggle = QPushButton("▲ Jobs Queue (0)", self.bar_frame)
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 3px;
                padding: 3px 8px;
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

        # 2. Expanded Queue Table (collapsible)
        self.queue_frame = QFrame(self)
        self.queue_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 4px;
            }}
        """)
        queue_layout = QVBoxLayout(self.queue_frame)
        queue_layout.setContentsMargins(6, 6, 6, 6)

        self.table = QTableWidget(0, 7, self.queue_frame)
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
        self.table.setFixedHeight(140)
        queue_layout.addWidget(self.table)

        self.queue_frame.setVisible(False)
        self.layout.addWidget(self.queue_frame)

    def _wire_signals(self):
        # Case session event logged -> updates ticker
        self.session.event_logged.connect(self._on_event_logged)

        # Job Manager signals
        self.job_manager.job_added.connect(self._on_job_added)
        self.job_manager.job_updated.connect(self._on_job_updated)

    def _toggle_expand(self):
        self._is_expanded = not self._is_expanded
        self.queue_frame.setVisible(self._is_expanded)
        self._update_toggle_button_text()

    def _update_toggle_button_text(self):
        arrow = "▼" if self._is_expanded else "▲"
        total = len(self.job_manager.jobs)
        self.btn_toggle.setText(f"{arrow} Jobs Queue ({total})")

    def _on_event_logged(self, event_data: dict):
        etype = event_data.get("event_type", "EVENT")
        msg = event_data.get("message", "")
        self.lbl_ticker.setText(f"Proof-of-Life: [{etype}] {msg}")

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

    def _on_job_updated(self, job: ForensicJob):
        self._refresh_job_row(job)
        self._refresh_summary()

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
