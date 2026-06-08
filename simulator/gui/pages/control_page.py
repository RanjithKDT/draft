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


class ControlPage(QWidget):
    """
    Page 8 — CONTROL Product Page.

    Direct control interface for truck tipping operations.
    Provides real-time control of hydraulic systems and tipping mechanism.

    Layout:
      ┌─────────────────────────────────────────────────────────────┐
      │ [CONTROL]  pill                        ← Back to Home     │
      │ ───────────────────────────────────────────────────────────│
      │                                                              │
      │  ┌─ HYDRAULIC STATUS ──────────────────────────────────────┐ │
      │  │  [●] Pump: ON     Pressure: 250 bar    Flow: 40 L/min  │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ TIP CONTROL ──────────────────────────────────────────┐ │
      │  │                                                        │ │
      │  │    ┌─────────────────────────────────────────┐          │ │
      │  │    │                                         │          │ │
      │  │    │         [RAISE]      [LOWER]          │          │ │
      │  │    │                                         │          │ │
      │  │    │         [◄ LIFT ►]                      │          │ │
      │  │    │                                         │          │ │
      │  │    └─────────────────────────────────────────┘          │ │
      │  │                                                        │ │
      │  │    Position: ████████░░░░░░░░░░░░░░░  50%           │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ EMERGENCY STOP ───────────────────────────────────────┐ │
      │  │                                                         │ │
      │  │              [■  EMERGENCY STOP  ■]                    │ │
      │  │                                                         │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ SYSTEM PARAMETERS ────────────────────────────────────┐ │
      │  │  Max Pressure: 350 bar    Max Angle: 45°    Rate: 5°/s │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        self._accent = t.CYAN_CONTROL   # Cyan for CONTROL

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)

        # ── Header: Title pill + Back button ──────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        title_pill = PageTitleBar("CONTROL", show_separator=False)
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

        # ── Hydraulic Status Card ──────────────────────────────────────
        status_card, status_layout = Card.create("HYDRAULIC STATUS")

        status_row = QHBoxLayout()
        status_row.setSpacing(16)

        # Pump status
        pump_widget = QWidget()
        pump_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {t.GREEN};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        pump_layout = QHBoxLayout(pump_widget)
        pump_layout.setContentsMargins(0, 0, 0, 0)
        pump_layout.setSpacing(6)
        pump_icon = IconWidget(fa="fa6s.circle", fallback="●", colour=t.GREEN, size=10)
        pump_lbl = QLabel("Pump: ON")
        pump_lbl.setStyleSheet(f"color: {t.GREEN}; font-size: 11px; background: transparent;")
        pump_layout.addWidget(pump_icon)
        pump_layout.addWidget(pump_lbl)
        status_row.addWidget(pump_widget)

        # Pressure
        pressure_widget = QWidget()
        pressure_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {self._accent};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        pressure_layout = QHBoxLayout(pressure_widget)
        pressure_layout.setContentsMargins(0, 0, 0, 0)
        pressure_layout.setSpacing(6)
        pressure_icon = IconWidget(fa="fa6s.gauge-high", fallback="◉", colour=self._accent, size=10)
        pressure_lbl = QLabel("Pressure: 250 bar")
        pressure_lbl.setStyleSheet(f"color: {self._accent}; font-size: 11px; background: transparent;")
        pressure_layout.addWidget(pressure_icon)
        pressure_layout.addWidget(pressure_lbl)
        status_row.addWidget(pressure_widget)

        # Flow rate
        flow_widget = QWidget()
        flow_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {t.BORDER_MID};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        flow_layout = QHBoxLayout(flow_widget)
        flow_layout.setContentsMargins(0, 0, 0, 0)
        flow_layout.setSpacing(6)
        flow_icon = IconWidget(fa="fa6s.droplet", fallback="~", colour=t.TEXT_MID, size=10)
        flow_lbl = QLabel("Flow: 40 L/min")
        flow_lbl.setStyleSheet(f"color: {t.TEXT_MID}; font-size: 11px; background: transparent;")
        flow_layout.addWidget(flow_icon)
        flow_layout.addWidget(flow_lbl)
        status_row.addWidget(flow_widget)

        status_row.addStretch()
        status_layout.addLayout(status_row)

        # ── Tip Control Card ──────────────────────────────────────────
        ctrl_card, ctrl_layout = Card.create("TIP CONTROL")

        # Control buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        raise_btn = ActionButton("▲  RAISE")
        raise_btn.setFixedWidth(100)
        lower_btn = ActionButton("▼  LOWER")
        lower_btn.setFixedWidth(100)

        btn_row.addStretch()
        btn_row.addWidget(raise_btn)
        btn_row.addWidget(lower_btn)
        btn_row.addStretch()

        ctrl_layout.addLayout(btn_row)

        # Lift control row
        lift_row = QHBoxLayout()
        lift_row.setSpacing(16)

        lift_btn = SuccessButton("◄  LIFT  ►")
        lift_btn.setFixedWidth(160)

        lift_row.addStretch()
        lift_row.addWidget(lift_btn)
        lift_row.addStretch()

        ctrl_layout.addLayout(lift_row)

        # Position indicator
        pos_label = QLabel("Position:")
        pos_label.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;")

        pos_bar_bg = QWidget()
        pos_bar_bg.setFixedHeight(12)
        pos_bar_bg.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_INPUT};
                border-radius: 6px;
            }}
        """)

        pos_bar_layout = QHBoxLayout(pos_bar_bg)
        pos_bar_layout.setContentsMargins(2, 2, 2, 2)

        pos_fill = QWidget()
        pos_fill.setFixedWidth(100)
        pos_fill.setStyleSheet(f"""
            QWidget {{
                background: {self._accent};
                border-radius: 4px;
            }}
        """)
        pos_bar_layout.addWidget(pos_fill)
        pos_bar_layout.addStretch()

        pos_pct = QLabel("50%")
        pos_pct.setStyleSheet(f"color: {self._accent}; font-size: 11px; font-weight: bold; background: transparent;")

        pos_row = QHBoxLayout()
        pos_row.setSpacing(8)
        pos_row.addWidget(pos_label)
        pos_row.addWidget(pos_bar_bg, 1)
        pos_row.addWidget(pos_pct)

        ctrl_layout.addLayout(pos_row)

        # ── Emergency Stop Card ────────────────────────────────────────
        estop_card, estop_layout = Card.create("EMERGENCY STOP")

        estop_layout.addSpacing(16)

        estop_btn = DangerButton("■  EMERGENCY STOP  ■")
        estop_btn.setFixedWidth(280)
        estop_btn.setFixedHeight(48)
        estop_btn.setStyleSheet(f"""
            QPushButton {{
                background: {t.RED};
                color: {t.TEXT_WHITE};
                border: 2px solid #EF4444;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {t.RED_HOVER};
                border-color: #F87171;
            }}
            QPushButton:pressed {{
                background: {t.RED_PRESSED};
            }}
        """)

        estop_layout.addWidget(estop_btn, 0, Qt.AlignCenter)
        estop_layout.addSpacing(16)

        # ── System Parameters Card ─────────────────────────────────────
        params_card, params_layout = Card.create("SYSTEM PARAMETERS")

        params_row = QHBoxLayout()
        params_row.setSpacing(24)

        # Max Pressure
        max_press_widget = QWidget()
        max_press_layout = QVBoxLayout(max_press_widget)
        max_press_layout.setContentsMargins(0, 0, 0, 0)
        max_press_layout.setSpacing(2)
        max_press_title = QLabel("MAX PRESSURE")
        max_press_title.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 8px; letter-spacing: 1px; background: transparent;")
        max_press_val = QLabel("350 bar")
        max_press_val.setStyleSheet(f"color: {t.TEXT_BRIGHT}; font-size: 13px; font-weight: bold; background: transparent;")
        max_press_layout.addWidget(max_press_title)
        max_press_layout.addWidget(max_press_val)
        params_row.addWidget(max_press_widget)

        # Max Angle
        max_angle_widget = QWidget()
        max_angle_layout = QVBoxLayout(max_angle_widget)
        max_angle_layout.setContentsMargins(0, 0, 0, 0)
        max_angle_layout.setSpacing(2)
        max_angle_title = QLabel("MAX ANGLE")
        max_angle_title.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 8px; letter-spacing: 1px; background: transparent;")
        max_angle_val = QLabel("45°")
        max_angle_val.setStyleSheet(f"color: {t.TEXT_BRIGHT}; font-size: 13px; font-weight: bold; background: transparent;")
        max_angle_layout.addWidget(max_angle_title)
        max_angle_layout.addWidget(max_angle_val)
        params_row.addWidget(max_angle_widget)

        # Rate
        rate_widget = QWidget()
        rate_layout = QVBoxLayout(rate_widget)
        rate_layout.setContentsMargins(0, 0, 0, 0)
        rate_layout.setSpacing(2)
        rate_title = QLabel("RATE")
        rate_title.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 8px; letter-spacing: 1px; background: transparent;")
        rate_val = QLabel("5°/s")
        rate_val.setStyleSheet(f"color: {t.TEXT_BRIGHT}; font-size: 13px; font-weight: bold; background: transparent;")
        rate_layout.addWidget(rate_title)
        rate_layout.addWidget(rate_val)
        params_row.addWidget(rate_widget)

        params_row.addStretch()
        params_layout.addLayout(params_row)

        # Add all cards to root
        root.addWidget(status_card)
        root.addWidget(ctrl_card)
        root.addWidget(estop_card)
        root.addWidget(params_card)
        root.addStretch()

        logger.debug("[CONTROL] Page built")

    def _go_home(self) -> None:
        """Navigate back to home page."""
        w = self.parent()
        while w is not None:
            if hasattr(w, "_switch_page"):
                w._switch_page(0)
                return
            w = w.parent() if hasattr(w, "parent") else None