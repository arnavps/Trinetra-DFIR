"""Multi-Track Gantt Recording Timeline Scrub Widget."""

from typing import List, Dict, Any
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME


class MultiTrackTimelineWidget(QFrame):
    """
    Horizontal multi-track Gantt timeline scrubber.
    Renders color-coded recording segments across 4 camera channels:
    - Solid Emerald (#3FB950): Normal Continuous Recording
    - Cyan (#38BDF8): Motion-Triggered Recording
    - Amber/Orange (#F0883E): Recovered via NAL Carving
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.setMaximumHeight(180)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                border: 1px solid {DFIR_DARK_THEME['border_color']};
                border-radius: 6px;
            }}
        """)

        # Sample mock timeline data across CH1-CH4
        self.tracks = [
            {
                "channel": "CH1 - MAIN GATE",
                "segments": [
                    {"start": 0.05, "end": 0.35, "type": "normal"},
                    {"start": 0.40, "end": 0.55, "type": "motion"},
                    {"start": 0.60, "end": 0.72, "type": "carved"},
                    {"start": 0.75, "end": 0.95, "type": "normal"},
                ]
            },
            {
                "channel": "CH2 - CASHIER",
                "segments": [
                    {"start": 0.00, "end": 0.45, "type": "normal"},
                    {"start": 0.50, "end": 0.65, "type": "carved"},
                    {"start": 0.70, "end": 0.98, "type": "motion"},
                ]
            },
            {
                "channel": "CH3 - PARKING",
                "segments": [
                    {"start": 0.10, "end": 0.30, "type": "motion"},
                    {"start": 0.35, "end": 0.80, "type": "normal"},
                    {"start": 0.85, "end": 0.95, "type": "carved"},
                ]
            },
            {
                "channel": "CH4 - VAULT",
                "segments": [
                    {"start": 0.00, "end": 0.25, "type": "normal"},
                    {"start": 0.30, "end": 0.48, "type": "carved"},
                    {"start": 0.55, "end": 0.90, "type": "normal"},
                ]
            },
        ]

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.contentsRect()
        width = rect.width()
        height = rect.height()

        # Draw Header Bar
        painter.setPen(QColor(DFIR_DARK_THEME["border_color"]))
        painter.setBrush(QColor("#0D1117"))
        painter.drawRect(0, 0, width, 24)

        painter.setPen(QColor(DFIR_DARK_THEME["text_bright"]))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(8, 16, "MULTI-TRACK RECORDING TIMELINE (CH1–CH4 SCALES)")

        # Legend (Top Right)
        legend_x = width - 360
        painter.setFont(QFont("Consolas", 8))
        
        # Legend Normal
        painter.setBrush(QColor("#0D3321"))
        painter.setPen(QColor("#3FB950"))
        painter.drawRect(legend_x, 6, 10, 10)
        painter.drawText(legend_x + 14, 15, "Continuous")

        # Legend Motion
        painter.setBrush(QColor("#0C2D48"))
        painter.setPen(QColor("#38BDF8"))
        painter.drawRect(legend_x + 90, 6, 10, 10)
        painter.drawText(legend_x + 104, 15, "Motion")

        # Legend Carved NAL
        painter.setBrush(QColor("#3A2404"))
        painter.setPen(QColor("#F0883E"))
        painter.drawRect(legend_x + 160, 6, 10, 10)
        painter.drawText(legend_x + 174, 15, "Carved (Orphan NAL)")

        # Draw Track Channels
        left_label_w = 120
        track_area_w = width - left_label_w - 16
        track_h = (height - 32) / len(self.tracks)

        for i, track in enumerate(self.tracks):
            top_y = 28 + (i * track_h)

            # Channel Label
            painter.setPen(QColor(DFIR_DARK_THEME["text_muted"]))
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            painter.drawText(8, int(top_y + track_h / 2 + 4), track["channel"])

            # Track Background Lane
            lane_rect = QRectF(left_label_w, top_y + 2, track_area_w, track_h - 4)
            painter.setPen(QPen(QColor(DFIR_DARK_THEME["border_color"]), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor("#0D1117"))
            painter.drawRoundedRect(lane_rect, 3, 3)

            # Draw Segments
            for seg in track["segments"]:
                seg_x = left_label_w + (seg["start"] * track_area_w)
                seg_w = (seg["end"] - seg["start"]) * track_area_w
                seg_rect = QRectF(seg_x, top_y + 4, seg_w, track_h - 8)

                if seg["type"] == "normal":
                    fill_c = QColor("#0D3321")
                    border_c = QColor("#3FB950")
                elif seg["type"] == "motion":
                    fill_c = QColor("#0C2D48")
                    border_c = QColor("#38BDF8")
                else:  # carved
                    fill_c = QColor("#3A2404")
                    border_c = QColor("#F0883E")

                painter.setPen(QPen(border_c, 1))
                painter.setBrush(QBrush(fill_c))
                painter.drawRoundedRect(seg_rect, 2, 2)

        # Scrubber Line indicator (e.g. 45% mark)
        scrub_x = left_label_w + (0.45 * track_area_w)
        painter.setPen(QPen(QColor("#58A6FF"), 2, Qt.PenStyle.SolidLine))
        painter.drawLine(int(scrub_x), 24, int(scrub_x), height)
