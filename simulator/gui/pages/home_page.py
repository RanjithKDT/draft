from __future__ import annotations

import subprocess
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QSizePolicy, QFrame, QPushButton,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
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


class _PingWorker(QThread):
    """
    Background thread: pings GW (172.16.0.1) every 2 s.
    Emits ping_ok on first success.
    Emits ping_timeout after max_seconds without success.
    Call stop() to cancel early (e.g. user hits IGN OFF while pending).
    """
    GW_IP       = "172.16.0.1"
    INTERVAL    = 2.0    # seconds between attempts
    MAX_SECONDS = 180.0  # 3 minutes

    ping_ok      = Signal()
    ping_timeout = Signal()

    def __init__(self, parent: "QThread | None" = None) -> None:
        super().__init__(parent)
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        import time
        elapsed = 0.0
        attempt = 0
        logger.info(f"[PING] Starting ping loop → {self.GW_IP} (max {self.MAX_SECONDS:.0f}s)")
        while not self._stop and elapsed < self.MAX_SECONDS:
            attempt += 1
            logger.debug(f"[PING] Attempt #{attempt} ({elapsed:.0f}s elapsed) → {self.GW_IP}")
            if self._ping_once():
                logger.info(f"[PING]  Reachable on attempt #{attempt} ({elapsed:.0f}s)")
                if not self._stop:
                    self.ping_ok.emit()
                return
            else:
                logger.debug(f"[PING] No response — retrying in {self.INTERVAL:.0f}s")
            time.sleep(self.INTERVAL)
            elapsed += self.INTERVAL
        if not self._stop:
            logger.warning(f"[PING] Timeout — {self.GW_IP} unreachable after {attempt} attempts")
            self.ping_timeout.emit()
        else:
            logger.info(f"[PING] Cancelled after {attempt} attempts")

    def _ping_once(self) -> bool:
        try:
            # Cross-platform: Windows uses -n/-w, POSIX uses -c/-W
            if sys.platform == "win32":
                cmd = ["ping", "-n", "1", "-w", "1000", self.GW_IP]
            else:
                cmd = ["ping", "-c", "1", "-W", "1", self.GW_IP]
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            return result.returncode == 0
        except Exception:
            return False


class _FetchWorker(QThread):
    """
    Background thread: SSH into GW, read fota properties, emit result.
    Never touches the GUI directly — emits signals only.

    Pass is_windows=True/False from the PlatformProfile so key file
    selection is authoritative rather than relying on sys.platform.
    """
    succeeded = Signal(object)   # DeviceInfo
    failed    = Signal(str)      # error message

    def __init__(self, is_windows: bool | None = None, parent: "QThread | None" = None) -> None:
        super().__init__(parent)
        self._is_windows = is_windows

    def run(self) -> None:
        try:
            from simulator.ssh.gw_client import fetch_device_info
            info = fetch_device_info(is_windows=self._is_windows)
            self.succeeded.emit(info)
        except Exception as ex:
            self.failed.emit(str(ex))


class _DeviceRow(QWidget):
    """
    One labelled info cell used in the device details horizontal strip.
    Layout (vertical): LABEL on top, value below — placed side by side with others.
    """
    def __init__(self, label: str, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            "color: #666666; font-size: 8px; letter-spacing: 2px; background: transparent;"
        )
        col.addWidget(lbl)

        self._val = QLabel("—")
        self._val.setStyleSheet(
            "color: #F2F2F2; font-size: 12px; background: transparent;"
        )
        col.addWidget(self._val)

    def set_value(self, text: str, ok: bool = True) -> None:
        self._val.setText(text)
        self._val.setStyleSheet(
            f"color: {'#F2F2F2' if ok else t.RED}; "
            f"font-size: 12px; background: transparent;"
        )


# PageTitleBar imported from simulator.gui.components
# — see components.py for the full implementation

class _ProductPage(QWidget):
    """
    Generic product detail page — navigated from HomePage cards.
    Shows the product name with Hyva colour accent and a back button.
    Content can be extended per product in future steps.
    """

    def __init__(self, product_name: str, accent: str, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._product_name = product_name
        self._accent       = accent

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(12)

        # ── Title bar + back button aligned RIGHT ─────────────────
        # Pattern: same as CAN Tools page (PageTitleBar left, btn right).
        # show_separator=False: suppress internal HSep; add full-width
        # HSep below the row so separator spans pill AND back button.
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)
        header_row.addWidget(
            PageTitleBar(product_name, show_separator=False),
            stretch=1,
        )

        back_btn = QPushButton("← Back to Home")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedHeight(26)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t.TEXT_DIM};
                border: 1px solid {t.BORDER_STRONG};
                border-radius: 13px;
                font-size: 10px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                color: {t.RED};
                border-color: {t.RED};
                background-color: #1A0000;
            }}
        """)
        back_btn.clicked.connect(self._go_home)
        header_row.addWidget(back_btn, stretch=0, alignment=Qt.AlignVCenter)

        root.addLayout(header_row)
        # Full-width separator — spans the title pill AND the back button.
        root.addWidget(HSep())
        root.addStretch()

        placeholder = QLabel(f"{product_name} — details coming soon.")
        placeholder.setStyleSheet(
            f"color:{t.TEXT_DIM}; font-size:13px;"
        )
        placeholder.setAlignment(Qt.AlignCenter)
        root.addWidget(placeholder)
        root.addStretch()

    # Signal-free back navigation: walk up to QStackedWidget parent.
    def _go_home(self) -> None:
        w = self.parent()
        while w is not None:
            if hasattr(w, "_switch_page"):
                w._switch_page(0)
                return
            w = w.parent() if hasattr(w, "parent") else None


class HomePage(QWidget):
    """
    Page 0 — Home.

    Top: ignition button.
    Middle: four Hyva product cards (GUIDE / CONTROL / TIP BY WIRE / EPTO).
    Bottom: Device Details card.

    Clicking a product card emits product_requested(name) which MainWindow
    uses to switch to the corresponding product sub-page.
    """

    product_requested = Signal(str)   # emitted with product name on card click

    # Maps J1939 source address → footer node_id for OBU-tracked CAN nodes.
    # Kept here (not at module level) because only HomePage.update_node_status uses it.
    # GW  (0x02) and HMI (0x03) are included so CAN heartbeats update their pills
    # alongside the TCP-level check from ConnectionMonitor — providing both
    # network-level (TCP) and application-level (CAN heartbeat) status.
    _SA_TO_NODE_ID: dict[int, str] = {
        0x01: "trailer_ctrl",
        0x02: "gw",
        0x03: "hmi",
        0x04: "truck_ctrl",
    }

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._worker: _FetchWorker | None = None
        self._profile = None   # injected by MainWindow.set_profile() after construction

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(0)

        root.addWidget(PageTitleBar("HOME"))
        root.addSpacing(16)

        # ── Ignition section ──────────────────────────────────────
        self._ign_on      = False
        self._ign_pending = False
        self._ping_worker = None

        ign_section = QHBoxLayout()
        ign_section.setContentsMargins(0, 0, 0, 0)
        ign_section.setSpacing(16)

        BTN_SIZE = 80
        self._btn_ign = QPushButton()
        self._btn_ign.setFixedSize(BTN_SIZE, BTN_SIZE)
        self._btn_ign.setCursor(Qt.PointingHandCursor)
        self._btn_ign.clicked.connect(self._on_ign_clicked)
        ign_section.addWidget(self._btn_ign, 0, Qt.AlignVCenter)
        ign_section.addStretch()

        root.addLayout(ign_section)
        root.addSpacing(20)

        self._refresh_ign_ui()

        # ── Product cards row ─────────────────────────────────────
        # Four cards in one horizontal row, equal width, clickable.
        # Hyva palette: all four cards use yellow — red carries a warning
        # connotation that does not apply to product names.
        _PRODUCTS = [
            ("GUIDE",       "#FFD100"),
            ("CONTROL",     "#FFD100"),
            ("TIP BY WIRE", "#FFD100"),
            ("EPTO",        "#FFD100"),
        ]

        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 0, 0, 0)
        cards_row.setSpacing(10)

        for name, accent in _PRODUCTS:
            card = self._make_product_card(name, accent)
            cards_row.addWidget(card)

        root.addLayout(cards_row)
        root.addSpacing(16)

        root.addStretch()

        # ── Device Details card ───────────────────────────────────
        card = QWidget()
        card.setObjectName("DeviceCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            QWidget#DeviceCard {{
                background-color: #1A1A1A;
                border: 1px solid #2C2C2C;
                border-top: 2px solid {t.YELLOW};
                border-radius: 8px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(0)

        # ── Header row ────────────────────────────────────────────
        head_row = QHBoxLayout()
        head_row.setSpacing(8)
        head_row.setContentsMargins(0, 0, 0, 0)

        head_icon = IconWidget(fa="fa6s.server", fallback="⬡", colour=t.YELLOW, size=13)
        head_row.addWidget(head_icon)

        head_lbl = QLabel("DEVICE DETAILS")
        head_lbl.setStyleSheet(
            f"color:{t.YELLOW}; font-size:11px; "
            f"letter-spacing:3px; font-weight:bold; background:transparent;"
        )
        head_row.addWidget(head_lbl)
        head_row.addStretch()

        self._status_dot = IconWidget(fa="fa6s.circle", fallback="●", colour="#333333", size=9)
        head_row.addWidget(self._status_dot)

        self._status_lbl = QLabel("Not fetched")
        self._status_lbl.setStyleSheet(
            "color:#444444; font-size:10px; letter-spacing:1px; background:transparent;"
        )
        head_row.addWidget(self._status_lbl)

        card_layout.addLayout(head_row)
        card_layout.addSpacing(6)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color:#2A2A2A;")
        card_layout.addWidget(div)
        card_layout.addSpacing(8)

        # ── Compact 2-column label/value grid ─────────────────────
        # Labels left (fixed width), values right (expand).
        # Grid grows/shrinks with the text — no fixed heights anywhere.
        LABEL_SS = (
            "color:#555555; font-size:9px; letter-spacing:1px; "
            "background:transparent; padding-right:6px;"
        )
        VALUE_SS = (
            "color:#E0E0E0; font-size:11px; background:transparent;"
            " font-family:'Liberation Mono','DejaVu Sans Mono',Consolas,monospace;"
        )

        info_grid = QGridLayout()
        info_grid.setContentsMargins(0, 0, 0, 0)
        info_grid.setHorizontalSpacing(8)
        info_grid.setVerticalSpacing(5)
        info_grid.setColumnStretch(1, 1)   # value column expands
        info_grid.setColumnStretch(3, 1)
        info_grid.setColumnMinimumWidth(2, 16)  # gap between the two pairs

        fields = [
            ("GW",          "GW"),
            ("HMI",         "HMI"),
            ("Release",     "RELEASE"),
            ("Original GW", "ORIGINAL GW"),
        ]
        self._device_vals: dict[str, QLabel] = {}

        for i, (key, display) in enumerate(fields):
            row_i, col_pair = divmod(i, 2)
            col_base = col_pair * 3   # 0,1  or  3,4  (with gap col 2)

            lbl_w = QLabel(display)
            lbl_w.setStyleSheet(LABEL_SS)

            val_w = QLabel("—")
            val_w.setStyleSheet(VALUE_SS)
            val_w.setTextInteractionFlags(Qt.TextSelectableByMouse)

            info_grid.addWidget(lbl_w, row_i, col_base,     Qt.AlignVCenter)
            info_grid.addWidget(val_w, row_i, col_base + 1, Qt.AlignVCenter)
            self._device_vals[key] = val_w

        # Back-compat: keep old names so existing set_value() calls still work
        self._row_gw      = type("_Compat", (), {
            "set_value": lambda s, t, ok=True: self._set_device_val("GW", t, ok)})()
        self._row_hmi     = type("_Compat", (), {
            "set_value": lambda s, t, ok=True: self._set_device_val("HMI", t, ok)})()
        self._row_release = type("_Compat", (), {
            "set_value": lambda s, t, ok=True: self._set_device_val("Release", t, ok)})()
        self._row_orig_gw = type("_Compat", (), {
            "set_value": lambda s, t, ok=True: self._set_device_val("Original GW", t, ok)})()

        card_layout.addLayout(info_grid)
        card_layout.addSpacing(8)

        # ── Fetch button — slim ───────────────────────────────────
        self._btn = QPushButton("FETCH DEVICE DETAILS")
        self._btn.setObjectName("FetchBtn")
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setFixedHeight(26)
        self._btn.clicked.connect(self._on_fetch)
        card_layout.addWidget(self._btn)

        root.addWidget(card)

    # ── Product card builder ──────────────────────────────────────

    def _make_product_card(self, name: str, accent: str) -> QWidget:
        """
        Build one clickable product card with Hyva colour accents.
        No icons — just clean text on a dark card.
        Hovering brightens the border; clicking emits product_requested.
        """
        card = QWidget()
        card.setObjectName("ProductCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setCursor(Qt.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setFixedHeight(72)
        card.setStyleSheet(f"""
            QWidget#ProductCard {{
                background-color: #1A1A1A;
                border: 1px solid #2C2C2C;
                border-top: 3px solid {accent};
                border-radius: 6px;
            }}
            QWidget#ProductCard:hover {{
                background-color: #222222;
                border: 1px solid {accent};
                border-top: 3px solid {accent};
            }}
        """)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(3)
        lay.setAlignment(Qt.AlignVCenter)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color:{accent}; font-size:13px; font-weight:700; "
            "letter-spacing:0.5px; background:transparent;"
        )
        name_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        tap_lbl = QLabel("tap to open →")
        tap_lbl.setStyleSheet(
            f"color:{t.TEXT_DIM}; font-size:9px; background:transparent;"
        )

        lay.addWidget(name_lbl)
        lay.addWidget(tap_lbl)

        # Capture clicks via mousePressEvent override on an inner label
        # that fills the card — more reliable than eventFilter on Windows.
        _name = name  # capture for lambda

        class _ClickCatcher(QLabel):
            def mousePressEvent(catcher_self, event: object) -> None:
                if event.button() == Qt.LeftButton:
                    self.product_requested.emit(_name)
                super().mousePressEvent(event)

        overlay = _ClickCatcher("", card)
        overlay.setGeometry(0, 0, card.width(), card.height())
        overlay.setStyleSheet("background:transparent;")

        # Resize overlay when card resizes
        def _on_card_resize(event: object, _o: QLabel = overlay, _c: QWidget = card) -> None:
            _o.setGeometry(0, 0, _c.width(), _c.height())
            QWidget.resizeEvent(_c, event)

        card.resizeEvent = _on_card_resize

        return card

    # ── Fetch logic ───────────────────────────────────────────────

    def _set_device_val(self, key: str, text: str, ok: bool = True) -> None:
        """Update a value label in the compact device grid."""
        lbl = self._device_vals.get(key)
        if lbl:
            lbl.setText(text)
            lbl.setStyleSheet(
                f"color:{'#E0E0E0' if ok else t.RED}; font-size:11px;"
                " background:transparent;"
                " font-family:'Liberation Mono','DejaVu Sans Mono',Consolas,monospace;"
            )


    # ── Node status card ──────────────────────────────────────────
    def _build_node_status_card(self) -> QWidget:
        """
        Auto-managed node status display.
        The bridge monitors the CAN bus and detects which nodes are present.
        Absent nodes are faked automatically — this card just shows the status.
        Green = node detected on bus.  Red = node absent, simulator faking it.
        """
        from simulator.obu.obu_bridge import NODE_DEFS

        card = QWidget()
        card.setObjectName("NodeCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet("""
            QWidget#NodeCard {
                background-color: #1A1A1A;
                border: 1px solid #2C2C2C;
                border-top: 2px solid #A38600;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        ic = IconWidget(fa="fa6s.network-wired", fallback="⬡", colour="#A38600", size=14)
        hdr.addWidget(ic)
        tl = QLabel("CAN NODES")
        tl.setStyleSheet("color:#A38600; font-size:12px; letter-spacing:3px; font-weight:bold;")
        hdr.addWidget(tl)
        hdr.addStretch()
        layout.addLayout(hdr)

        hint = QLabel("Auto-detected. Absent nodes are  simulated by the bridge.")
        hint.setStyleSheet("color:#444444; font-size:10px; line-height:1.5;")
        layout.addWidget(hint)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color:#2A2A2A;")
        layout.addWidget(div)

        self._node_status_rows: dict[int, tuple[QLabel, QLabel]] = {}

        for sa, name in NODE_DEFS:
            row = QHBoxLayout()
            row.setSpacing(8)

            dot = IconWidget(fa="fa6s.circle-dot", fallback="●", colour="#333333", size=10)
            dot.setFixedWidth(14)

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("color:#666666; font-size:11px;")

            addr_lbl = QLabel(f"SA=0x{sa:02X}")
            addr_lbl.setStyleSheet("color:#333333; font-size:10px;")
            addr_lbl.setAlignment(Qt.AlignRight)

            status_lbl = QLabel("WAITING")
            status_lbl.setFixedWidth(80)
            status_lbl.setAlignment(Qt.AlignRight)
            status_lbl.setStyleSheet(
                "color:#333333; font-size:10px; letter-spacing:1px;"
            )

            row.addWidget(dot)
            row.addWidget(name_lbl)
            row.addStretch()
            row.addWidget(addr_lbl)
            row.addWidget(status_lbl)

            self._node_status_rows[sa] = (dot, status_lbl, name_lbl)
            layout.addLayout(row)

        layout.addStretch()

        return card

    # signal so MainWindow can forward to footer
    node_state_changed = Signal(str, str)   # (node_id, 'present'|'simulated'|'disconnected')

    def update_node_status(self, status: dict) -> None:
        """Called when bridge emits node_status_changed. Routes states to footer pills."""
        for sa, present in status.items():
            node_id = self._SA_TO_NODE_ID.get(sa)
            if node_id is None:
                continue
            state = "present" if present else "simulated"
            self.node_state_changed.emit(node_id, state)


    # ── Ignition helpers ──────────────────────────────────────────

    def set_obu_bridge(self, bridge: "ObuBridge | None") -> None:
        """Called by MainWindow to inject the OBU Bridge."""
        self._obu_bridge = bridge
        if bridge:
            bridge.node_status_changed.connect(self.update_node_status)

    def set_ign_controller(self, controller: "IgnitionController | None") -> None:
        """Called by MainWindow to inject the platform-aware controller."""
        self._ign_ctrl = controller

    def set_profile(self, profile) -> None:
        """
        Called by MainWindow to inject the PlatformProfile.
        Stored so _on_fetch can pass the correct is_windows flag to the SSH client.
        """
        self._profile = profile

    def _on_ign_clicked(self) -> None:
        """
        Single entry point for the IGN button.
        - If OFF → try to turn ON (start ping loop)
        - If PENDING (blinking) → cancel immediately → go to OFF
        - If ON → turn OFF
        """
        if self._ign_pending:
            logger.info("[IGN] User cancelled IGN-ON during ping — reverting to OFF")
            self._set_ign(False)
        elif self._ign_on:
            logger.info("[IGN] User pressed IGN OFF")
            self._set_ign(False)
        else:
            logger.info("[IGN] User pressed IGN ON")
            self._set_ign(True)

    def _set_ign(self, on: bool) -> None:
        if on:
            logger.info("[IGN] ── IGN ON requested ──────────────────────────")
            self._ign_on      = False
            self._ign_pending = True
            # Button stays ENABLED so user can cancel by pressing again
            self._btn_ign.setEnabled(True)

            # Fire the hardware relay first
            if hasattr(self, "_ign_ctrl") and self._ign_ctrl:
                logger.info("[IGN] Sending relay ON via controller")
                ok = self._ign_ctrl.set_ignition(True)
                if ok:
                    logger.info("[IGN] Relay command accepted")
                else:
                    logger.warning("[IGN] Relay command returned failure — continuing anyway")
            else:
                logger.info("[IGN] No hardware controller — software-only mode")

            # Start blinking green while waiting for GW to come up
            logger.info("[IGN] Starting blink — waiting for GW ping at 172.16.0.1")
            self._start_ign_blink()

            # Kick off ping worker
            self._ping_worker = _PingWorker(self)
            self._ping_worker.ping_ok.connect(self._on_ign_confirmed)
            self._ping_worker.ping_timeout.connect(self._on_ign_timeout)
            self._ping_worker.start()
            logger.info("[IGN] Ping worker started (timeout: 3 min, interval: 2 s)")

        else:
            logger.info("[IGN] ── IGN OFF requested ─────────────────────────")

            # Cancel any running ping worker
            if hasattr(self, "_ping_worker") and self._ping_worker:
                logger.info("[IGN] Stopping ping worker")
                self._ping_worker.stop()
                self._ping_worker = None
            else:
                logger.debug("[IGN] No ping worker running")

            self._ign_on      = False
            self._ign_pending = False
            self._stop_ign_blink()
            self._refresh_ign_ui()
            self._btn_ign.setEnabled(True)

            if hasattr(self, "_ign_ctrl") and self._ign_ctrl:
                logger.info("[IGN] Sending relay OFF via controller")
                self._ign_ctrl.set_ignition(False)
            else:
                logger.info("[IGN] No hardware controller — IGN OFF (visual only)")

            if hasattr(self, "_obu_bridge") and self._obu_bridge:
                if self._obu_bridge.isRunning():
                    logger.info("[IGN] Broadcasting IGNITION_OFF state before stopping bridge")
                    self._obu_bridge.broadcast_ignition_off()
                    logger.info("[IGN] Stopping OBU bridge")
                    self._obu_bridge.stop_bridge()
                else:
                    logger.debug("[IGN] OBU bridge was not running")
            logger.info("[IGN] IGN is now OFF")

    def _on_ign_confirmed(self) -> None:
        """GW ping succeeded — confirm IGN ON."""
        logger.info("[IGN]  GW ping succeeded at 172.16.0.1 — IGN confirmed ON")
        self._ping_worker = None
        self._stop_ign_blink()
        self._ign_pending = False
        self._ign_on      = True
        self._refresh_ign_ui()
        self._btn_ign.setEnabled(True)
        if hasattr(self, "_obu_bridge") and self._obu_bridge:
            if not self._obu_bridge.isRunning():
                logger.info("[IGN] Starting OBU bridge")
                self._obu_bridge.start()
            else:
                logger.debug("[IGN] OBU bridge already running")
        logger.info("[IGN] IGN is now ON (confirmed)")

    def _on_ign_timeout(self) -> None:
        """3 minutes elapsed, GW never responded — revert to OFF."""
        logger.warning("[IGN] ✗ GW ping timeout after 3 min — 172.16.0.1 unreachable")
        logger.warning("[IGN] Reverting to IGN OFF — check GW network connection")
        self._ping_worker = None
        self._stop_ign_blink()
        self._ign_pending = False
        self._ign_on      = False
        self._refresh_ign_ui()
        self._btn_ign.setEnabled(True)
        # Revert the hardware relay
        if hasattr(self, "_ign_ctrl") and self._ign_ctrl:
            logger.info("[IGN] Sending relay OFF (timeout revert)")
            self._ign_ctrl.set_ignition(False)
        else:
            logger.info("[IGN] No controller to revert")

    def _start_ign_blink(self) -> None:
        if not hasattr(self, "_blink_timer"):
            self._blink_timer = QTimer(self)
            self._blink_timer.setInterval(350)
            self._blink_state = False
            self._blink_timer.timeout.connect(self._blink_tick)
        self._blink_state = False
        self._blink_tick()
        self._blink_timer.start()

    def _stop_ign_blink(self) -> None:
        if hasattr(self, "_blink_timer"):
            self._blink_timer.stop()

    def _blink_tick(self) -> None:
        R = 40
        self._blink_state = not self._blink_state
        if self._blink_state:
            self._btn_ign.setText("IGN\nON")
            self._btn_ign.setStyleSheet(f"""
                QPushButton {{
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                        stop:0 #22C55E55, stop:0.6 #0D2A18, stop:1 #080F0B
                    );
                    color: #22C55E;
                    border: 2px solid #22C55E;
                    border-radius: {R}px;
                    font-size: 11px; font-weight: bold; letter-spacing: 1px;
                    outline: none;
                }}
            """)
        else:
            self._btn_ign.setText("IGN\nON")
            self._btn_ign.setStyleSheet(f"""
                QPushButton {{
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                        stop:0 #0A1A10, stop:0.6 #060E09, stop:1 #030705
                    );
                    color: #1A6030;
                    border: 2px solid #1A4A28;
                    border-radius: {R}px;
                    font-size: 11px; font-weight: bold; letter-spacing: 1px;
                    outline: none;
                }}
            """)

    def _refresh_ign_ui(self) -> None:
        R = 40
        if self._ign_on:
            # Confirmed ON — solid green
            self._btn_ign.setText("IGN\nON")
            self._btn_ign.setStyleSheet(f"""
                QPushButton {{
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                        stop:0 #1A4A28, stop:0.6 #0D2A18, stop:1 #080F0B
                    );
                    color: #22C55E;
                    border: 2px solid #22C55E;
                    border-radius: {R}px;
                    font-size: 11px; font-weight: bold; letter-spacing: 1px;
                    outline: none;
                }}
                QPushButton:hover {{
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                        stop:0 #22C55E44, stop:0.6 #1A4A28, stop:1 #0D2A18
                    );
                    border: 2px solid #4ADE80; color: #4ADE80;
                }}
            """)
        else:
            # OFF — distinct red so state is unmistakable
            self._btn_ign.setText("IGN\nOFF")
            self._btn_ign.setStyleSheet(f"""
                QPushButton {{
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                        stop:0 #3A0A0A, stop:0.6 #220808, stop:1 #0A0303
                    );
                    color: #CC1020;
                    border: 2px solid #661010;
                    border-radius: {R}px;
                    font-size: 11px; font-weight: bold; letter-spacing: 1px;
                    outline: none;
                }}
                QPushButton:hover {{
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                        stop:0 #CC102033, stop:0.6 #3A0A0A, stop:1 #220808
                    );
                    border: 2px solid #EF4444; color: #EF4444;
                }}
            """)

    def _on_fetch(self) -> None:
        if self._worker and self._worker.isRunning():
            return   # already in progress

        # Derive is_windows from injected profile (authoritative).
        # Falls back to None → sys.platform auto-detection inside gw_client.
        is_windows: bool | None = None
        if hasattr(self, "_profile") and self._profile is not None:
            from simulator.platform.platform_detector import OperatingSystem
            is_windows = (
                self._profile.operating_system == OperatingSystem.WINDOWS
            )

        self._set_fetching()
        self._worker = _FetchWorker(is_windows=is_windows)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._worker.start()

    def _set_fetching(self) -> None:
        self._btn.setEnabled(False)
        self._btn.setText("FETCHING…")
        self._status_dot.set_colour(t.YELLOW)
        self._status_lbl.setText("Connecting to GW")
        self._status_lbl.setStyleSheet(
            f"color: {t.YELLOW}; font-size: 10px; "
            f"letter-spacing: 1px; background: transparent;"
        )

    def _on_success(self, info: dict) -> None:
        self._row_gw.set_value(info.gw_version)
        self._row_hmi.set_value(info.hmi_version)
        self._row_release.set_value(info.release_version)
        self._row_orig_gw.set_value(info.original_gw_version)

        self._status_dot.set_colour(t.GREEN)
        self._status_lbl.setText("Fetched")
        self._status_lbl.setStyleSheet(
            f"color: {t.GREEN}; font-size: 10px; "
            f"letter-spacing: 1px; background: transparent;"
        )
        self._btn.setEnabled(True)
        self._btn.setText("REFRESH DEVICE DETAILS")
        logger.info("[HOME] Device details fetched successfully")

        # SSH succeeded → GW is definitely reachable at the application level.
        # Emit node_state_changed so MainWindow forwards this to the footer pill.
        # This is more reliable than TCP check: SSH proves the GW OS + SSH daemon
        # are fully functional, not just that port 22 is open.
        self.node_state_changed.emit("gw", "present")

    def _on_failure(self, error: str) -> None:
        for r in (self._row_gw, self._row_hmi, self._row_release, self._row_orig_gw):
            r.set_value("—")

        self._status_dot.set_colour(t.RED)
        self._status_lbl.setText("Failed")
        self._status_lbl.setStyleSheet(
            f"color: {t.RED}; font-size: 10px; "
            f"letter-spacing: 1px; background: transparent;"
        )
        self._btn.setEnabled(True)
        self._btn.setText("FETCH DEVICE DETAILS")
        logger.warning(f"[HOME] Device detail fetch failed: {error}")


