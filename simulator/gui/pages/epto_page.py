from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton,
)
from PySide6.QtCore import Qt
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.icons import IconWidget, Fa, Symbol
from simulator.gui.components import (
    PageTitleBar, RedSepH, RedSepV, HSep,
    Card, SubCard, InfoRow, BackButton,
    SectionLabel, ValueLabel, StatusLabel,
    ActionButton, SuccessButton, DangerButton, GhostButton,
)


class EptoPage(QWidget):
    """
    Page 10 — EPTO Product Page.

    External PTO (Power Take-Off) control interface for managing
    external equipment powered by the truck's PTO system.

    Layout:
      ┌─────────────────────────────────────────────────────────────┐
      │ [EPTO]  pill                           ← Back to Home     │
      │ ───────────────────────────────────────────────────────────│
      │                                                              │
      │  ┌─ PTO STATUS ────────────────────────────────────────────┐ │
      │  │  [●] PTO: ENGAGED    RPM: 1000    Power: 45 kW        │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ PTO ENGAGEMENT ───────────────────────────────────────┐ │
      │  │                                                        │ │
      │  │      ┌───────────────────────────────────────┐         │ │
      │  │      │                                       │         │ │
      │  │      │           [●] ENGAGE PTO             │         │ │
      │  │      │           [○] DISENGAGE PTO           │         │ │
      │  │      │                                       │         │ │
      │  │      └───────────────────────────────────────┘         │ │
      │  │                                                        │ │
      │  │      Engagement: ████████████████░░░░░  75%          │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ RPM CONTROL ─────────────────────────────────────────┐ │
      │  │                                                        │ │
      │  │   Target RPM: [1000 ▲] [▼]                            │ │
      │  │                                                        │ │
      │  │   ┌─────────────────────────────────────────┐          │ │
      │  │   │  500   750   1000   1250   1500   2000  │          │ │
      │  │   └─────────────────────────────────────────┘          │ │
      │  │                                                        │ │
      │  │   Current: 1000 RPM    Status: STABLE                 │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ OUTPUT CONNECTIONS ───────────────────────────────────┐ │
      │  │  [✓] Output 1: Active (Hydraulic)                      │ │
      │  │  [✓] Output 2: Active (Electrical)                    │ │
      │  │  [○] Output 3: Inactive                               │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ DIAGNOSTICS ──────────────────────────────────────────┐ │
      │  │  Temperature: 72°C    Oil Pressure: 3.5 bar          │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        self._accent = t.ORANGE_EPTO   # Orange for EPTO

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)

        # ── Header: Title pill + Back button ──────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        title_pill = PageTitleBar("EPTO", show_separator=False)
        title_pill.setStyleSheet(f"""
            QWidget {{ background: {self._accent}; }}
        """)
        header_row.addWidget(title_pill, stretch=1)

        back_btn = GhostButton(f"{Symbol.BACK}  Home")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {t.TEXT_DIM};
                border: 1px solid {t.BORDER_STRONG};
                border-radius: 13px;
                font-size: 10px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                color: {t.RED};
                border-color: {t.RED};
                background: #1A0000;
            }}
        """)
        back_btn.clicked.connect(self._go_home)
        header_row.addWidget(back_btn, stretch=0, alignment=Qt.AlignVCenter)

        root.addLayout(header_row)
        root.addWidget(HSep())

        # ── PTO Status Card ───────────────────────────────────────────
        status_card, status_layout = Card.create("PTO STATUS")

        status_row = QHBoxLayout()
        status_row.setSpacing(16)

        # PTO status
        pto_widget = QWidget()
        pto_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {t.GREEN};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        pto_layout = QHBoxLayout(pto_widget)
        pto_layout.setContentsMargins(0, 0, 0, 0)
        pto_layout.setSpacing(6)
        pto_icon = IconWidget(fa="fa6s.circle", fallback="●", colour=t.GREEN, size=10)
        pto_lbl = QLabel("PTO: ENGAGED")
        pto_lbl.setStyleSheet(f"color: {t.GREEN}; font-size: 11px; background: transparent;")
        pto_layout.addWidget(pto_icon)
        pto_layout.addWidget(pto_lbl)
        status_row.addWidget(pto_widget)

        # RPM
        rpm_widget = QWidget()
        rpm_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {self._accent};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        rpm_layout = QHBoxLayout(rpm_widget)
        rpm_layout.setContentsMargins(0, 0, 0, 0)
        rpm_layout.setSpacing(6)
        rpm_icon = IconWidget(fa="fa6s.rotate", fallback="↻", colour=self._accent, size=10)
        rpm_lbl = QLabel("RPM: 1000")
        rpm_lbl.setStyleSheet(f"color: {self._accent}; font-size: 11px; background: transparent;")
        rpm_layout.addWidget(rpm_icon)
        rpm_layout.addWidget(rpm_lbl)
        status_row.addWidget(rpm_widget)

        # Power
        power_widget = QWidget()
        power_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {t.BORDER_MID};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        power_layout = QHBoxLayout(power_widget)
        power_layout.setContentsMargins(0, 0, 0, 0)
        power_layout.setSpacing(6)
        power_icon = IconWidget(fa="fa6s.bolt", fallback="⚡", colour=t.TEXT_MID, size=10)
        power_lbl = QLabel("Power: 45 kW")
        power_lbl.setStyleSheet(f"color: {t.TEXT_MID}; font-size: 11px; background: transparent;")
        power_layout.addWidget(power_icon)
        power_layout.addWidget(power_lbl)
        status_row.addWidget(power_widget)

        status_row.addStretch()
        status_layout.addLayout(status_row)

        # ── PTO Engagement Card ────────────────────────────────────────
        engage_card, engage_layout = Card.create("PTO ENGAGEMENT")

        engage_layout.addSpacing(12)

        # Engagement buttons
        engage_btn_widget = QWidget()
        engage_btn_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {self._accent};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        engage_btn_layout = QVBoxLayout(engage_btn_widget)
        engage_btn_layout.setSpacing(10)

        engage_btn = SuccessButton("●  ENGAGE PTO")
        engage_btn.setFixedWidth(200)
        disengage_btn = ActionButton("○  DISENGAGE PTO")
        disengage_btn.setFixedWidth(200)

        engage_btn_layout.addWidget(engage_btn, 0, Qt.AlignCenter)
        engage_btn_layout.addWidget(disengage_btn, 0, Qt.AlignCenter)

        engage_layout.addWidget(engage_btn_widget, 0, Qt.AlignCenter)

        engage_layout.addSpacing(12)

        # Engagement progress bar
        engage_label = QLabel("Engagement:")
        engage_label.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;")

        engage_bar_bg = QWidget()
        engage_bar_bg.setFixedHeight(14)
        engage_bar_bg.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_INPUT};
                border-radius: 7px;
            }}
        """)
        engage_bar_layout = QHBoxLayout(engage_bar_bg)
        engage_bar_layout.setContentsMargins(3, 3, 3, 3)

        engage_fill = QWidget()
        engage_fill.setFixedWidth(150)
        engage_fill.setStyleSheet(f"""
            QWidget {{
                background: {self._accent};
                border-radius: 5px;
            }}
        """)
        engage_bar_layout.addWidget(engage_fill)
        engage_bar_layout.addStretch()

        engage_pct = QLabel("75%")
        engage_pct.setStyleSheet(f"color: {self._accent}; font-size: 11px; font-weight: bold; background: transparent;")

        engage_progress_row = QHBoxLayout()
        engage_progress_row.setSpacing(8)
        engage_progress_row.addWidget(engage_label)
        engage_progress_row.addWidget(engage_bar_bg, 1)
        engage_progress_row.addWidget(engage_pct)

        engage_layout.addLayout(engage_progress_row)

        # ── RPM Control Card ───────────────────────────────────────────
        rpm_card, rpm_layout = Card.create("RPM CONTROL")

        # Target RPM controls
        rpm_control_row = QHBoxLayout()
        rpm_control_row.setSpacing(12)

        target_lbl = QLabel("Target RPM:")
        target_lbl.setStyleSheet(f"color: {t.TEXT_LABEL}; font-size: 11px; background: transparent;")

        target_val = QLabel("1000")
        target_val.setStyleSheet(f"color: {t.TEXT_BRIGHT}; font-size: 18px; font-weight: bold; font-family: {t.FONT_MONO}; background: transparent;")

        up_btn = ActionButton("▲")
        up_btn.setFixedWidth(36)
        down_btn = ActionButton("▼")
        down_btn.setFixedWidth(36)

        rpm_control_row.addWidget(target_lbl)
        rpm_control_row.addWidget(target_val)
        rpm_control_row.addWidget(up_btn)
        rpm_control_row.addWidget(down_btn)
        rpm_control_row.addStretch()

        rpm_layout.addLayout(rpm_control_row)

        rpm_layout.addSpacing(8)

        # Preset RPM buttons
        preset_widget = QWidget()
        preset_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        preset_layout = QHBoxLayout(preset_widget)
        preset_layout.setSpacing(6)

        presets = ["500", "750", "1000", "1250", "1500", "2000"]
        for preset in presets:
            preset_btn = PillButton(preset)
            preset_btn.setFixedWidth(60)
            preset_layout.addWidget(preset_btn)

        rpm_layout.addWidget(preset_widget)

        rpm_layout.addSpacing(8)

        # Current RPM status
        current_row = QHBoxLayout()
        current_row.setSpacing(16)

        current_lbl = QLabel("Current:")
        current_lbl.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;")

        current_val = QLabel("1000 RPM")
        current_val.setStyleSheet(f"color: {self._accent}; font-size: 12px; font-weight: bold; font-family: {t.FONT_MONO}; background: transparent;")

        status_lbl = QLabel("Status:")
        status_lbl.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;")

        status_val = QLabel("STABLE")
        status_val.setStyleSheet(f"color: {t.GREEN}; font-size: 10px; font-weight: 600; background: transparent;")

        current_row.addWidget(current_lbl)
        current_row.addWidget(current_val)
        current_row.addSpacing(24)
        current_row.addWidget(status_lbl)
        current_row.addWidget(status_val)
        current_row.addStretch()

        rpm_layout.addLayout(current_row)

        # ── Output Connections Card ────────────────────────────────────
        conn_card, conn_layout = Card.create("OUTPUT CONNECTIONS")

        outputs = [
            ("Output 1", "Active (Hydraulic)", True),
            ("Output 2", "Active (Electrical)", True),
            ("Output 3", "Inactive", False),
        ]

        for i, (name, desc, active) in enumerate(outputs):
            conn_row = QHBoxLayout()
            conn_row.setSpacing(10)

            colour = t.GREEN if active else t.TEXT_DIM
            icon = IconWidget(fa="fa6s.check-circle" if active else "fa6s.circle",
                           fallback="✓" if active else "○",
                           colour=colour, size=12)

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"color: {t.TEXT_LABEL}; font-size: 11px; background: transparent;")

            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {colour}; font-size: 11px; background: transparent;")

            conn_row.addWidget(icon)
            conn_row.addWidget(name_lbl)
            conn_row.addStretch()
            conn_row.addWidget(desc_lbl)

            conn_layout.addLayout(conn_row)

            if i < len(outputs) - 1:
                sep = HSep()
                sep.setFixedHeight(1)
                conn_layout.addWidget(sep)

        # ── Diagnostics Card ────────────────────────────────────────────
        diag_card, diag_layout = Card.create("DIAGNOSTICS")

        diag_row = QHBoxLayout()
        diag_row.setSpacing(24)

        diag_items = [
            ("TEMPERATURE", "72°C", "fa6s.thermometer-half"),
            ("OIL PRESSURE", "3.5 bar", "fa6s.droplet"),
        ]

        for label, value, fa_icon in diag_items:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(2)

            title_lbl = QLabel(label)
            title_lbl.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 8px; letter-spacing: 1px; background: transparent;")

            value_row = QHBoxLayout()
            value_row.setSpacing(4)

            icon = IconWidget(fa=fa_icon, fallback="◉", colour=self._accent, size=10)
            value_lbl = QLabel(value)
            value_lbl.setStyleSheet(f"color: {t.TEXT_BRIGHT}; font-size: 13px; font-weight: bold; font-family: {t.FONT_MONO}; background: transparent;")

            value_row.addWidget(icon)
            value_row.addWidget(value_lbl)

            item_layout.addWidget(title_lbl)
            item_layout.addLayout(value_row)

            diag_row.addWidget(item_widget)

        diag_row.addStretch()
        diag_layout.addLayout(diag_row)

        # Add all cards to root
        root.addWidget(status_card)
        root.addWidget(engage_card)
        root.addWidget(rpm_card)
        root.addWidget(conn_card)
        root.addWidget(diag_card)
        root.addStretch()

        logger.debug("[EPTO] Page built")

    def _go_home(self) -> None:
        """Navigate back to home page."""
        w = self.parent()
        while w is not None:
            if hasattr(w, "_switch_page"):
                w._switch_page(0)
                return
            w = w.parent() if hasattr(w, "parent") else None


class PillButton(QPushButton):
    """Small pill-shaped button for preset selections."""

    def __init__(self, text: str, parent: "QWidget | None" = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {t.BG_CARD_DEEP};
                color: {t.TEXT_LABEL};
                border: 1px solid {t.BORDER_SOFT};
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background: {t.BG_CARD_HOVER};
                border-color: {t.ORANGE_EPTO};
                color: {t.ORANGE_EPTO};
            }}
        """)