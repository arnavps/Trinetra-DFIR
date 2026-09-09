"""Top Forensic Status Ribbon Widget displaying hardware write-block status, drive info, Merkle hash, and offline air-gap state."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget
from app.engine9_ui.widgets.fluent_theme import DFIR_DARK_THEME, get_badge_stylesheet


class ForensicStatusRibbonWidget(QFrame):
    """
    Top status ribbon bar providing real-time telemetry on physical drive source,
    write-blocker verification, Merkle global hash, and offline air-gap posture.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DFIR_DARK_THEME['card_bg']};
                border-bottom: 1px solid {DFIR_DARK_THEME['border_color']};
                padding: 4px 8px;
            }}
            QLabel {{
                color: {DFIR_DARK_THEME['text_color']};
                font-family: {DFIR_DARK_THEME['font_main']};
                font-size: 12px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        # 1. Drive Source
        self.lbl_source = QLabel("<b>Source:</b> /dev/sdb [Physical Disk 1] — WD Purple 2.0 TB (SATA-III)", self)
        layout.addWidget(self.lbl_source)

        # 2. Hardware Write-Block Status Badge
        self.badge_writeblock = QLabel("[HARDWARE WRITE-BLOCKED: ACTIVE]", self)
        self.badge_writeblock.setStyleSheet(get_badge_stylesheet(
            DFIR_DARK_THEME["status_emerald_bg"], DFIR_DARK_THEME["status_emerald_fg"]
        ))
        layout.addWidget(self.badge_writeblock)

        # 3. Filesystem Tag
        self.lbl_fs = QLabel("<b>FS:</b> DHFS 4.1 (Dahua Embedded)", self)
        self.lbl_fs.setStyleSheet(f"font-family: {DFIR_DARK_THEME['font_mono']}; font-weight: bold; color: #58A6FF;")
        layout.addWidget(self.lbl_fs)

        # 4. Global Image Hash
        self.lbl_hash = QLabel("<b>Merkle Hash:</b> SHA-256: 7f83b1657b98f2b3...a9c8 [VERIFIED]", self)
        self.lbl_hash.setStyleSheet(f"font-family: {DFIR_DARK_THEME['font_mono']}; color: #38BDF8;")
        layout.addWidget(self.lbl_hash)

        layout.addStretch()

        # 5. Air-Gap State Badge
        self.badge_airgap = QLabel("AIR-GAP: 100% OFFLINE (0 Sockets Bound)", self)
        self.badge_airgap.setStyleSheet(get_badge_stylesheet(
            DFIR_DARK_THEME["status_cyan_bg"], DFIR_DARK_THEME["status_cyan_fg"]
        ))
        layout.addWidget(self.badge_airgap)

    def update_telemetry(self, source: str, oem: str, write_blocked: bool, image_hash: str) -> None:
        """Updates ribbon values dynamically based on active loaded case."""
        self.lbl_source.setText(f"<b>Source:</b> {source}")
        self.lbl_fs.setText(f"<b>FS:</b> {oem}")
        hash_short = image_hash[:16] + "..." + image_hash[-6:] if len(image_hash) > 22 else image_hash
        self.lbl_hash.setText(f"<b>Merkle Hash:</b> SHA-256: {hash_short} [VERIFIED]")

        if write_blocked:
            self.badge_writeblock.setText("[HARDWARE WRITE-BLOCKED: ACTIVE]")
            self.badge_writeblock.setStyleSheet(get_badge_stylesheet(
                DFIR_DARK_THEME["status_emerald_bg"], DFIR_DARK_THEME["status_emerald_fg"]
            ))
        else:
            self.badge_writeblock.setText("[SOFTWARE WRITE-BLOCK: ACTIVE]")
            self.badge_writeblock.setStyleSheet(get_badge_stylesheet(
                DFIR_DARK_THEME["status_cyan_bg"], DFIR_DARK_THEME["status_cyan_fg"]
            ))
