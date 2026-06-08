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


class TipByWirePage(QWidget):
    """
    Page 9 — TIP BY WIRE Product Page.

    Electronic tipping control system with precise wire-based
    positioning and automated tipping sequences.

    Layout:
      ┌─────────────────────────────────────────────────────────────┐
      │ [TIP BY WIRE]  pill                   ← Back to Home     │
      │ ───────────────────────────────────────────────────────────│
      │                                                              │
      │  ┌─ SEQUENCE STATUS ──────────────────────────────────────┐ │
      │  │  Step 3 of 5    Status: IN PROGRESS                   │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ TIP SEQUENCE ─────────────────────────────────────────┐ │
      │  │  [1] ✓ Init    [2] ✓ Lift    [3] ● Tilt    [4] ○ Lower │ │
      │  │  [5] ○ Complete                                        │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ WIRE POSITION ─────────────────────────────────────────┐ │
      │  │                                                        │ │
      │  │   A: ██████████████░░░░░░░░░░░  12.5m                 │ │
      │  │   B: ████████████████████░░░░░  14.2m                 │ │
      │  │   C: ████████████░░░░░░░░░░░░  10.8m                 │ │
      │  │                                                        │ │
      │  │   Sync: 98.5%    Max Diff: 0.15m                      │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ CONTROLS ──────────────────────────────────────────────┐ │
      │  │  [A+] [A-]   [B+] [B-]   [C+] [C-]   [SYNC]          │ │
      │  │                                                        │ │
      │  │  [START SEQUENCE]   [PAUSE]   [ABORT]                │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      │  ┌─ TELEMETRY ─────────────────────────────────────────────┐ │
      │  │  Load: 12.5t    Speed: 2.1°/s    Temp: 68°C          │ │
      │  └─────────────────────────────────────────────────────────┘ │
      │                                                              │
      └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        self._accent = t.GREEN_TIP_BY_WIRE   # Green for TIP BY WIRE

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)

        # ── Header: Title pill + Back button ──────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        title_pill = PageTitleBar("TIP BY WIRE", show_separator=False)
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

        # ── Sequence Status Card ──────────────────────────────────────
        status_card, status_layout = Card.create("SEQUENCE STATUS")

        seq_status_row = QHBoxLayout()
        seq_status_row.setSpacing(16)

        # Step indicator
        step_widget = QWidget()
        step_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {self._accent};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        step_layout = QHBoxLayout(step_widget)
        step_layout.setContentsMargins(0, 0, 0, 0)
        step_layout.setSpacing(6)
        step_icon = IconWidget(fa="fa6s.list-ol", fallback="≡", colour=self._accent, size=10)
        step_lbl = QLabel("Step 3 of 5")
        step_lbl.setStyleSheet(f"color: {self._accent}; font-size: 11px; background: transparent;")
        step_layout.addWidget(step_icon)
        step_layout.addWidget(step_lbl)
        seq_status_row.addWidget(step_widget)

        # Progress status
        progress_widget = QWidget()
        progress_widget.setStyleSheet(f"""
            QWidget {{
                background: {t.BG_CARD_DEEP};
                border: 1px solid {t.BORDER_MID};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(6)
        progress_icon = IconWidget(fa="fa6s.spinner", fallback="◎", colour=t.TEXT_MID, size=10)
        progress_lbl = QLabel("Status: IN PROGRESS")
        progress_lbl.setStyleSheet(f"color: {t.TEXT_MID}; font-size: 11px; background: transparent;")
        progress_layout.addWidget(progress_icon)
        progress_layout.addWidget(progress_lbl)
        seq_status_row.addWidget(progress_widget)

        seq_status_row.addStretch()
        status_layout.addLayout(seq_status_row)

        # ── Tip Sequence Card ──────────────────────────────────────────
        sequence_card, sequence_layout = Card.create("TIP SEQUENCE")

        steps = [
            ("1", "Init", True),
            ("2", "Lift", True),
            ("3", "Tilt", True),
            ("4", "Lower", False),
            ("5", "Complete", False),
        ]

        step_row = QHBoxLayout()
        step_row.setSpacing(8)

        for i, (num, name, done) in enumerate(steps):
            step_widget = QWidget()
            step_widget.setFixedWidth(90)
            colour = self._accent if done else t.TEXT_DIM
            border_col = self._accent if done else t.BORDER_SOFT

            step_widget.setStyleSheet(f"""
                QWidget {{
                    background: {t.BG_CARD_DEEP};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    padding: 6px 8px;
                }}
            """)

            step_layout_inner = QHBoxLayout(step_widget)
            step_layout_inner.setContentsMargins(4, 4, 4, 4)
            step_layout_inner.setSpacing(6)

            # Step number circle
            num_widget = QLabel(num)
            num_widget.setFixedSize(20, 20)
            num_widget.setAlignment(Qt.AlignCenter)
            num_widget.setStyleSheet(f"""
                QLabel {{
                    background: {colour if done else t.BG_SURFACE};
                    color: {t.TEXT_ON_GREEN if done else t.TEXT_DIM};
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: bold;
                }}
            """)
            step_layout_inner.addWidget(num_widget)

            # Checkmark or pending icon
            if done:
                icon = IconWidget(fa="fa6s.check", fallback="✓", colour=colour, size=8)
            else:
                icon = IconWidget(fa="fa6s.circle", fallback="○", colour=colour, size=8)
            step_layout_inner.addWidget(icon)

            # Step name
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"color: {colour}; font-size: 9px; background: transparent;")
            step_layout_inner.addWidget(name_lbl)

            step_row.addWidget(step_widget)

            if i < len(steps) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet(f"color: {t.TEXT_FAINT}; font-size: 12px; background: transparent;")
                step_row.addWidget(arrow)

        step_row.addStretch()
        sequence_layout.addLayout(step_row)

        # ── Wire Position Card ──────────────────────────────────────────
        wire_card, wire_layout = Card.create("WIRE POSITION")

        wires = [
            ("A", 125, 200),
            ("B", 142, 200),
            ("C", 108, 200),
        ]

        for wire_id, current, max_val in wires:
            wire_row = QHBoxLayout()
            wire_row.setSpacing(12)

            wire_lbl = QLabel(f"Wire {wire_id}:")
            wire_lbl.setStyleSheet(f"color: {t.TEXT_LABEL}; font-size: 11px; background: transparent;")
            wire_lbl.setFixedWidth(60)

            bar_bg = QWidget()
            bar_bg.setFixedHeight(14)
            bar_bg.setStyleSheet(f"""
                QWidget {{
                    background: {t.BG_INPUT};
                    border-radius: 7px;
                }}
            """)
            bar_layout = QHBoxLayout(bar_bg)
            bar_layout.setContentsMargins(3, 3, 3, 3)

            fill_pct = int((current / max_val) * 100)
            fill = QWidget()
            fill.setFixedWidth(fill_pct)
            fill.setStyleSheet(f"""
                QWidget {{
                    background: {self._accent};
                    border-radius: 5px;
                }}
            """)
            bar_layout.addWidget(fill)
            bar_layout.addStretch()

            wire_val = QLabel(f"{current / 10:.1f}m")
            wire_val.setStyleSheet(f"color: {self._accent}; font-size: 11px; font-weight: bold; font-family: {t.FONT_MONO}; background: transparent;")
            wire_val.setFixedWidth(50)

            wire_row.addWidget(wire_lbl)
            wire_row.addWidget(bar_bg, 1)
            wire_row.addWidget(wire_val)

            wire_layout.addLayout(wire_row)

        # Sync info
        sync_row = QHBoxLayout()
        sync_row.setSpacing(16)

        sync_lbl = QLabel("Sync:")
        sync_lbl.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;")
        sync_val = QLabel("98.5%")
        sync_val.setStyleSheet(f"color: {t.GREEN}; font-size: 10px; font-weight: bold; background: transparent;")

        diff_lbl = QLabel("Max Diff:")
        diff_lbl.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;")
        diff_val = QLabel("0.15m")
        diff_val.setStyleSheet(f"color: {t.TEXT_MID}; font-size: 10px; font-family: {t.FONT_MONO}; background: transparent;")

        sync_row.addWidget(sync_lbl)
        sync_row.addWidget(sync_val)
        sync_row.addSpacing(24)
        sync_row.addWidget(diff_lbl)
        sync_row.addWidget(diff_val)
        sync_row.addStretch()

        wire_layout.addSpacing(8)
        wire_layout.addLayout(sync_row)

        # ── Controls Card ─────────────────────────────────────────────
        ctrl_card, ctrl_layout = Card.create("CONTROLS")

        # Wire adjustment buttons
        wire_btn_row = QHBoxLayout()
        wire_btn_row.setSpacing(8)

        for wire_id in ["A", "B", "C"]:
            wire_grp = QHBoxLayout()
            wire_grp.setSpacing(4)

            plus_btn = ActionButton(f"{wire_id}+")
            plus_btn.setFixedWidth(40)
            minus_btn = ActionButton(f"{wire_id}-")
            minus_btn.setFixedWidth(40)

            wire_grp.addWidget(plus_btn)
            wire_grp.addWidget(minus_btn)
            wire_btn_row.addLayout(wire_grp)

        sync_btn = SuccessButton("SYNC")
        sync_btn.setFixedWidth(60)

        wire_btn_row.addStretch()
        wire_btn_row.addWidget(sync_btn)
        ctrl_layout.addLayout(wire_btn_row)

        ctrl_layout.addSpacing(12)

        # Main control buttons
        main_btn_row = QHBoxLayout()
        main_btn_row.setSpacing(12)

        start_seq_btn = SuccessButton("▶  START SEQUENCE")
        start_seq_btn.setFixedWidth(150)
        pause_btn = ActionButton("⏸  PAUSE")
        pause_btn.setFixedWidth(80)
        abort_btn = DangerButton("ABORT")
        abort_btn.setFixedWidth(80)

        main_btn_row.addWidget(start_seq_btn)
        main_btn_row.addWidget(pause_btn)
        main_btn_row.addWidget(abort_btn)
        main_btn_row.addStretch()

        ctrl_layout.addLayout(main_btn_row)

        # ── Telemetry Card ─────────────────────────────────────────────
        tel_card, tel_layout = Card.create("TELEMETRY")

        tel_row = QHBoxLayout()
        tel_row.setSpacing(16)

        telemetry_items = [
            ("Load", "12.5t", "fa6s.weight-scale"),
            ("Speed", "2.1°/s", "fa6s.gauge-simple"),
            ("Temp", "68°C", "fa6s.thermometer-half"),
        ]

        for label, value, fa_icon in telemetry_items:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(2)

            title_lbl = QLabel(label.upper())
            title_lbl.setStyleSheet(f"color: {t.TEXT_DIM}; font-size: 8px; letter-spacing: 1px; background: transparent;")

            value_lbl = QLabel(value)
            value_lbl.setStyleSheet(f"color: {t.TEXT_BRIGHT}; font-size: 13px; font-weight: bold; font-family: {t.FONT_MONO}; background: transparent;")

            item_layout.addWidget(title_lbl)
            item_layout.addWidget(value_lbl)

            tel_row.addWidget(item_widget)

        tel_row.addStretch()
        tel_layout.addLayout(tel_row)

        # Add all cards to root
        root.addWidget(status_card)
        root.addWidget(sequence_card)
        root.addWidget(wire_card)
        root.addWidget(ctrl_card)
        root.addWidget(tel_card)
        root.addStretch()

        logger.debug("[TIP BY WIRE] Page built")

    def _go_home(self) -> None:
        """Navigate back to home page."""
        w = self.parent()
        while w is not None:
            if hasattr(w, "_switch_page"):
                w._switch_page(0)
                return
            w = w.parent() if hasattr(w, "parent") else None