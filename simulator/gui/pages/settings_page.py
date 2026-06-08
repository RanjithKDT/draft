from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QSizePolicy, QFrame, QPushButton, QScrollArea, QLineEdit,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.icons import IconWidget
from simulator.gui.components import PageTitleBar, HSep
from simulator.gui.constants import PROJECT_ROOT
from simulator.platform.platform_detector import PlatformProfile
from simulator.gui._version import APP_VERSION


class _SettingsSubPage(QWidget):
    """Base for settings sub-pages — shared back navigation, platform strip, and back button."""

    _CARD = "#222222"
    _BDR  = "#3A3A3A"
    _BDR2 = "#505050"
    _TXT  = "#F0F0F0"
    _DIM  = "#666666"
    _ACC  = "#FFD100"

    def __init__(self, profile: "PlatformProfile | None" = None, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._profile = profile

    def _go_settings(self) -> None:
        w = self.parent()
        while w is not None:
            if hasattr(w, "_switch_page"):
                w._switch_page(5)
                return
            w = w.parent() if hasattr(w, "parent") else None

    def _back_button(self) -> QPushButton:
        btn = QPushButton("← Back to Settings")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {t.TEXT_DIM};
                border: 1px solid {t.BORDER_FAINT};
                border-radius: 4px;
                font-size: 10px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                color: {t.RED};
                border-color: {t.RED};
            }}
        """)
        btn.clicked.connect(self._go_settings)
        return btn

    def _vdiv(self) -> QWidget:
        """Thin vertical divider used inside platform strip."""
        inner = QWidget()
        inner.setFixedSize(1, 18)
        inner.setStyleSheet(f"background:{self._BDR2};")
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        r = QHBoxLayout(wrap)
        r.setContentsMargins(12, 0, 12, 0)
        r.addWidget(inner)
        return wrap

    def _build_platform_strip(self) -> QWidget:
        """
        Info strip showing OS label, CAN backend, and CAN channel.
        Raspi overrides this with its own strip showing the Pi model label.
        """
        strip = QWidget()
        strip.setObjectName("PlatformStrip")
        strip.setAttribute(Qt.WA_StyledBackground, True)
        strip.setStyleSheet(f"""
            QWidget#PlatformStrip {{
                background-color: {self._CARD};
                border: 1px solid {self._BDR};
                border-left: 3px solid {self._ACC};
                border-radius: 8px;
            }}
        """)
        row = QHBoxLayout(strip)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(0)

        row.addWidget(IconWidget(fa="fa6s.desktop", fallback="⬡", colour=self._ACC, size=13))
        row.addSpacing(8)

        display = self._profile.display_label if self._profile else "UNKNOWN"
        name_lbl = QLabel(display)
        name_lbl.setStyleSheet(
            f"color:{self._TXT}; font-size:11px; font-weight:700; "
            "letter-spacing:0.5px; background:transparent;"
        )
        row.addWidget(name_lbl, 0, Qt.AlignVCenter)
        row.addWidget(self._vdiv())

        backend = (
            self._profile.can_backend.value.upper()
            if self._profile else "—"
        )
        backend_lbl = QLabel(backend)
        backend_lbl.setStyleSheet(
            f"color:{self._DIM}; font-size:10px; "
            "font-family:monospace; background:transparent;"
        )
        row.addWidget(backend_lbl, 0, Qt.AlignVCenter)
        row.addWidget(self._vdiv())

        channel = self._profile.can_channel if self._profile else "—"
        channel_lbl = QLabel(channel)
        channel_lbl.setStyleSheet(
            f"color:{self._DIM}; font-size:10px; "
            "font-family:monospace; background:transparent;"
        )
        row.addWidget(channel_lbl, 0, Qt.AlignVCenter)
        row.addStretch()
        return strip


_GPIO_PIN_INFO: dict[int, tuple[str, str]] = {
    0:  ("ID EEPROM SDA",   ""),   1:  ("ID EEPROM SCL",   ""),
    2:  ("I2C1 SDA",        ""),   3:  ("I2C1 SCL",        ""),
    4:  ("GPCLK0",          ""),   5:  ("GPIO 5",          ""),
    6:  ("GPIO 6",          ""),   7:  ("SPI0 CE1",        ""),
    8:  ("SPI0 CE0",        ""),   9:  ("SPI0 MISO",       ""),
    10: ("SPI0 MOSI",       ""),   11: ("SPI0 SCLK",       ""),
    12: ("PWM0",            ""),   13: ("PWM1",             ""),
    14: ("UART TXD",        ""),   15: ("UART RXD",        ""),
    16: ("GPIO 16",         ""),   17: ("GPIO 17",         ""),
    18: ("PCM CLK / PWM0",  ""),   19: ("PCM FS  / PWM1",  ""),
    20: ("PCM DIN",         ""),   21: ("PCM DOUT",        ""),
    22: ("GPIO 22",         ""),   23: ("GPIO 23",         ""),
    24: ("GPIO 24",         ""),   25: ("GPIO 25",         ""),
    26: ("GPIO 26",         ""),   27: ("GPIO 27",         "Ignition K15 (gpiod)"),
}


class _RaspiSettingsPage(_SettingsSubPage):
    """Raspberry Pi GPIO settings — pin state, assignment, and chip config."""

    _BG  = "#1A1A1A"
    _GRN = "#22C55E"
    _RED = "#CC4444"

    def __init__(self, profile: "PlatformProfile | None" = None, parent: "QWidget | None" = None) -> None:
        super().__init__(profile, parent)
        self._pin_roles: dict[int, str] = {
            bcm: role for bcm, (_, role) in _GPIO_PIN_INFO.items()
        }
        self._role_labels:   dict[int, QLabel]    = {}
        self._state_pills:   dict[int, QWidget]   = {}
        self._config_inputs: dict[int, QLineEdit] = {}

        # Populated by _build_platform_strip() — always called, so always valid.
        # Declared here so _scan_gpio() can reference them regardless of call order.
        # Type is IconWidget so set_colour() can be called without casting.
        self._gpio_status_dot: "IconWidget | None" = None
        self._gpio_status_lbl: QLabel | None = None

        self.setStyleSheet(f"background-color: {self._BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(12)

        # Header row: page title pill left, back button right.
        # show_separator=False: suppresses the internal HSep in PageTitleBar.
        # The external HSep below provides a single full-width separator.
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(8)
        hdr_row.addWidget(PageTitleBar("RASPBERRY PI SETTINGS", show_separator=False))
        # Strip: Pi model (e.g. "RASPBERRY PI 4 MODEL B") or generic "RASPBERRY PI"
        hdr_row.addWidget(self._build_platform_strip())
        hdr_row.addStretch()
        hdr_row.addWidget(self._back_button())
        root.addLayout(hdr_row)
        root.addWidget(HSep())    # full-width separator spanning entire row

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        vlay = QVBoxLayout(body)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(16)

        vlay.addWidget(self._build_gpio_card())
        vlay.addLayout(self._build_reset_row())
        vlay.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll)

        self._scan_gpio()

    def _is_raspi(self) -> bool:
        """Return True when the detected platform is Raspberry Pi."""
        if self._profile is None:
            return False
        from simulator.platform.platform_detector import OperatingSystem
        return self._profile.operating_system == OperatingSystem.RASPBERRY_PI

    def _build_platform_strip(self) -> QWidget:
        """
        Platform strip for the Raspberry Pi page.
        Same pill style as Windows and Linux settings pages — auto-sizes to content.
        Shows the Pi model when on Raspberry Pi, or "RASPBERRY PI" on any other OS.
        GPIO chip and scan status are shown inside the GPIO card, not in this strip.
        """
        strip = QWidget()
        strip.setObjectName("PlatformStrip")
        strip.setAttribute(Qt.WA_StyledBackground, True)
        strip.setFixedHeight(36)
        strip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        strip.setStyleSheet(f"""
            QWidget#PlatformStrip {{
                background-color: {self._CARD};
                border: 1px solid {self._BDR};
                border-left: 3px solid {self._ACC};
                border-radius: 8px;
            }}
        """)
        row = QHBoxLayout(strip)
        row.setContentsMargins(12, 0, 16, 0)
        row.setSpacing(8)

        row.addWidget(IconWidget(fa="fa6s.microchip", fallback="⬡", colour=self._ACC, size=13))

        # On Pi: show auto-detected model e.g. "RASPBERRY PI 4 MODEL B".
        # On other OS: show the generic "RASPBERRY PI" fallback label.
        if self._is_raspi() and self._profile:
            display = self._profile.display_label
        else:
            display = "RASPBERRY PI"

        name_lbl = QLabel(display)
        name_lbl.setObjectName("PanelTitle")
        row.addWidget(name_lbl, 0, Qt.AlignVCenter)
        return strip


    def _build_gpio_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("GpioCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            QWidget#GpioCard {{
                background-color: {self._CARD};
                border: 1px solid {self._BDR};
                border-top: 2px solid {self._ACC};
                border-radius: 8px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        ic = IconWidget(fa="fa6s.microchip", fallback="⬡", colour=self._ACC, size=13)
        ic.setFixedWidth(18)
        hdr.addWidget(ic, 0, Qt.AlignVCenter)
        title = QLabel("GPIO PINS")
        title.setStyleSheet(
            f"color:{self._ACC}; font-size:11px; font-weight:700; "
            "letter-spacing:1px; background:transparent;"
        )
        hdr.addWidget(title, 0, Qt.AlignVCenter)
        hdr.addStretch()

        chip_hint = QLabel("chip override:")
        chip_hint.setStyleSheet(
            f"color:{self._DIM}; font-size:9px; background:transparent;"
        )
        hdr.addWidget(chip_hint, 0, Qt.AlignVCenter)

        self._gpio_chip = QLineEdit()
        self._gpio_chip.setPlaceholderText("auto")
        self._gpio_chip.setFixedSize(90, 22)
        self._gpio_chip.setStyleSheet(f"""
            QLineEdit {{
                background-color: #111111;
                color: {self._TXT};
                border: 1px solid {self._BDR2};
                border-radius: 3px;
                padding: 0 6px;
                font-size: 10px;
                font-family: monospace;
            }}
            QLineEdit:focus {{ border-color: {self._ACC}; }}
        """)
        hdr.addWidget(self._gpio_chip, 0, Qt.AlignVCenter)

        self._scan_status = QLabel("")
        self._scan_status.setStyleSheet(
            f"color:{self._DIM}; font-size:10px; background:transparent;"
        )
        hdr.addWidget(self._scan_status, 0, Qt.AlignVCenter)

        scan_btn = QPushButton("⟳  Rescan")
        scan_btn.setCursor(Qt.PointingHandCursor)
        scan_btn.setFixedHeight(24)
        scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1A1A1A;
                color: {self._DIM};
                border: 1px solid {self._BDR};
                border-radius: 4px;
                font-size: 10px;
                padding: 0 12px;
            }}
            QPushButton:hover {{ color: {self._ACC}; border-color: {self._ACC}; }}
        """)
        scan_btn.clicked.connect(self._scan_gpio)
        hdr.addWidget(scan_btn)
        lay.addLayout(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background:{self._BDR}; max-height:1px;")
        lay.addWidget(sep)

        col_hdr = QHBoxLayout()
        col_hdr.setContentsMargins(0, 0, 0, 0)
        col_hdr.setSpacing(6)
        for text, width in [
            ("BCM", 58), ("FUNCTION", 160), ("STATE", 110), ("ASSIGNMENT", 160)
        ]:
            lbl = QLabel(text)
            lbl.setFixedWidth(width)
            lbl.setStyleSheet(
                f"color:{self._DIM}; font-size:8px; "
                "letter-spacing:1.5px; background:transparent;"
            )
            col_hdr.addWidget(lbl)
        col_hdr.addStretch()
        lay.addLayout(col_hdr)

        self._pins_container = QWidget()
        self._pins_container.setStyleSheet("background:transparent;")
        self._pins_layout = QVBoxLayout(self._pins_container)
        self._pins_layout.setContentsMargins(0, 0, 0, 0)
        self._pins_layout.setSpacing(4)
        lay.addWidget(self._pins_container)
        return card

    def _build_pin_rows(
        self, rows: list[tuple[int, str, str, str, str]]
    ) -> None:
        while self._pins_layout.count():
            item = self._pins_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._role_labels.clear()
        self._state_pills.clear()
        self._config_inputs.clear()

        for bcm, _func, _default_role, val, direction in rows:
            func = _GPIO_PIN_INFO.get(bcm, (f"GPIO {bcm}", ""))[0]
            current_role = self._pin_roles.get(bcm, "")

            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(6)

            bcm_lbl = QLabel(f"BCM {bcm:02d}")
            bcm_lbl.setFixedWidth(58)
            bcm_lbl.setStyleSheet(
                f"color:{'#FFD100' if current_role else self._DIM}; "
                "font-size:10px; font-family:monospace; "
                "font-weight:700; background:transparent;"
            )
            row_lay.addWidget(bcm_lbl, 0, Qt.AlignVCenter)

            func_lbl = QLabel(func)
            func_lbl.setFixedWidth(160)
            func_lbl.setStyleSheet(
                f"color:{self._TXT}; font-size:10px; background:transparent;"
            )
            row_lay.addWidget(func_lbl, 0, Qt.AlignVCenter)

            state_pill = self._make_state_pill(val, direction)
            state_pill.setFixedWidth(110)
            row_lay.addWidget(state_pill, 0, Qt.AlignVCenter)

            role_lbl = QLabel(current_role or "—")
            role_lbl.setFixedWidth(160)
            role_lbl.setStyleSheet(
                f"color:{'#FFD100' if current_role else self._DIM}; "
                "font-size:10px; background:transparent;"
            )
            row_lay.addWidget(role_lbl, 0, Qt.AlignVCenter)

            inp = QLineEdit()
            inp.setPlaceholderText("assign role…")
            inp.setFixedHeight(24)
            inp.setStyleSheet(f"""
                QLineEdit {{
                    background-color: #111111;
                    color: {self._TXT};
                    border: 1px solid {self._BDR};
                    border-radius: 4px;
                    padding: 0 8px;
                    font-size: 10px;
                }}
                QLineEdit:focus {{ border-color: {self._ACC}; }}
            """)
            row_lay.addWidget(inp, 1)

            apply_btn = QPushButton("APPLY")
            apply_btn.setFixedHeight(24)
            apply_btn.setCursor(Qt.PointingHandCursor)
            apply_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self._ACC};
                    color: #000000;
                    border: none;
                    border-radius: 4px;
                    font-size: 9px;
                    font-weight: 700;
                    letter-spacing: 1px;
                    padding: 0 10px;
                }}
                QPushButton:hover {{ background-color: #E8BA00; }}
                QPushButton:pressed {{ background-color: #C9A000; }}
            """)
            apply_btn.clicked.connect(
                lambda _, b=bcm, i=inp, rl=role_lbl, bl=bcm_lbl:
                    self._on_apply(b, i, rl, bl)
            )
            row_lay.addWidget(apply_btn, 0, Qt.AlignVCenter)

            self._pins_layout.addWidget(row_w)
            self._role_labels[bcm]   = role_lbl
            self._state_pills[bcm]   = state_pill
            self._config_inputs[bcm] = inp

    def _make_state_pill(self, val: str, direction: str) -> QWidget:
        pill = QWidget()
        pill.setStyleSheet("background:transparent;")
        row = QHBoxLayout(pill)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)

        if val == "HIGH":
            dot_color = self._GRN
        elif val == "LOW":
            dot_color = self._RED
        else:
            dot_color = "#444444"

        dot = IconWidget(fa="fa6s.circle", fallback="●", colour=dot_color, size=8)
        dot.setFixedSize(10, 10)
        row.addWidget(dot, 0, Qt.AlignVCenter)

        text = f"{val} · {direction}" if val != "—" else "— · —"
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{self._DIM}; font-size:10px; background:transparent;"
        )
        row.addWidget(lbl, 0, Qt.AlignVCenter)
        return pill

    def _build_reset_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 0)
        row.addStretch()
        btn = QPushButton("↺  Reset")
        btn.setFixedHeight(30)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._CARD};
                color: {self._TXT};
                border: 1px solid {self._BDR};
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {self._ACC};
                color: #000;
                border-color: {self._ACC};
            }}
        """)
        btn.clicked.connect(self._on_reset)
        row.addWidget(btn)
        return row


    def _on_apply(
        self, bcm: int, inp: QLineEdit, role_lbl: QLabel, bcm_lbl: QLabel
    ) -> None:
        text = inp.text().strip()
        self._pin_roles[bcm] = text
        role_lbl.setText(text or "—")
        has_role = bool(text)
        role_lbl.setStyleSheet(
            f"color:{'#FFD100' if has_role else self._DIM}; "
            "font-size:10px; background:transparent;"
        )
        bcm_lbl.setStyleSheet(
            f"color:{'#FFD100' if has_role else self._DIM}; "
            "font-size:10px; font-family:monospace; "
            "font-weight:700; background:transparent;"
        )
        inp.clear()
        logger.info(f"[SETTINGS] BCM {bcm} → \"{text}\"")

    def _on_reset(self) -> None:
        for bcm in range(28):
            self._pin_roles[bcm] = _GPIO_PIN_INFO.get(bcm, (f"GPIO {bcm}", ""))[1]
        self._scan_gpio()
        logger.info("[SETTINGS] Assignments reset to defaults")

    def _scan_gpio(self) -> None:
        """Detect GPIO pin states. Priority: gpiod → RPi.GPIO → reference."""
        self._scan_status.setText("scanning…")

        rows: list[tuple[int, str, str, str, str]] = []
        source = "reference"

        try:
            import gpiod
            chip_name  = self._gpio_chip.text().strip() or None
            candidates = (
                [chip_name] if chip_name
                else ["gpiochip0", "gpiochip1", "gpiochip2", "gpiochip4"]
            )
            chip_obj = None
            for cname in candidates:
                try:
                    chip_obj = gpiod.Chip(cname)
                    break
                except Exception:
                    continue
            if chip_obj:
                for bcm in range(min(chip_obj.num_lines(), 28)):
                    line = chip_obj.get_line(bcm)
                    direction = (
                        "OUT"
                        if line.direction() == gpiod.Line.DIRECTION_OUTPUT
                        else "IN"
                    )
                    try:
                        val = "HIGH" if line.get_value() else "LOW"
                    except Exception:
                        val = "—"
                    func, role = _GPIO_PIN_INFO.get(bcm, (f"GPIO {bcm}", ""))
                    rows.append((bcm, func, role, val, direction))
                chip_obj.close()
                source = "gpiod (live)"
        except ImportError:
            logger.debug("[GPIO] gpiod not installed — skipping (expected on non-Pi)")
        except Exception as ex:
            logger.warning(f"[GPIO] gpiod: {ex}")

        if not rows:
            try:
                import RPi.GPIO as GPIO  # type: ignore
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                for bcm in range(28):
                    try:
                        val = "HIGH" if GPIO.input(bcm) else "LOW"
                    except Exception:
                        val = "—"
                    func, role = _GPIO_PIN_INFO.get(bcm, (f"GPIO {bcm}", ""))
                    rows.append((bcm, func, role, val, "—"))
                source = "RPi.GPIO (live)"
            except ImportError:
                logger.debug("[GPIO] RPi.GPIO not installed — skipping (expected on non-Pi)")
            except Exception as ex:
                logger.warning(f"[GPIO] RPi.GPIO: {ex}")

        if not rows:
            for bcm in range(28):
                func, role = _GPIO_PIN_INFO.get(bcm, (f"GPIO {bcm}", ""))
                rows.append((bcm, func, role, "—", "—"))
            source = "reference  (not a Pi)"

        self._scan_status.setText(f"28 pins  ·  {source}")

        is_live = source.startswith("gpiod") or source.startswith("RPi")
        dot_color   = self._GRN if is_live else "#444444"
        status_text = "LIVE" if is_live else "REFERENCE"

        # These widgets only exist when the platform strip was built (Pi only).
        if self._gpio_status_dot is not None:
            self._gpio_status_dot.set_colour(dot_color)
        if self._gpio_status_lbl is not None:
            self._gpio_status_lbl.setText(status_text)
            self._gpio_status_lbl.setStyleSheet(
                f"color:{dot_color}; font-size:10px; "
                "letter-spacing:1px; background:transparent;"
            )

        self._build_pin_rows(rows)


class HyvaProductsPage(QWidget):
    """
    Page — Hyva Products.
    Four product cards: GUIDE · CONTROL · TIP BY WIRE · EPTO.
    Each card shows a colour-coded icon, short description, and key features.
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(16)

        root.addWidget(PageTitleBar("HYVA PRODUCTS"))

        intro = QLabel(
            "Hyva tipping system products supported by this simulator testbench."
        )
        intro.setStyleSheet(
            f"color:{t.TEXT_DIM}; font-size:11px;"
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        # ── 2 × 2 product card grid ───────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 0, 0)

        products = [
            {
                "name":        "GUIDE",
                "accent":      "#FFD100",   # Hyva yellow
                "fa_icon":     "fa6s.compass",
                "icon":        "◎",
                "tagline":     "Body guidance & angle monitoring",
                "features": [
                    "Real-time inclination feedback",
                    "Lateral + longitudinal tilt sensing",
                    "Overload & topple-over detection",
                    "J1939 CAN integration",
                ],
            },
            {
                "name":        "CONTROL",
                "accent":      "#38BDF8",   # cyan
                "fa_icon":     "fa6s.sliders",
                "icon":        "⊞",
                "tagline":     "Electronic tipping cycle control",
                "features": [
                    "Automated raise / lower sequencing",
                    "Pressure sensor integration (0–500 bar)",
                    "DTS mode management (CONNECT / CONTROL)",
                    "Safety interlock & state machine",
                ],
            },
            {
                "name":        "TIP BY WIRE",
                "accent":      "#4ADE80",   # green
                "fa_icon":     "fa6s.bolt",
                "icon":        "⚡",
                "tagline":     "Full electronic tip actuation",
                "features": [
                    "Wire-controlled hydraulic valve",
                    "Joystick & CAN input",
                    "Body tipped / stowed detection",
                    "Redundant safety monitoring",
                ],
            },
            {
                "name":        "EPTO",
                "accent":      "#F97316",   # orange
                "fa_icon":     "fa6s.gear",
                "icon":        "⚙",
                "tagline":     "Electronic Power Take-Off control",
                "features": [
                    "Engine speed & torque management",
                    "PTO engagement sequencing",
                    "Over-speed protection",
                    "CAN-based truck integration",
                ],
            },
        ]

        for i, prod in enumerate(products):
            row, col = divmod(i, 2)
            grid.addWidget(self._product_card(prod), row, col)

        root.addLayout(grid)
        root.addStretch()

    @staticmethod
    def _product_card(p: dict) -> QWidget:
        card = QWidget()
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            QWidget {{
                background-color: #1A1A1A;
                border: 1px solid #2C2C2C;
                border-top: 3px solid {p['accent']};
                border-radius: 8px;
            }}
        """)
        col = QVBoxLayout(card)
        col.setContentsMargins(20, 18, 20, 20)
        col.setSpacing(0)

        # Icon + name row
        head_row = QHBoxLayout()
        head_row.setSpacing(12)
        head_row.setContentsMargins(0, 0, 0, 0)

        icon_lbl = IconWidget(fa=p["fa_icon"], fallback=p["icon"], colour=p["accent"], size=22)
        icon_lbl.setFixedWidth(32)
        head_row.addWidget(icon_lbl, 0, Qt.AlignVCenter)

        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        name_lbl = QLabel(p["name"])
        name_lbl.setStyleSheet(
            f"color:{p['accent']}; font-size:15px; font-weight:700;"
            " letter-spacing:1px; background:transparent;"
        )
        tagline_lbl = QLabel(p["tagline"])
        tagline_lbl.setStyleSheet(
            f"color:{t.TEXT_DIM}; font-size:10px; background:transparent;"
        )
        name_col.addWidget(name_lbl)
        name_col.addWidget(tagline_lbl)
        head_row.addLayout(name_col)
        head_row.addStretch()
        col.addLayout(head_row)

        # Divider
        col.addSpacing(12)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:#2C2C2C; background:#2C2C2C;")
        col.addWidget(sep)
        col.addSpacing(10)

        # Feature bullets
        for feat in p["features"]:
            feat_row = QHBoxLayout()
            feat_row.setSpacing(8)
            feat_row.setContentsMargins(0, 0, 0, 0)

            dot = QLabel("▸")
            dot.setFixedWidth(14)
            dot.setStyleSheet(
                f"color:{p['accent']}; font-size:9px; background:transparent;"
            )
            feat_lbl = QLabel(feat)
            feat_lbl.setStyleSheet(
                f"color:{t.TEXT_BRIGHT}; font-size:11px;"
                " background:transparent;"
            )
            feat_row.addWidget(dot, 0, Qt.AlignTop)
            feat_row.addWidget(feat_lbl, 1)

            feat_w = QWidget()
            feat_w.setStyleSheet("background:transparent;")
            feat_w.setLayout(feat_row)
            col.addWidget(feat_w)
            col.addSpacing(4)

        col.addStretch()
        return card


# class _CreditsDialog(QDialog):
#     """
#     Hidden credits dialog — opened by clicking the bottom-right corner
#     of the About page 6 times.
#     """

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Credits")
#         self.setModal(True)
#         self.setMinimumWidth(540)
#         self.setStyleSheet(f"""
#             QDialog {{
#                 background-color: {t.BG_PAGE};
#             }}
#         """)

#         root = QVBoxLayout(self)
#         root.setContentsMargins(32, 28, 32, 28)
#         root.setSpacing(20)

#         # ── Title ─────────────────────────────────────────────────
#         title = QLabel("✦  Credits")
#         title.setStyleSheet(
#             f"color:{t.YELLOW}; font-size:18px; font-weight:700; background:transparent;"
#         )
#         root.addWidget(title)

#         sep = QFrame()
#         sep.setFrameShape(QFrame.HLine)
#         sep.setStyleSheet(f"background:{t.BORDER_FAINT};")
#         root.addWidget(sep)

#         # ── Company block ─────────────────────────────────────────
#         def _block(heading: str, lines: list[str], accent: str = t.TEXT_DIM) -> QWidget:
#             w = QWidget()
#             w.setStyleSheet("background:transparent;")
#             lay = QVBoxLayout(w)
#             lay.setContentsMargins(0, 0, 0, 0)
#             lay.setSpacing(4)
#             h = QLabel(heading.upper())
#             h.setStyleSheet(
#                 f"color:{accent}; font-size:9px; font-weight:700; "
#                 "letter-spacing:1.2px; background:transparent;"
#             )
#             lay.addWidget(h)
#             for line in lines:
#                 l = QLabel(line)
#                 l.setStyleSheet(
#                     f"color:{t.TEXT_BRIGHT}; font-size:11px; background:transparent;"
#                 )
#                 l.setWordWrap(True)
#                 lay.addWidget(l)
#             return w

#         root.addWidget(_block(
#             "Company",
#             [
#                 "Hyva Holding B.V.",
#                 "Antonie van Leeuwenhoekweg 37",
#                 "2408 AK  Alphen aan den Rijn,  Netherlands",
#                 "Province: South Holland",
#                 "Phone: +31 172 423 555",
#             ],
#             accent="#FFD100",
#         ))

#         root.addWidget(_block(
#             "Simulator Developer",
#             ["Ranjith Channabasappa"],
#             accent="#38BDF8",
#         ))

#         # ── Team ──────────────────────────────────────────────────
#         team = [
#             ("Design",                "Niels Brandhorst",         "n.brandhorst@hyva.com"),
#             ("Design & Development",  "Ranjith Channabasappa",     "r.channabasappa@hyva.com"),
#             ("Design",                "Rakshitha Krishnamurthy",   "r.krishnamurthy@hyva.com"),
#             ("Design",                "Dheeraj Jain",              "d.jain@hyva.com"),
#             ("Design",                "Charitha MC",               "charitha.mc@KNODTEC.COM"),
#         ]

#         team_w = QWidget()
#         team_w.setStyleSheet("background:transparent;")
#         team_lay = QVBoxLayout(team_w)
#         team_lay.setContentsMargins(0, 0, 0, 0)
#         team_lay.setSpacing(6)

#         hdr = QLabel("TEAM")
#         hdr.setStyleSheet(
#             f"color:{t.YELLOW}; font-size:9px; font-weight:700; "
#             "letter-spacing:1.2px; background:transparent;"
#         )
#         team_lay.addWidget(hdr)

#         for role, name, email in team:
#             row_w = QWidget()
#             row_w.setStyleSheet("background:transparent;")
#             row_lay = QHBoxLayout(row_w)
#             row_lay.setContentsMargins(0, 0, 0, 0)
#             row_lay.setSpacing(10)

#             role_lbl = QLabel(role)
#             role_lbl.setFixedWidth(110)
#             role_lbl.setStyleSheet(
#                 f"color:{t.TEXT_DIM}; font-size:10px; background:transparent;"
#             )
#             name_lbl = QLabel(name)
#             name_lbl.setFixedWidth(190)
#             name_lbl.setStyleSheet(
#                 f"color:{t.TEXT_BRIGHT}; font-size:11px; background:transparent;"
#             )
#             email_lbl = QLabel(f"<{email}>")
#             email_lbl.setStyleSheet(
#                 f"color:{t.TEXT_DIM}; font-size:10px; background:transparent;"
#             )
#             row_lay.addWidget(role_lbl)
#             row_lay.addWidget(name_lbl)
#             row_lay.addWidget(email_lbl)
#             row_lay.addStretch()
#             team_lay.addWidget(row_w)

#         root.addWidget(team_w)

#         # ── Close button ──────────────────────────────────────────
#         close_btn = QPushButton("Close")
#         close_btn.setFixedHeight(32)
#         close_btn.setCursor(Qt.PointingHandCursor)
#         close_btn.setStyleSheet(f"""
#             QPushButton {{
#                 background-color: {t.BG_SURFACE};
#                 color: {t.TEXT_BRIGHT};
#                 border: 1px solid {t.BORDER_FAINT};
#                 border-radius: 4px;
#                 font-size: 11px;
#                 padding: 0 20px;
#             }}
#             QPushButton:hover {{
#                 background-color: {t.YELLOW};
#                 color: #000000;
#             }}
#         """)
#         close_btn.clicked.connect(self.accept)
#         root.addWidget(close_btn, 0, Qt.AlignRight)

class _CreditsDialog(QDialog):
    """
    Hidden credits dialog — opened by clicking the bottom-right corner
    of the About page 6 times.

    Animation: pulsing yellow dot in the header (QTimer, 900 ms toggle).
    No other animations.

    Layout (root QVBoxLayout, no margins):
      hero   — fixed height, yellow-gradient background
      scroll — stretch=1, body with Company + Tech + Team cards
      footer — fixed 46 px, OUTSIDE scroll area, always visible

    Maximize is disabled so the footer is never pushed off screen.
    Font is set explicitly on the dialog stylesheet so Inter is used
    even though MainWindow stylesheet does not cascade into QDialog.
    """

    _TEAM = [
        ("Design",               "Niels Brandhorst",        "n.brandhorst@hyva.com"),
        ("Design & Development", "Ranjith Channabasappa",   "r.channabasappa@hyva.com"),
        ("Design & Testing",     "Rakshitha Krishnamurthy", "r.krishnamurthy@hyva.com"),
        ("Design & Testing",     "Dheeraj Jain",            "d.jain@hyva.com"),
        ("Design",               "Charitha MC",             "charitha.mc@KNODTEC.COM"),
    ]

    _TECH = [
        ("Language",   "Python 3.12"),
        ("GUI",        "PySide6  ·  Qt 6"),
        ("CAN Bus",    "python-can  ·  J1939 / TippingTCS"),
        ("Transport",  "rpyc  ·  SSH / paramiko"),
        ("Hardware",   "PCAN-USB  ·  SocketCAN  ·  Lucid IO  ·  GPIO"),
        ("Automation", "pytest  ·  Behave BDD"),
    ]

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Credits — Hyva Simulator")
        self.setModal(True)
        self.setMinimumSize(680, 520)
        self.setMaximumSize(860, 700)

        # Disable maximize — footer must always remain visible
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowMaximizeButtonHint
        )

        # Rainbow timer — cycles the dot through 7 spectrum colours
        self._rainbow_index = 0
        self._pulse_timer   = QTimer(self)
        self._pulse_timer.setInterval(600)

        # ── Stylesheet ─────────────────────────────────────────────
        # Font set explicitly here because MainWindow stylesheet does
        # NOT cascade into a top-level QDialog window.
        self.setStyleSheet(f"""
            QDialog, QWidget {{
                font-family: 'Inter', 'Liberation Sans', 'DejaVu Sans', Arial, sans-serif;
                background-color: {t.BG_PAGE};
            }}
            QLabel {{
                background-color: transparent;
                font-family: 'Inter', 'Liberation Sans', 'DejaVu Sans', Arial, sans-serif;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {t.BG_SURFACE};
                width: 5px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {t.BORDER_STRONG};
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        # ── Root layout ────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_hero())

        # Scroll area — stretches between hero and footer
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        scroll.setWidget(body)

        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 20)
        body_lay.setSpacing(16)

        cols_row = QHBoxLayout()
        cols_row.setSpacing(14)
        cols_row.setContentsMargins(0, 0, 0, 0)
        cols_row.addWidget(self._make_company_card(), 1)
        cols_row.addWidget(self._make_tech_card(),    1)
        body_lay.addLayout(cols_row)
        body_lay.addWidget(self._make_team_card())
        # No addStretch — causes scroll body to over-expand on large windows

        root.addWidget(scroll, 1)   # stretch=1 — fills space between hero and footer

        # Footer added to ROOT layout, never inside scroll
        # This guarantees it is always visible regardless of dialog height
        root.addWidget(self._build_footer())

    # ── Animation ──────────────────────────────────────────────────

    # Rainbow spectrum — 7 colours cycling through red → orange → yellow →
    # green → cyan → blue → violet.  Chosen to be vivid on a dark background.
    _RAINBOW_COLOURS = [
        "#FF3333",   # red
        "#FF8800",   # orange
        "#FFD100",   # Hyva yellow
        "#44DD44",   # green
        "#00CCCC",   # cyan
        "#3388FF",   # blue
        "#AA44FF",   # violet
    ]

    def _pulse_tick(self) -> None:
        """Advance the rainbow dot to the next spectrum colour."""
        self._rainbow_index = (self._rainbow_index + 1) % len(self._RAINBOW_COLOURS)
        color = self._RAINBOW_COLOURS[self._rainbow_index]
        self._pulse_dot.setStyleSheet(
            f"color:{color}; font-size:8px; background:transparent;"
        )

    def closeEvent(self, event: object) -> None:
        self._pulse_timer.stop()
        super().closeEvent(event)

    # ── Widget builders ────────────────────────────────────────────

    def _build_hero(self) -> QWidget:
        hero = QWidget()
        hero.setObjectName("CreditsHero")
        hero.setAttribute(Qt.WA_StyledBackground, True)
        hero.setStyleSheet(f"""
            QWidget#CreditsHero {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1A1200,
                    stop:0.6 #141400,
                    stop:1 {t.BG_PAGE}
                );
                border-bottom: 2px solid {t.YELLOW};
            }}
        """)
        lay = QHBoxLayout(hero)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(16)

        # Logo
        logo_lbl = QLabel()
        logo_path = PROJECT_ROOT / "assets" / "logo" / "hyva_logo.jpg"
        if logo_path.exists():
            px = QPixmap(str(logo_path))
            logo_lbl.setPixmap(px.scaledToHeight(40, Qt.SmoothTransformation))
        else:
            logo_lbl.setText("HYVA")
            logo_lbl.setStyleSheet(
                f"color:{t.RED}; font-size:18px; font-weight:bold;"
            )
        logo_lbl.setAlignment(Qt.AlignVCenter)
        lay.addWidget(logo_lbl)

        # Vertical divider
        vdiv = QWidget()
        vdiv.setFixedSize(1, 40)
        vdiv.setStyleSheet(f"background:{t.BORDER_STRONG};")
        lay.addWidget(vdiv)

        # Title block
        title_col = QVBoxLayout()
        title_col.setSpacing(5)
        title_col.setContentsMargins(0, 0, 0, 0)

        name_row = QHBoxLayout()
        name_row.setSpacing(10)
        name_row.setContentsMargins(0, 0, 0, 0)

        # Pulsing dot — only animation in the whole dialog
        self._pulse_dot = QLabel("●")
        self._pulse_dot.setStyleSheet(
            f"color:{t.YELLOW}; font-size:8px;"
        )
        name_row.addWidget(self._pulse_dot, 0, Qt.AlignVCenter)

        app_name = QLabel("HYVA SIMULATOR")
        app_name.setStyleSheet(
            f"color:{t.TEXT_WHITE}; font-size:16px; font-weight:700; "
            "letter-spacing:3px;"
        )
        name_row.addWidget(app_name)

        ver_badge = QLabel(f"v{APP_VERSION}")
        ver_badge.setStyleSheet(
            f"color:{t.BG_PAGE}; background:{t.YELLOW}; "
            "font-size:9px; font-weight:700; letter-spacing:1px; "
            "border-radius:3px; padding:2px 7px;"
        )
        ver_badge.setAlignment(Qt.AlignVCenter)
        name_row.addWidget(ver_badge)
        name_row.addStretch()
        title_col.addLayout(name_row)

        # Short description shown below the version badge
        description = QLabel(
            "Desktop tool for testing and validating Hyva truck tipping systems.\n"
            "Simulates sensors, J1939 CAN messages, and hardware signals so the real\n"
            "Gateway (GW) and HMI can be tested without a physical truck."
        )
        description.setWordWrap(True)
        description.setStyleSheet(
            f"color:{t.TEXT_BRIGHT}; font-size:10px; line-height:1.5;"
        )
        title_col.addWidget(description)

        dept = QLabel("System Validation  ·  Hyva Group")
        dept.setStyleSheet(
            f"color:{t.YELLOW_DIM}; font-size:9px; letter-spacing:1px;"
        )
        title_col.addWidget(dept)

        lay.addLayout(title_col)
        lay.addStretch()

        # Start pulse after dot widget is created
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_timer.start()

        return hero

    def _build_footer(self) -> QWidget:
        """
        Fixed footer in root layout — never inside the scroll area.
        Always visible at any dialog height.
        """
        footer = QWidget()
        footer.setObjectName("CreditsFooter")
        footer.setAttribute(Qt.WA_StyledBackground, True)
        footer.setFixedHeight(46)
        footer.setStyleSheet(f"""
            QWidget#CreditsFooter {{
                background-color: {t.BG_SURFACE};
                border-top: 1px solid {t.BORDER_FAINT};
            }}
        """)
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(24, 0, 20, 0)

        copy_lbl = QLabel("© 2026 Hyva Group. All rights reserved.")
        copy_lbl.setStyleSheet(
            f"color:{t.TEXT_DIM}; font-size:10px;"
        )
        lay.addWidget(copy_lbl)
        lay.addStretch()

        close_btn = QPushButton("  Close  ")
        close_btn.setFixedHeight(28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t.TEXT_BRIGHT};
                border: 1px solid {t.BORDER_STRONG};
                border-radius: 4px;
                font-size: 11px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {t.YELLOW};
                color: #000000;
                border-color: {t.YELLOW};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn)
        return footer

    @staticmethod
    def _card_shell(accent: str) -> tuple:
        """Return a styled dark card and its inner QVBoxLayout."""
        card = QWidget()
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setObjectName("CreditsCard")
        card.setStyleSheet(f"""
            QWidget#CreditsCard {{
                background-color: {t.BG_CARD};
                border: 1px solid {t.BORDER_FAINT};
                border-top: 2px solid {accent};
                border-radius: 8px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 18)
        lay.setSpacing(10)
        return card, lay

    @staticmethod
    def _section_header(text: str, accent: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            f"color:{accent}; font-size:9px; font-weight:700; "
            "letter-spacing:2px;"
        )
        return lbl

    @staticmethod
    def _divider() -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#2A2A2A; border:none; max-height:1px;")
        return div

    def _make_company_card(self) -> QWidget:
        card, lay = self._card_shell(t.YELLOW)
        lay.addWidget(self._section_header("Company", t.YELLOW))
        lay.addWidget(self._divider())
        for label, value in [
            ("Name",    "Hyva Holding B.V."),
            ("Address", "Antonie van Leeuwenhoekweg 37"),
            ("City",    "2408 AK  Alphen aan den Rijn"),
            ("Country", "Netherlands  ·  South Holland"),
            ("Phone",   "+31 172 423 555"),
            ("Project", "Hyva-Simulator"),
        ]:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            k = QLabel(label)
            k.setFixedWidth(62)
            k.setStyleSheet(
                f"color:{t.TEXT_DIM}; font-size:10px;"
            )
            v = QLabel(value)
            v.setWordWrap(True)
            v.setStyleSheet(
                f"color:{t.TEXT_BRIGHT}; font-size:11px;"
            )
            row.addWidget(k)
            row.addWidget(v, 1)
            lay.addLayout(row)
        lay.addStretch()
        return card

    def _make_tech_card(self) -> QWidget:
        card, lay = self._card_shell("#38BDF8")
        lay.addWidget(self._section_header("Tech Stack", "#38BDF8"))
        lay.addWidget(self._divider())
        for label, value in self._TECH:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            k = QLabel(label)
            k.setFixedWidth(80)
            k.setStyleSheet(
                f"color:{t.TEXT_DIM}; font-size:10px;"
            )
            v = QLabel(value)
            v.setWordWrap(True)
            v.setStyleSheet(
                f"color:{t.TEXT_BRIGHT}; font-size:11px;"
            )
            row.addWidget(k)
            row.addWidget(v, 1)
            lay.addLayout(row)
        lay.addStretch()
        return card

    def _make_team_card(self) -> QWidget:
        card, lay = self._card_shell(t.GREEN)
        lay.addWidget(self._section_header("Team", t.GREEN))
        lay.addWidget(self._divider())

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(2, 1)

        for col, text in enumerate(("ROLE", "NAME", "EMAIL")):
            h = QLabel(text)
            h.setStyleSheet(
                "color:#444444; font-size:8px; letter-spacing:1.5px;"
            )
            grid.addWidget(h, 0, col)

        hdiv = QFrame()
        hdiv.setFrameShape(QFrame.HLine)
        hdiv.setStyleSheet("background:#252525; border:none; max-height:1px;")
        grid.addWidget(hdiv, 1, 0, 1, 3)

        for i, (role, name, email) in enumerate(self._TEAM):
            row_idx = i + 2

            dot = QLabel("◆")
            dot.setFixedWidth(14)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet(
                f"color:{t.GREEN}; font-size:6px;"
            )
            role_lbl = QLabel(role)
            role_lbl.setStyleSheet(
                f"color:{t.TEXT_DIM}; font-size:10px;"
            )
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(
                f"color:{t.TEXT_BRIGHT}; font-size:11px;"
            )
            email_lbl = QLabel(email)
            email_lbl.setStyleSheet(
                f"color:{t.TEXT_DIM}; font-size:10px;"
            )

            role_row = QHBoxLayout()
            role_row.setContentsMargins(0, 0, 0, 0)
            role_row.setSpacing(4)
            role_row.addWidget(dot)
            role_row.addWidget(role_lbl)
            role_w = QWidget()
            role_w.setStyleSheet("background:transparent;")
            role_w.setLayout(role_row)

            grid.addWidget(role_w,    row_idx, 0)
            grid.addWidget(name_lbl,  row_idx, 1)
            grid.addWidget(email_lbl, row_idx, 2)

        lay.addLayout(grid)
        return card

def _about_card(
    accent_color: str,
    icon: str,
    heading: str,
    rows: "list[tuple[str, str]]",
    fa_icon: str = "",
) -> QWidget:
    """
    One info card for the About page.

    accent_color : top-border glow + icon colour
    icon         : unicode fallback symbol (when qtawesome not installed)
    fa_icon      : Font Awesome 6 icon name e.g. "fa6s.circle-info"
    heading      : card section title
    rows         : list of (label, value) tuples
    """
    card = QWidget()
    card.setObjectName("AboutInfoCard")
    card.setAttribute(Qt.WA_StyledBackground, True)
    card.setStyleSheet(f"""
        QWidget#AboutInfoCard {{
            background-color: #1A1A1A;
            border: 1px solid #2C2C2C;
            border-top: 2px solid {accent_color};
            border-radius: 8px;
        }}
    """)

    col = QVBoxLayout(card)
    col.setContentsMargins(20, 18, 20, 20)
    col.setSpacing(0)

    head_row = QHBoxLayout()
    head_row.setSpacing(10)
    head_row.setContentsMargins(0, 0, 0, 0)

    icon_lbl = IconWidget(fa=fa_icon or "fa6s.circle", fallback=icon,
                          colour=accent_color, size=18)
    icon_lbl.setFixedWidth(28)
    head_row.addWidget(icon_lbl)

    head_lbl = QLabel(heading.upper())
    head_lbl.setStyleSheet(
        f"color: {accent_color}; font-size: 12px; "
        f"letter-spacing: 3px; font-weight: bold; background: transparent;"
    )
    head_row.addWidget(head_lbl)
    head_row.addStretch()
    col.addLayout(head_row)
    col.addSpacing(14)

    div = QFrame()
    div.setFrameShape(QFrame.HLine)
    div.setStyleSheet("color: #2A2A2A;")
    col.addWidget(div)
    col.addSpacing(14)

    for label, value in rows:
        row_w = QWidget()
        row_w.setStyleSheet("background: transparent;")
        row_layout = QVBoxLayout(row_w)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(2)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            "color: #888888; font-size: 9px; "
            "letter-spacing: 2px; background: transparent;"
        )
        row_layout.addWidget(lbl)

        val = QLabel(value)
        val.setWordWrap(True)
        val.setStyleSheet("color: #F2F2F2; font-size: 13px; background: transparent;")
        row_layout.addWidget(val)

        col.addWidget(row_w)
        col.addSpacing(10)

    col.addStretch()
    return card


class AboutPage(QWidget):
    """
    About page — three info cards.

    Easter egg
    ----------
    Click the Hyva logo in the top header 6 consecutive times within
    2 seconds between each click to open the Credits dialog.
    The logo counter is managed in TopHeader; it calls
    ``AboutPage.open_credits()`` via a direct slot connection.
    No visible trigger exists on this page.
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        root.addWidget(PageTitleBar("ABOUT"))
        root.addSpacing(24)

        # ── Three info cards side by side ─────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        cards_row.setContentsMargins(0, 0, 0, 0)

        cards_row.addWidget(_about_card(
            accent_color = "#FFD100",
            icon         = "◈",
            fa_icon      = "fa6s.desktop",
            heading      = "Application",
            rows         = [
                ("Name",    "Hyva Simulator"),
                ("Version", APP_VERSION),
                ("Team",    "System Validation — Hyva"),
            ],
        ))

        cards_row.addWidget(_about_card(
            accent_color = "#38BDF8",
            icon         = "⬡",
            fa_icon      = "fa6s.laptop-code",
            heading      = "Platform",
            rows         = [
                ("Supported OS",       "Windows 10/11  ·  Linux  ·  Raspberry Pi"),
                ("Platform Detection", "Auto-detected at startup"),
                ("CAN Interface",      "PCAN-USB  ·  SocketCAN  ·  CAN HAT"),
            ],
        ))

        cards_row.addWidget(_about_card(
            accent_color = "#4ADE80",
            icon         = "⚖",
            fa_icon      = "fa6s.scale-balanced",
            heading      = "Legal",
            rows         = [
                ("Copyright", "© 2026 Hyva Group. All rights reserved."),
                ("License",   "Internal use only — not for distribution"),
            ],
        ))

        root.addLayout(cards_row)
        root.addStretch()

    def open_credits(self) -> None:
        """Open the hidden Credits dialog. Called by TopHeader on 6-click easter egg."""
        logger.info("[ABOUT] Credits opened")
        _CreditsDialog(self).exec()


class _GeneralSettingsPage(_SettingsSubPage):
    """General settings sub-page (placeholder — extend in future)."""

    def __init__(self, profile: "PlatformProfile | None" = None, parent: "QWidget | None" = None) -> None:
        super().__init__(profile, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(12)

        # Header row: page title pill left, back button right.
        # show_separator=False: the internal HSep inside PageTitleBar is
        # suppressed.  The external root.addWidget(HSep()) below provides a
        # single full-width separator spanning the entire row width.
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(8)
        hdr_row.addWidget(PageTitleBar("GENERAL SETTINGS", show_separator=False))
        hdr_row.addStretch()
        hdr_row.addWidget(self._back_button())
        root.addLayout(hdr_row)
        root.addWidget(HSep())    # full-width separator spanning entire row
        root.addStretch()

        lbl = QLabel("General settings — coming soon.")
        lbl.setStyleSheet(f"color:{t.TEXT_DIM}; font-size:13px;")
        lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(lbl)
        root.addStretch()


class _WindowsSettingsPage(_SettingsSubPage):
    """Windows-specific settings sub-page."""

    def __init__(self, profile: "PlatformProfile | None" = None, parent: "QWidget | None" = None) -> None:
        super().__init__(profile, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(12)

        # Header row: page title pill left, back button right.
        # show_separator=False: suppresses the internal HSep in PageTitleBar.
        # The external HSep below provides a single full-width separator.
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(8)
        hdr_row.addWidget(PageTitleBar("WINDOWS SETTINGS", show_separator=False))
        # Strip: auto-detected version (e.g. "WINDOWS 11") or generic "WINDOWS"
        hdr_row.addWidget(self._build_windows_strip())
        hdr_row.addStretch()
        hdr_row.addWidget(self._back_button())
        root.addLayout(hdr_row)
        root.addWidget(HSep())    # full-width separator spanning entire row
        root.addStretch()

        lbl = QLabel("Windows settings — coming soon.")
        lbl.setStyleSheet(f"color:{t.TEXT_DIM}; font-size:13px;")
        lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(lbl)
        root.addStretch()

    def _is_windows(self) -> bool:
        """Return True when the detected platform is Windows."""
        if self._profile is None:
            return False
        from simulator.platform.platform_detector import OperatingSystem
        return self._profile.operating_system == OperatingSystem.WINDOWS

    def _build_windows_strip(self) -> QWidget:
        """
        Platform strip for the Windows page.
        Auto-sizes to its content (no stretch) — matches PageTitleBar pill width behaviour.
        Shows auto-detected Windows version when on Windows (e.g. "WINDOWS 11");
        shows generic "WINDOWS" fallback on any other OS.
        """
        strip = QWidget()
        strip.setObjectName("PlatformStrip")
        strip.setAttribute(Qt.WA_StyledBackground, True)
        strip.setFixedHeight(36)
        strip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        strip.setStyleSheet(f"""
            QWidget#PlatformStrip {{
                background-color: {self._CARD};
                border: 1px solid {self._BDR};
                border-left: 3px solid {self._ACC};
                border-radius: 8px;
            }}
        """)
        row = QHBoxLayout(strip)
        row.setContentsMargins(12, 0, 16, 0)
        row.setSpacing(8)

        row.addWidget(IconWidget(fa="fa6s.display", fallback="▣", colour=self._ACC, size=13))

        if self._is_windows() and self._profile:
            # Auto-detected Windows — show full label (e.g. "WINDOWS 11")
            display = self._profile.display_label
        else:
            # Not on Windows — show generic fallback
            display = "WINDOWS"

        name_lbl = QLabel(display)
        name_lbl.setObjectName("PanelTitle")
        row.addWidget(name_lbl, 0, Qt.AlignVCenter)
        return strip


class _LinuxSettingsPage(_SettingsSubPage):
    """Linux-specific settings sub-page."""

    def __init__(self, profile: "PlatformProfile | None" = None, parent: "QWidget | None" = None) -> None:
        super().__init__(profile, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(12)

        # Header row: page title pill left, back button right.
        # show_separator=False: suppresses the internal HSep in PageTitleBar.
        # The external HSep below provides a single full-width separator.
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(8)
        hdr_row.addWidget(PageTitleBar("LINUX SETTINGS", show_separator=False))
        # Strip: auto-detected distro + channel (e.g. "UBUNTU 22.04") or "LINUX"
        hdr_row.addWidget(self._build_linux_strip())
        hdr_row.addStretch()
        hdr_row.addWidget(self._back_button())
        root.addLayout(hdr_row)
        root.addWidget(HSep())    # full-width separator spanning entire row
        root.addStretch()

        lbl = QLabel("Linux settings — coming soon.")
        lbl.setStyleSheet(f"color:{t.TEXT_DIM}; font-size:13px;")
        lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(lbl)
        root.addStretch()

    def _is_linux(self) -> bool:
        """Return True when the detected platform is Linux (not Pi, not Windows)."""
        if self._profile is None:
            return False
        from simulator.platform.platform_detector import OperatingSystem
        return self._profile.operating_system == OperatingSystem.LINUX

    def _build_linux_strip(self) -> QWidget:
        """
        Platform strip for the Linux page.
        Auto-sizes to content (no stretch).
        Shows auto-detected distro + SocketCAN channel when on Linux;
        shows generic "LINUX" label on any other OS.
        """
        strip = QWidget()
        strip.setObjectName("PlatformStrip")
        strip.setAttribute(Qt.WA_StyledBackground, True)
        strip.setFixedHeight(36)
        strip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        strip.setStyleSheet(f"""
            QWidget#PlatformStrip {{
                background-color: {self._CARD};
                border: 1px solid {self._BDR};
                border-left: 3px solid {self._ACC};
                border-radius: 8px;
            }}
        """)
        row = QHBoxLayout(strip)
        row.setContentsMargins(12, 0, 16, 0)
        row.setSpacing(8)

        row.addWidget(IconWidget(fa="fa6s.terminal", fallback=">", colour=self._ACC, size=13))

        if self._is_linux() and self._profile:
            # Auto-detected Linux — show distro name (e.g. "UBUNTU 22.04")
            display = self._profile.display_label
            name_lbl = QLabel(display)
            name_lbl.setObjectName("PanelTitle")
            row.addWidget(name_lbl, 0, Qt.AlignVCenter)

            row.addWidget(self._vdiv())

            channel_lbl = QLabel(self._profile.can_channel)
            channel_lbl.setStyleSheet(
                f"color:{self._DIM}; font-size:10px; "
                "font-family:monospace; background:transparent;"
            )
            row.addWidget(channel_lbl, 0, Qt.AlignVCenter)
        else:
            # Not on Linux — show generic fallback label only
            name_lbl = QLabel("LINUX")
            name_lbl.setObjectName("PanelTitle")
            row.addWidget(name_lbl, 0, Qt.AlignVCenter)

        return strip

class SettingsLandingPage(QWidget):
    """
    Settings root — 4 category cards.
    Emits setting_requested(key) when a card is clicked.
    """

    setting_requested = Signal(str)

    _CARDS = [
        ("general", "GENERAL",      "fa6s.gear",     "⚙", "#FFD100",
         "Logging, themes, startup behaviour"),
        ("windows", "WINDOWS",      "fa6s.display",  "▣", "#38BDF8",
         "PCAN adapter · CAN bus configuration"),
        ("linux",   "LINUX",        "fa6s.terminal", ">", "#4ADE80",
         "SocketCAN · network interfaces"),
        ("raspi",   "RASPBERRY PI", "fa6s.microchip","⬡", "#F97316",
         "GPIO pins · K15 relay · gpiod"),
    ]

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(16)

        root.addWidget(PageTitleBar("SETTINGS"))

        intro = QLabel("Platform-specific and general simulator configuration.")
        intro.setStyleSheet(f"color:{t.TEXT_DIM}; font-size:11px;")
        root.addWidget(intro)

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 0, 0)

        for i, (key, name, fa_icon, fallback, accent, desc) in enumerate(self._CARDS):
            row, col = divmod(i, 2)
            grid.addWidget(self._make_card(key, name, fa_icon, fallback, accent, desc), row, col)

        root.addLayout(grid)
        root.addStretch()

    def _make_card(
        self, key: str, name: str, fa_icon: str,
        fallback: str, accent: str, desc: str,
    ) -> QWidget:
        card = QWidget()
        card.setObjectName("SettingCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setCursor(Qt.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setFixedHeight(90)
        card.setStyleSheet(f"""
            QWidget#SettingCard {{
                background-color: #1A1A1A;
                border: 1px solid #2C2C2C;
                border-top: 3px solid {accent};
                border-radius: 6px;
            }}
            QWidget#SettingCard:hover {{
                background-color: #222222;
                border: 1px solid {accent};
                border-top: 3px solid {accent};
            }}
        """)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(5)
        lay.setAlignment(Qt.AlignVCenter)

        head_row = QHBoxLayout()
        head_row.setSpacing(10)
        head_row.setContentsMargins(0, 0, 0, 0)
        head_row.addWidget(IconWidget(fa=fa_icon, fallback=fallback, colour=accent, size=15))

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color:{accent}; font-size:13px; font-weight:700; "
            "letter-spacing:0.5px; background:transparent;"
        )
        head_row.addWidget(name_lbl)
        head_row.addStretch()
        lay.addLayout(head_row)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(
            f"color:{t.TEXT_DIM}; font-size:10px; background:transparent;"
        )
        lay.addWidget(desc_lbl)

        _key = key

        class _ClickOverlay(QLabel):
            def mousePressEvent(overlay_self, event: object) -> None:
                if event.button() == Qt.LeftButton:
                    self.setting_requested.emit(_key)
                super().mousePressEvent(event)

        overlay = _ClickOverlay("", card)
        overlay.setGeometry(0, 0, card.width(), card.height())
        overlay.setStyleSheet("background:transparent;")

        def _on_resize(event: object, _o: QLabel = overlay, _c: QWidget = card) -> None:
            _o.setGeometry(0, 0, _c.width(), _c.height())
            QWidget.resizeEvent(_c, event)

        card.resizeEvent = _on_resize
        return card

# ══════════════════════════════════════════════════════════════════
# GOODBYE SCREEN  — animated shutdown splash
# ══════════════════════════════════════════════════════════════════

