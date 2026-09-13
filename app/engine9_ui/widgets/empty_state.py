"""Standardized honest empty-state widget for Trinetra-DFIR pages."""

from typing import Optional, Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME


class EmptyStateWidget(QWidget):
    """
    Standardized empty-state container.
    Renders an honest, professional explanation when prerequisite data is not yet available.
    Never papers over missing data with mock rows or placeholder metrics.
    """

    def __init__(
        self,
        icon_str: str = "🔍",
        title: str = "No Data Available",
        description: str = "Prerequisite steps have not yet been executed for this evidence.",
        button_text: Optional[str] = None,
        button_callback: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setSpacing(12)

        # Icon
        self.lbl_icon = QLabel(icon_str, self)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet("font-size: 42px; margin-bottom: 4px;")
        self.layout.addWidget(self.lbl_icon)

        # Title
        self.lbl_title = QLabel(title, self)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 16px;
            font-weight: bold;
            color: {DFIR_DARK_THEME['text_bright']};
        """)
        self.layout.addWidget(self.lbl_title)

        # Description
        self.lbl_desc = QLabel(description, self)
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setMaximumWidth(520)
        self.lbl_desc.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 12px;
            color: {DFIR_DARK_THEME['text_muted']};
            line-height: 1.4;
        """)
        self.layout.addWidget(self.lbl_desc)

        # Action Button (optional)
        if button_text:
            self.btn_action = QPushButton(button_text, self)
            self.btn_action.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DFIR_DARK_THEME['accent_blue']};
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 8px 18px;
                    border-radius: 4px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #79C0FF;
                    color: #0D1117;
                }}
            """)
            if button_callback:
                self.btn_action.clicked.connect(button_callback)
            self.layout.addWidget(self.btn_action, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_message(self, title: str, description: str, icon_str: Optional[str] = None):
        self.lbl_title.setText(title)
        self.lbl_desc.setText(description)
        if icon_str:
            self.lbl_icon.setText(icon_str)
