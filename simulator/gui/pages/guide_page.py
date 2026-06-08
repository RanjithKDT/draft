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
    ActionButton, SuccessButton, GhostButton,
)


class GuidePage(QWidget):
    """
    Page 7 — GUIDE Product Page.

    Intelligent Digital Tipping System - Guide mode provides real-time
    guidance during truck tipping operations.

    Layout:
      ┌─────────────────────────────────────────────────────────────┐
      │ [GUIDE]  pill                            ← Back to Home   │
      │ ───────────────────────────────────────────────────────────│
      │                                                              │
      │  ┌─ SYSTEM STATUS ───────────────────────────────────────┐ │
      │  │  [●] System Active    Mode: GUIDANCE    IGN: ON        │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ TILT GUIDANCE ───────────────────────────────────────┐ │
      │  │  Lateral:      0.00°  (safe)    Safe range: ±12.5°   │ │
      │  │  Longitudinal:  0.00°  (safe)    Warning: 12.5° - 17°  │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ SAFETY STATUS ───────────────────────────────────────┐ │
      │  │  [✓] Ground Stability: STABLE                         │ │
      │  │  [✓] Payload Level: NOMINAL                           │ │
      │  │  [✓] Tipping Angle: SAFE                              │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ OPERATION CONTROLS ───────────────────────────────────┐ │
      │  │  [START GUIDE]    [PAUSE]    [STOP]                   │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ TIP PROGRESS ─────────────────────────────────────────┐ │
      │  │  ████████████░░░░░░░░░░░░░░░░░░░░░░  45%             │ │
      │  │  Estimated time remaining: 2 min 30 sec               │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        self._accent = t.YELLOW_GUIDE   # Hyva Yellow for GUIDE

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)

        # ── Header: Title pill + Back button ──────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        title_pill = PageTitleBar("GUIDE", show_separator=False)
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

        # ── System Status Card ─────────────────────────────────────────
        status_card, status_layout = Card.create("SYSTEM STATUS")

        status_row = QHBoxLayout()
        status_row.setSpacing(16)

        # Active indicator
        active_widget = QWidget()
        active_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {t.GREEN};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        active_layout = QHBoxLayout(active_widget)
        active_layout.setContentsMargins(0, 0, 0, 0)
        active_layout.setSpacing(6)
        active_icon = IconWidget(fa="fa6s.circle", fallback="●", colour=t.GREEN, size=10)
        active_lbl = QLabel("System Active")
        active_lbl.setStyleSheet(f"color: {t.GREEN}; font-size: 11px; background: transparent;")
        active_layout.addWidget(active_icon)
        active_layout.addWidget(active_lbl)
        status_row.addWidget(active_widget)

        # Mode indicator
        mode_widget = QWidget()
        mode_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {self._accent};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(6)
        mode_icon = IconWidget(fa="fa6s.compass", fallback="◎", colour=self._accent, size=10)
        mode_lbl = QLabel("Mode: GUIDANCE")
        mode_lbl.setStyleSheet(f"color: {self._accent}; font-size: 11px; background: transparent;")
        mode_layout.addWidget(mode_icon)
        mode_layout.addWidget(mode_lbl)
        status_row.addWidget(mode_widget)

        # IGN status
        ign_widget = QWidget()
        ign_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {t.BORDER_MID};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        ign_layout = QHBoxLayout(ign_widget)
        ign_layout.setContentsMargins(0, 0, 0, 0)
        ign_layout.setSpacing(6)
        ign_icon = IconWidget(fa="fa6s.power-off", fallback="⏻", colour=t.GREEN, size=10)
        ign_lbl = QLabel("IGN: ON")
        ign_lbl.setStyleSheet(f"color: {t.TEXT_MID}; font-size: 11px; background: transparent;")
        ign_layout.addWidget(ign_icon)
        ign_layout.addWidget(ign_lbl)
        status_row.addWidget(ign_widget)

        status_row.addStretch()
        status_layout.addLayout(status_row)

        # ── Tilt Guidance Card ──────────────────────────────────────────
        tilt_card, tilt_layout = Card.create("TILT GUIDANCE")

        # Lateral tilt row
        lat_row = QHBoxLayout()
        lat_row.setSpacing(12)

        lat_icon = IconWidget(fa="fa6s.arrows-left-right", fallback="↔", colour=self._accent, size=12)
        lat_lbl = QLabel("Lateral:")
        lat_lbl.setStyleSheet(f"color: {t.TEXT_LABEL}; font-size: 11px; background: transparent;")
        lat_val = QLabel("0.00°")
        lat_val.setStyleSheet(f"color: {t.TEXT_BRIGHT}; font-size: 14px; font-weight: bold; font-family: {t.FONT_MONO}; background: transparent;")
        lat_safe = QLabel("(safe)")
        lat_safe.setStyleSheet(f"color: {t.GREEN}; font-size: 10px; background: transparent;")
        lat_range = QLabel("Safe range: ±12.5°")
        lat_range.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;")
        lat_range.setAlignment(Qt.AlignRight)
        lat_row.addWidget(lat_icon)
        lat_row.addWidget(lat_lbl)
        lat_row.addWidget(lat_val)
        lat_row.addWidget(lat_safe)
        lat_row.addStretch()
        lat_row.addWidget(lat_range)
        tilt_layout.addLayout(lat_row)

        # Longitudinal tilt row
        long_row = QHBoxLayout()
        long_row.setSpacing(12)

        long_icon = IconWidget(fa="fa6s.arrow-up-long", fallback="↑", colour=self._accent, size=12)
        long_lbl = QLabel("Longitudinal:")
        long_lbl.setStyleSheet(f"color: {t.TEXT_LABEL}; font-size: 11px; background: transparent;")
        long_val = QLabel("0.00°")
        long_val.setStyleSheet(f"color: {t.TEXT_BRIGHT}; font-size: 14px; font-weight: bold; font-family: {t.FONT_MONO}; background: transparent;")
        long_safe = QLabel("(safe)")
        long_safe.setStyleSheet(f"color: {t.GREEN}; font-size: 10px; background: transparent;")
        long_range = QLabel("Warning: 12.5° - 17°")
        long_range.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;")
        long_range.setAlignment(Qt.AlignRight)
        long_row.addWidget(long_icon)
        long_row.addWidget(long_lbl)
        long_row.addWidget(long_val)
        long_row.addWidget(long_safe)
        long_row.addStretch()
        long_row.addWidget(long_range)
        tilt_layout.addLayout(long_row)

        # ── Safety Status Card ──────────────────────────────────────────
        safety_card, safety_layout = Card.create("SAFETY STATUS")

        safety_items = [
            ("Ground Stability", "STABLE", t.GREEN, "fa6s.mountain"),
            ("Payload Level", "NOMINAL", t.GREEN, "fa6s.box"),
            ("Tipping Angle", "SAFE", t.GREEN, "fa6s.gauge-simple"),
        ]

        for i, (label, value, colour, fa_icon) in enumerate(safety_items):
            item_row = QHBoxLayout()
            item_row.setSpacing(10)

            icon = IconWidget(fa=fa_icon, fallback="✓", colour=colour, size=11)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {t.TEXT_LABEL}; font-size: 11px; background: transparent;")

            val_lbl = QLabel(value)
            val_lbl.setStyleSheet(f"color: {colour}; font-size: 11px; font-weight: 600; background: transparent;")

            item_row.addWidget(icon)
            item_row.addWidget(lbl)
            item_row.addStretch()
            item_row.addWidget(val_lbl)

            if i < len(safety_items) - 1:
                sep = HSep()
                sep.setFixedHeight(1)
                safety_layout.addLayout(item_row)
                safety_layout.addWidget(sep)
            else:
                safety_layout.addLayout(item_row)

        # ── Operation Controls Card ─────────────────────────────────────
        ctrl_card, ctrl_layout = Card.create("OPERATION CONTROLS")

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)

        start_btn = SuccessButton("▶  START GUIDE")
        start_btn.setFixedWidth(140)
        pause_btn = ActionButton("⏸  PAUSE")
        pause_btn.setFixedWidth(100)
        stop_btn = DangerButton("■  STOP")
        stop_btn.setFixedWidth(100)

        ctrl_row.addWidget(start_btn)
        ctrl_row.addWidget(pause_btn)
        ctrl_row.addWidget(stop_btn)
        ctrl_row.addStretch()

        ctrl_layout.addLayout(ctrl_row)

        # ── Tip Progress Card ────────────────────────────────────────────
        progress_card, progress_layout = Card.create("TIP PROGRESS")

        # Progress bar
        bar_bg = QWidget()
        bar_bg.setFixedHeight(16)
        bar_bg.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_INPUT};
                border-radius: 8px;
            }}
        """)

        bar_layout = QHBoxLayout(bar_bg)
        bar_layout.setContentsMargins(3, 3, 3, 3)

        fill = QWidget()
        fill.setFixedWidth(120)
        fill.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {t.YELLOW_DIM},
                    stop:0.5 {self._accent},
                    stop:1 {self._accent});
                border-radius: 5px;
            }}
        """)
        bar_layout.addWidget(fill)
        bar_layout.addStretch()

        progress_layout.addWidget(bar_bg)

        # Percentage and time
        info_row = QHBoxLayout()
        info_row.setSpacing(16)

        pct_lbl = QLabel("45%")
        pct_lbl.setStyleSheet(f"color: {self._accent}; font-size: 12px; font-weight: bold; background: transparent;")

        time_lbl = QLabel("Estimated time remaining: 2 min 30 sec")
        time_lbl.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;")

        info_row.addWidget(pct_lbl)
        info_row.addStretch()
        info_row.addWidget(time_lbl)
        progress_layout.addLayout(info_row)

        # Add all cards to root
        root.addWidget(status_card)
        root.addWidget(tilt_card)
        root.addWidget(safety_card)
        root.addWidget(ctrl_card)
        root.addWidget(progress_card)
        root.addStretch()

        logger.debug("[GUIDE] Page built")

    def _go_home(self) -> None:
        """Navigate back to home page."""
        w = self.parent()
        while w is not None:
            if hasattr(w, "_switch_page"):
                w._switch_page(0)
                return
            w = w.parent() if hasattr(w, "parent") else None