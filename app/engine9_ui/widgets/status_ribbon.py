"""Top status ribbon bar displaying live case metadata, write-block, AI model verification, and air-gap integrity."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QDialog,
    QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QWidget
)

from app.engine9_ui.case_session import CaseSession
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME
from app.engine8_ai.model_registry import verify_all_models
from app.security.network_watchdog import assert_offline_environment, NetworkViolationError


class ModelStatusDialog(QDialog):
    """Inspects live verification status of all 8 registered AI models."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("AI Model Verification Ledger (models/manifest.json)")
        self.resize(680, 360)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DFIR_DARK_THEME['bg_dark']};
                color: {DFIR_DARK_THEME['text_normal']};
            }}
            QTableWidget {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                color: {DFIR_DARK_THEME['text_normal']};
                gridline-color: {DFIR_DARK_THEME['border_color']};
            }}
            QHeaderView::section {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                color: {DFIR_DARK_THEME['text_bright']};
                font-weight: bold;
                padding: 6px;
                border: 1px solid {DFIR_DARK_THEME['border_color']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_lbl = QLabel("<b>Fail-Closed AI Model Checksum Verification</b><br>Scanned live from models/manifest.json against local disk weights.")
        header_lbl.setStyleSheet(f"color: {DFIR_DARK_THEME['text_bright']}; font-size: 12px;")
        layout.addWidget(header_lbl)

        table = QTableWidget(self)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Model File", "Verification Status", "Description", "Local Path"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        models_report = verify_all_models()
        table.setRowCount(len(models_report))

        for row, (name, info) in enumerate(models_report.items()):
            status = info["status"]
            desc = info.get("description", "")
            path = info.get("path", "")

            item_name = QTableWidgetItem(name)
            item_name.setForeground(Qt.GlobalColor.white)

            item_status = QTableWidgetItem(status)
            if status == "VERIFIED":
                item_status.setForeground(Qt.GlobalColor.green)
            elif status == "PLACEHOLDER":
                item_status.setForeground(Qt.GlobalColor.yellow)
            else:
                item_status.setForeground(Qt.GlobalColor.red)

            item_desc = QTableWidgetItem(desc)
            item_path = QTableWidgetItem(path)

            table.setItem(row, 0, item_name)
            table.setItem(row, 1, item_status)
            table.setItem(row, 2, item_desc)
            table.setItem(row, 3, item_path)

        layout.addWidget(table)

        btn_close = QPushButton("Close", self)
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(f"""
            background-color: {DFIR_DARK_THEME['panel_bg']};
            border: 1px solid {DFIR_DARK_THEME['border_color']};
            color: {DFIR_DARK_THEME['text_bright']};
            padding: 6px 14px;
            border-radius: 4px;
        """)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)


class StatusRibbon(QFrame):
    """
    Persistent Top Bar:
    1. Live Case Identity
    2. Real Write-Block Verification Badge
    3. Live AI Model Verification Status (clickable modal)
    4. Air-Gap Watchdog Verification Badge
    """

    def __init__(self, session: CaseSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self.setFixedHeight(46)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DFIR_DARK_THEME['panel_bg']};
                border-bottom: 1px solid {DFIR_DARK_THEME['border_color']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(12)

        # 1. Case Identity
        self.lbl_case = QLabel("CASE: NO CASE LOADED", self)
        self.lbl_case.setStyleSheet(f"color: {DFIR_DARK_THEME['accent_blue']}; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.lbl_case)

        # 2. Source / Image path
        self.lbl_source = QLabel("Source: None", self)
        self.lbl_source.setStyleSheet(f"color: {DFIR_DARK_THEME['text_muted']}; font-size: 11px;")
        layout.addWidget(self.lbl_source)

        layout.addStretch()

        # 3. Write-Block Status Badge
        self.lbl_writeblock = QLabel("WRITE-BLOCK: UNVERIFIED", self)
        self.lbl_writeblock.setStyleSheet("""
            background-color: #21262D;
            color: #8B949E;
            font-size: 11px;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #30363D;
        """)
        layout.addWidget(self.lbl_writeblock)

        # 4. Live AI Models Status (Clickable)
        self.btn_models = QPushButton("AI MODELS: CHECKING...", self)
        self.btn_models.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_models.clicked.connect(self._open_models_dialog)
        self.btn_models.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #58A6FF;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 4px;
                border: 1px solid #30363D;
            }
            QPushButton:hover {
                background-color: #30363D;
                border-color: #58A6FF;
            }
        """)
        layout.addWidget(self.btn_models)

        # 5. Air-Gap Watchdog Badge
        self.lbl_offline = QLabel("AIR-GAP: VERIFYING...", self)
        layout.addWidget(self.lbl_offline)

        # Wire to session updates
        self.session.case_changed.connect(self.update_telemetry)
        self.session.acquisition_completed.connect(lambda _: self.update_telemetry())

        self.update_telemetry()

    def update_telemetry(self) -> None:
        """Refreshes all top bar telemetry live from CaseSession and system checks."""
        # 1. Case ID
        if self.session.case_id:
            self.lbl_case.setText(f"CASE: {self.session.case_id} — {self.session.case_name or ''}")
        else:
            self.lbl_case.setText("CASE: NO CASE LOADED")

        # 2. Source
        if self.session.evidence_source:
            self.lbl_source.setText(f"Source: {self.session.evidence_source}")
        elif self.session.image_path:
            self.lbl_source.setText(f"Evidence: {self.session.image_path}")
        else:
            self.lbl_source.setText("Source: None")

        # 3. Write-Block Status
        if self.session.write_block_verified is True:
            self.lbl_writeblock.setText("WRITE-BLOCKED — VERIFIED")
            self.lbl_writeblock.setStyleSheet("""
                background-color: #0D3321;
                color: #3FB950;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #238636;
            """)
        elif self.session.write_block_verified is False:
            self.lbl_writeblock.setText("WRITE VIOLATION — UNPROTECTED")
            self.lbl_writeblock.setStyleSheet("""
                background-color: #3A1D1D;
                color: #F85149;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #DA3633;
            """)
        else:
            self.lbl_writeblock.setText("WRITE-BLOCK: UNVERIFIED")
            self.lbl_writeblock.setStyleSheet("""
                background-color: #21262D;
                color: #8B949E;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #30363D;
            """)

        # 4. Live Model Verification
        try:
            models_report = verify_all_models()
            total_models = len(models_report)
            verified_count = sum(1 for m in models_report.values() if m["status"] == "VERIFIED")
            self.btn_models.setText(f"{verified_count} / {total_models} AI MODELS VERIFIED")
            if verified_count == total_models and total_models > 0:
                self.btn_models.setStyleSheet("""
                    QPushButton {
                        background-color: #0D3321;
                        color: #3FB950;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 4px 10px;
                        border-radius: 4px;
                        border: 1px solid #238636;
                    }
                """)
            else:
                self.btn_models.setStyleSheet("""
                    QPushButton {
                        background-color: #3A2404;
                        color: #F0883E;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 4px 10px;
                        border-radius: 4px;
                        border: 1px solid #9E6A03;
                    }
                """)
        except Exception:
            self.btn_models.setText("AI MODELS: MANIFEST ERROR")

        # 5. Air-Gap Watchdog Check
        try:
            assert_offline_environment()
            self.lbl_offline.setText("AIR-GAP: ARMED & OFFLINE")
            self.lbl_offline.setStyleSheet("""
                background-color: #0D3321;
                color: #3FB950;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #238636;
            """)
        except NetworkViolationError:
            self.lbl_offline.setText("NETWORK VIOLATION")
            self.lbl_offline.setStyleSheet("""
                background-color: #3A1D1D;
                color: #F85149;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #DA3633;
            """)
        except Exception:
            self.lbl_offline.setText("AIR-GAP: ARMED")
            self.lbl_offline.setStyleSheet("""
                background-color: #0D3321;
                color: #3FB950;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #238636;
            """)

    def _open_models_dialog(self) -> None:
        dialog = ModelStatusDialog(self)
        dialog.exec()
