"""Raw sector/hex viewer for investigator verification."""

import os
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget
from app.engine1_acquisition.image_reader import ImageReader


class DiskHexView(QWidget):
    """Raw sector and hex dump viewer for forensic inspection."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Offset (bytes):", self))
        self.offset_input = QLineEdit("0", self)
        top_bar.addWidget(self.offset_input)

        self.btn_load = QPushButton("Inspect Hex", self)
        self.btn_load.clicked.connect(self._inspect_offset)
        top_bar.addWidget(self.btn_load)

        self.layout.addLayout(top_bar)

        self.hex_text = QTextEdit(self)
        self.hex_text.setReadOnly(True)
        self.hex_text.setStyleSheet("font-family: Consolas, monospace; font-size: 13px;")
        self.layout.addWidget(self.hex_text)

        self.current_image_path = None

    def set_image_path(self, image_path: str) -> None:
        self.current_image_path = image_path
        self._inspect_offset()

    def _inspect_offset(self) -> None:
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            self.hex_text.setText("No valid image file loaded.")
            return

        try:
            offset = int(self.offset_input.text(), 0)
        except ValueError:
            offset = 0

        try:
            with ImageReader(self.current_image_path) as reader:
                reader.seek(offset)
                data = reader.read(512)

            lines = []
            for i in range(0, len(data), 16):
                chunk = data[i : i + 16]
                hex_str = " ".join(f"{b:02X}" for b in chunk)
                ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                lines.append(f"{offset + i:08X}  {hex_str:<48}  |{ascii_str}|")

            self.hex_text.setText("\n".join(lines))
        except Exception as e:
            self.hex_text.setText(f"Error inspecting hex at offset {offset}: {e}")
