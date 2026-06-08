from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QLineEdit, QSlider,
)
from PySide6.QtCore import Qt, Signal
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.icons import IconWidget
from simulator.gui.components import (
    NodePill, PageTitleBar, RedSepH, RedSepV, HSep,
    ActionButton, DangerButton, SuccessButton, GhostButton,
    PillButton, PillSelector, RadioGroup, TextField,
    IntField, FloatField, HexField,
    SectionLabel, ValueLabel, StatusLabel, BadgeLabel,
    Card, SubCard, InfoRow, BackButton, DataTable,
)

# ── Sensor icon map: sensor_id → (fa6 icon name, Unicode fallback) ─
_SENSOR_ICONS: dict[int, tuple[str, str]] = {
    0x04: ("fa6s.arrows-left-right", "↔"),
    0x03: ("fa6s.arrow-up-long",     "↑"),
    0x01: ("fa6s.gauge-high",        "⊙"),
    0x09: ("fa6s.gamepad",           "□"),
}

# Slider uses integer steps internally; converts to/from float range on demand
_SLIDER_STEPS = 10_000


class _SensorCard(QWidget):
    """
    Compact sensor control card.  Fixed height so 4 cards sit cleanly
    without stretching.  Width is constrained by SensorsPage to 520 px.

    Row layout:
      Row 1 — header:   [icon] NAME [stretch] VALUE unit  ● STATE
      Row 2 — slider:   MIN ────────●──────── MAX
      Row 3 — target:         [stretch] TARGET [input] unit [↺]

    Left accent bar (4 px) reflects state:
      #FFD100 yellow  → ramping toward target
      #22C55E green   → at target (non-zero)
      #2A2A2A dim     → idle (at zero)
    """

    target_changed = Signal(int, float)   # (sensor_id, target_value)

    # State tuples: (fa_icon, fallback, dot_color, label, label_color, border_color)
    _S_IDLE   = ("fa6s.circle-dot",   "●", "#333333", "IDLE",      "#3A3A3A", "#2A2A2A")
    _S_RAMP   = ("fa6s.circle-notch", "◔", "#FFD100", "RAMPING",   "#FFD100", "#FFD100")
    _S_ON_TGT = ("fa6s.circle-check", "●", "#22C55E", "AT TARGET", "#22C55E", "#22C55E")

    # Slider stylesheet — Hyva yellow handle, amber taper fill
    _SLIDER_SS = f"""
        QSlider::groove:horizontal {{
            height: 4px; background: #1A1A1A;
            border: none; border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #6A4C00, stop:0.6 #B88800, stop:1 #FFD100);
            border-radius: 2px;
        }}
        QSlider::add-page:horizontal {{
            background: #222222; border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: #FFD100; border: 1.5px solid #A38600;
            width: 13px; height: 13px; margin: -5px 0;
            border-radius: 7px;
        }}
        QSlider::handle:horizontal:hover   {{ background: #FFE040; }}
        QSlider::handle:horizontal:pressed {{ background: #CC9900; }}
    """

    def __init__(
        self,
        sensor_id: int,
        label: str,
        unit: str,
        min_val: float,
        max_val: float,
        default: float,
        ramp: float,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        self._sid     = sensor_id
        self._unit    = unit
        self._min     = min_val
        self._max     = max_val
        self._span    = (max_val - min_val) or 1.0
        self._target  = default
        self._current = default

        self.setObjectName("SensorCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Fixed height keeps all 4 cards uniform — no vertical stretching
        self.setFixedHeight(88)
        self.setStyleSheet("""
            QWidget#SensorCard {
                background: #181818;
                border: 1px solid #262626;
                border-radius: 8px;
            }
        """)

        # ── Outer: accent bar (4 px) + content ───────────────────────
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._accent = QFrame()
        self._accent.setFixedWidth(4)
        self._accent.setObjectName("CardAccent")
        self._accent.setStyleSheet(
            "QFrame#CardAccent { background:#2A2A2A; border-radius:4px 0 0 4px; }"
        )
        outer.addWidget(self._accent)

        content = QWidget()
        content.setObjectName("CardContent")
        content.setStyleSheet("QWidget#CardContent { background:transparent; }")
        inner = QVBoxLayout(content)
        inner.setContentsMargins(12, 8, 12, 8)
        inner.setSpacing(4)
        outer.addWidget(content, 1)

        # ── Row 1 — name │ live value │ state ─────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        fa_name, fallback = _SENSOR_ICONS.get(sensor_id, ("fa6s.sliders", "⊙"))
        row1.addWidget(IconWidget(fa=fa_name, fallback=fallback, colour="#FFD100", size=10))

        name_lbl = QLabel(label.upper())
        name_lbl.setStyleSheet(
            "color:#FFD100; font-size:10px; letter-spacing:1.5px;"
            " font-weight:600; background:transparent;"
        )
        row1.addWidget(name_lbl)
        row1.addStretch()

        # Live value — fixed-width monospace so digits never shift
        self._current_lbl = QLabel(f"{default:+.3f}")
        self._current_lbl.setFixedWidth(72)
        self._current_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._current_lbl.setStyleSheet(
            f"color:#E8E8E8; font-size:15px; font-weight:700;"
            f" font-family:{t.FONT_MONO}; background:transparent;"
        )
        row1.addWidget(self._current_lbl)

        if unit:
            u1 = QLabel(unit)
            u1.setStyleSheet(
                "color:#4A4A4A; font-size:10px; background:transparent;"
            )
            row1.addWidget(u1)

        self._status_dot = IconWidget(fa="fa6s.circle-dot", fallback="●", colour="#333333", size=7)
        self._status_lbl = QLabel("IDLE")
        self._status_lbl.setStyleSheet(
            "color:#3A3A3A; font-size:8px; letter-spacing:1px; background:transparent;"
        )
        row1.addSpacing(4)
        row1.addWidget(self._status_dot)
        row1.addWidget(self._status_lbl)
        inner.addLayout(row1)

        # ── Row 2 — range labels flanking the slider ──────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(5)

        mn_lbl = QLabel(f"{min_val:g}")
        mn_lbl.setStyleSheet("color:#555555; font-size:9px; background:transparent;")
        row2.addWidget(mn_lbl)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, _SLIDER_STEPS)
        self._slider.setValue(self._val_to_step(default))
        self._slider.setFixedHeight(16)
        self._slider.setStyleSheet(self._SLIDER_SS)
        row2.addWidget(self._slider, 1)

        mx_lbl = QLabel(f"{max_val:g}")
        mx_lbl.setStyleSheet("color:#555555; font-size:9px; background:transparent;")
        row2.addWidget(mx_lbl)
        inner.addLayout(row2)

        # ── Row 3 — target label │ input │ unit │ reset ──────────────
        row3 = QHBoxLayout()
        row3.setSpacing(5)
        row3.addStretch()

        tgt_lbl = QLabel("TARGET")
        tgt_lbl.setStyleSheet(
            "color:#3A3A3A; font-size:8px; letter-spacing:1px; background:transparent;"
        )
        row3.addWidget(tgt_lbl)

        self._target_inp = QLineEdit(f"{default:.3f}")
        self._target_inp.setFixedWidth(72)
        self._target_inp.setAlignment(Qt.AlignRight)
        self._target_inp.setStyleSheet(f"""
            QLineEdit {{
                background:#0E0E0E; color:#FFD100;
                border:1px solid #2A2A2A; border-radius:3px;
                padding:1px 5px; font-size:11px;
                font-family:{t.FONT_MONO};
            }}
            QLineEdit:focus {{ border-color:#FFD100; }}
        """)
        row3.addWidget(self._target_inp)

        if unit:
            tu = QLabel(unit)
            tu.setStyleSheet(
                "color:#3A3A3A; font-size:9px; background:transparent;"
            )
            row3.addWidget(tu)

        btn_reset = QPushButton("↺")
        btn_reset.setFixedSize(18, 18)
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setToolTip("Reset to 0.0")
        btn_reset.setStyleSheet("""
            QPushButton {
                background:transparent; color:#333333;
                border:none; font-size:12px; padding:0;
            }
            QPushButton:hover   { color:#FFD100; }
            QPushButton:pressed { color:#B89000; }
        """)
        btn_reset.clicked.connect(lambda: self._set_target(0.0, send=True))
        row3.addWidget(btn_reset)
        inner.addLayout(row3)

        # ── Signal wiring — logic unchanged ──────────────────────────
        self._slider.valueChanged.connect(self._on_slider_moved)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._target_inp.returnPressed.connect(self._on_inp_return)
        self._target_inp.editingFinished.connect(self._on_inp_return)

    # ── Private helpers ───────────────────────────────────────────────

    def _val_to_step(self, val: float) -> int:
        pos = (val - self._min) / self._span * _SLIDER_STEPS
        return max(0, min(_SLIDER_STEPS, int(pos)))

    def _step_to_val(self, step: int) -> float:
        return self._min + step / _SLIDER_STEPS * self._span

    def _clamp(self, val: float) -> float:
        return max(self._min, min(self._max, val))

    def _set_target(self, val: float, *, send: bool = False) -> None:
        """Set new target, sync slider and text field, optionally emit signal."""
        val = self._clamp(val)
        self._target = val

        self._slider.blockSignals(True)
        self._slider.setValue(self._val_to_step(val))
        self._slider.blockSignals(False)

        self._target_inp.blockSignals(True)
        self._target_inp.setText(f"{val:.3f}")
        self._target_inp.blockSignals(False)

        self._refresh_status()

        if send:
            logger.info(
                f"[SENSORS] sid={self._sid:#04x}  target={val:.3f} {self._unit}"
            )
            self.target_changed.emit(self._sid, val)

    def _refresh_status(self) -> None:
        """Update the left accent bar and status pill to reflect current state."""
        at_tgt = abs(self._current - self._target) < 1e-3
        if at_tgt and abs(self._target) < 1e-3:
            tpl = self._S_IDLE
        elif at_tgt:
            tpl = self._S_ON_TGT
        else:
            tpl = self._S_RAMP

        fa, fb, fc, txt, tc, border_col = tpl

        self._accent.setStyleSheet(
            f"QFrame#CardAccent {{ background:{border_col};"
            f" border-radius:4px 0 0 4px; }}"
        )
        self._status_dot.set_colour(fc)
        self._status_lbl.setText(txt)
        self._status_lbl.setStyleSheet(
            f"color:{tc}; font-size:8px; letter-spacing:1px; background:transparent;"
        )

    # ── Slots ─────────────────────────────────────────────────────────

    def _on_slider_moved(self, step: int) -> None:
        """Live-update text field while dragging; do NOT emit to bridge yet."""
        val = self._clamp(self._step_to_val(step))
        self._target = val
        self._target_inp.blockSignals(True)
        self._target_inp.setText(f"{val:.3f}")
        self._target_inp.blockSignals(False)
        self._refresh_status()

    def _on_slider_released(self) -> None:
        """Slider released — commit and emit to bridge."""
        val = self._clamp(self._step_to_val(self._slider.value()))
        self._target = val
        logger.info(
            f"[SENSORS] sid={self._sid:#04x}  slider released → {val:.3f} {self._unit}"
        )
        self.target_changed.emit(self._sid, val)

    def _on_inp_return(self) -> None:
        """Text field committed (Return or focus-out)."""
        try:
            val = float(self._target_inp.text().replace(",", "."))
        except ValueError:
            logger.warning(
                f"[SENSORS] sid={self._sid:#04x}  invalid input:"
                f" {self._target_inp.text()!r}"
            )
            self._target_inp.setText(f"{self._target:.3f}")
            return
        self._set_target(val, send=True)

    # ── Public API ────────────────────────────────────────────────────

    def update_current(self, value: float) -> None:
        """Receive live ramp value from bridge. Called on main thread via Qt signal."""
        self._current = value
        self._current_lbl.setText(f"{value:+.3f}")
        self._refresh_status()


class SensorsPage(QWidget):
    """
    Page 2 — Sensor controls.

    Four compact sensor cards stacked vertically, left-aligned, 520 px wide.
    Cards do not expand to fill the window — space to the right and below
    is intentionally left free for future use.

    Layout (left-aligned, page-level):
      ┌─ SENSORS ──────────────────────────────────────────────────────┐
      │  ┌── card 520 px ──────────────────────────────────────────┐  │
      │  │  ↔  LATERAL TILT        +0.000 °    ● IDLE             │  │
      │  │  -18.75 ────────●──────────────── 18.75                │  │
      │  │                      TARGET  0.000  °  ↺               │  │
      │  └─────────────────────────────────────────────────────────┘  │
      │  (× 3 more cards, 8 px gap between)                           │
      │                                                                │
      │  (free space below + to the right)                            │
      └────────────────────────────────────────────────────────────────┘

    Decoupled from ObuBridge:
      - SensorsPage emits sensor_target_changed(sid, val)
      - MainWindow connects that to bridge.set_sensor_target
      - MainWindow connects bridge.sensor_reading_changed to update_sensor_reading

    Call set_obu_bridge() from MainWindow after both objects exist.
    """

    sensor_target_changed = Signal(int, float)   # (sensor_id, target_value)

    # Card width — wide enough for the slider to be usable, narrow enough to
    # feel compact and intentional.  Right side of page is free space.
    _CARD_WIDTH = 520

    _LABEL_OVERRIDE: dict[int, str] = {
        0x04: "Lateral Tilt",
        0x03: "Longitudinal Tilt",
        0x01: "Cylinder Pressure",
        0x09: "Joystick Position",
    }

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        from simulator.obu.obu_bridge import SENSOR_DEFS

        # Page root — top-aligned, left-aligned; does NOT stretch to fill
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(20, 16, 20, 20)
        page_layout.setSpacing(12)
        # NOTE: do NOT call setAlignment on the layout here.
        # setAlignment applies to ALL items in the layout, which would
        # constrain PageTitleBar to its minimum width and clip the separator.
        # Per-item alignment (Qt.AlignLeft) is set on individual addWidget calls.

        page_layout.addWidget(PageTitleBar("SENSORS"))

        # Card list — vertical, top-aligned, cards at fixed width
        self._cards: dict[int, _SensorCard] = {}

        for sid, label, unit, mn, mx, default, ramp in SENSOR_DEFS:
            display = self._LABEL_OVERRIDE.get(sid, label)
            card = _SensorCard(sid, display, unit, mn, mx, default, ramp)
            card.setFixedWidth(self._CARD_WIDTH)
            card.target_changed.connect(self.sensor_target_changed)
            self._cards[sid] = card
            page_layout.addWidget(card, 0, Qt.AlignLeft | Qt.AlignTop)

        logger.debug(f"[SENSORS] Page built — {len(self._cards)} sensor cards")

    # ── Public slots ───────────────────────────────────────────────

    def update_sensor_reading(self, sensor_id: int, current_value: float) -> None:
        """Slot — receive live ramp value from bridge and update the matching card."""
        card = self._cards.get(sensor_id)
        if card:
            card.update_current(current_value)

    def set_obu_bridge(self, bridge: "ObuBridge | None") -> None:
        """
        Wire the OBU bridge after construction.
        Safe to call with bridge=None (logs a warning, page works disconnected).
        """
        if bridge is None:
            logger.warning("[SENSORS] set_obu_bridge: bridge=None — page runs disconnected")
            return
        self.sensor_target_changed.connect(bridge.set_sensor_target)
        bridge.sensor_reading_changed.connect(self.update_sensor_reading)
        logger.info(f"[SENSORS] Bridge wired — {len(self._cards)} sensor cards active")


