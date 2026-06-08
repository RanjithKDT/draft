"""
main_window.py

Layout:
  ┌──────────────────────────────────────────────────────┐
  │  A — TOP HEADER:  [Logo]  |  HYVA SIMULATOR          │
  ├──────────────────────────────────────────────────────┤
  │  B — RED SEPARATOR (full width, 3px)                 │
  ├───────────────┬─────┬────────────────────────────────┤
  │               │     │                                │
  │  C — SIDEBAR  │  R  │   D — CONTENT AREA             │
  │  [⌂ HOME]     │  E  │   (QStackedWidget)             │
  │  [((●)) CAN]  │  D  │                                │
  ├───────────────┤     ├────────────────────────────────┤
  │  v2.0.5       │     │  OS label  |  pill chips       │
  └───────────────┴─────┴────────────────────────────────┘

All page and widget classes live in their own files:
  simulator/gui/pages/    — QStackedWidget page classes
  simulator/gui/widgets/  — chrome widgets (header, sidebar, footer)
  simulator/gui/components.py — reusable building-block components
"""

from __future__ import annotations

import atexit
import os
import tempfile
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QSizePolicy, QApplication,
)
from PySide6.QtCore import Qt, QTimer
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.styles import build_stylesheet
from simulator.gui.components import RedSepH, RedSepV
from simulator.gui.fonts import load_fonts
from simulator.gui.constants import PROJECT_ROOT
from simulator.platform.platform_detector import PlatformProfile
from simulator.platform.can_detector import CanChannel

from simulator.gui.widgets.top_header import TopHeader
from simulator.gui.widgets.sidebar import Sidebar
from simulator.gui.widgets.footer_bar import FooterBar
from simulator.gui.widgets.goodbye_screen import GoodbyeScreen

from simulator.gui.pages.home_page import HomePage, _ProductPage
from simulator.gui.pages.can_page import CanPage
from simulator.gui.pages.can_tools_page import CanToolsPage
from simulator.gui.pages.sensors_page import SensorsPage
from simulator.gui.pages.calibration_page import CalibrationPage
from simulator.gui.pages.playback_page import PlaybackPage
from simulator.gui.pages.rpc_page import RpcPage
from simulator.gui.pages.settings_page import (
    SettingsLandingPage, AboutPage,
    _GeneralSettingsPage, _WindowsSettingsPage,
    _LinuxSettingsPage, _RaspiSettingsPage,
)


# ── Application version ───────────────────────────────────────────
# Imported from _version.py (single source of truth).
# Re-exported here so callers doing `from main_window import APP_VERSION` still work.
# SIDEBAR_WIDTH, BAUDRATE_OPTIONS, PROJECT_ROOT are imported from constants.py above.


def _cleanup_arrow(path: str) -> None:
    """Remove the temporary SVG file created for the dropdown arrow."""
    try:
        os.remove(path)
    except OSError:
        pass


def _build_arrow_svg() -> str:
    """
    Write the yellow dropdown arrow SVG to a temp file once and return its path.
    CSS border-trick triangles are ignored by Fusion style on Windows;
    image:url() with SVG is the only reliable cross-platform approach.
    Returns "" on failure — QSS silently ignores image:url("").
    """
    path = str(Path(tempfile.gettempdir()) / "dts_arrow_yellow.svg")
    try:
        with open(path, "w") as fh:
            fh.write(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="7">'
                '<polygon points="0,0 10,0 5,7" fill="#FFD100"/></svg>'
            )
        path = path.replace("\\", "/")
        atexit.register(_cleanup_arrow, path)
        return path
    except Exception as ex:
        logger.warning(f"[GUI] Could not write dropdown arrow SVG: {ex}")
        return ""


_ARROW_SVG: str = _build_arrow_svg()


class MainWindow(QMainWindow):

    def __init__(
        self,
        profile: PlatformProfile,
        can_channels: list[CanChannel],
        rpc_server: "RpcServer | None" = None,
    ) -> None:
        super().__init__()
        load_fonts()
        self._profile = profile
        self._can_channels = can_channels
        self._rpc_server = rpc_server

        # Initialised here so set_connection() can safely read/write it even
        # if _build_ui() order ever changes.  _build_ui() must NOT redefine it.
        self._can_connected_count: int = 0

        self.setWindowTitle("Hyva Simulator")
        self.resize(1100, 660)
        self.setMinimumSize(800, 500)

        self._apply_stylesheet()
        # _build_ui() creates self._footer and all pages.
        # IgnitionController is wired AFTER _build_ui() because set_connection()
        # (passed as on_lucid_error) writes to self._footer which _build_ui() creates.
        self._build_ui()

        # ── Ignition controller ───────────────────────────────────
        try:
            from simulator.ign.ignition_controller import IgnitionController
            self._ign_ctrl = IgnitionController(
                profile,
                on_lucid_error=self.set_connection,
            )
            self._home.set_ign_controller(self._ign_ctrl)
            logger.info(f"[IGN] Controller ready: {self._ign_ctrl._backend.name}")
        except Exception as ex:
            logger.warning(f"[IGN] Controller init failed: {ex} — visual only")
            self._ign_ctrl = None

        self._home.set_profile(self._profile)

        # ── OBU Bridge ────────────────────────────────────────────
        try:
            from simulator.obu.obu_bridge import ObuBridge
            first_ch = can_channels[0] if can_channels else None
            ch = first_ch.node_id if first_ch else "PCAN_USBBUS1"
            br = first_ch.bitrate if first_ch and first_ch.bitrate > 0 else 250_000
            self._obu_bridge = ObuBridge(channel=ch, bitrate=br, profile=self._profile)
            self._home.set_obu_bridge(self._obu_bridge)
            self._sensors_page.set_obu_bridge(self._obu_bridge)
            self._playback_page.set_obu_bridge(self._obu_bridge)
            self._home.node_state_changed.connect(self._on_node_state_changed)
            logger.info(f"[OBU] Bridge ready on {ch}")
        except Exception as ex:
            logger.warning(f"[OBU] Bridge init failed: {ex}")
            self._obu_bridge = None
            self._sensors_page.set_obu_bridge(None)
            self._playback_page.set_obu_bridge(None)

        # ── Lucid sensor voltage output ───────────────────────────
        self._lucid_sensor_output = None
        if self._obu_bridge is not None and self._ign_ctrl is not None:
            try:
                sensor_out = self._ign_ctrl.make_sensor_output()
                if sensor_out is not None:
                    self._obu_bridge.sensor_reading_changed.connect(
                        sensor_out.update, Qt.QueuedConnection
                    )
                    self._lucid_sensor_output = sensor_out
                    logger.info(
                        "[GUI] Lucid sensor voltage output wired — "
                        "AOVO ch0=pressure  ch1=lat  ch2=long"
                    )
                else:
                    logger.info(
                        "[GUI] Lucid sensor voltage output not available "
                        "(no Lucid hardware or GPIO/Software backend)"
                    )
            except Exception as ex:
                logger.warning(f"[GUI] Lucid sensor output init failed: {ex}")

        # ── RPC Server ────────────────────────────────────────────
        if self._rpc_server is not None:
            self._rpc_server.set_bridge(self._obu_bridge)
            self._rpc_server.set_ign_ctrl(self._ign_ctrl)
            ok = self._rpc_server.start()
            self._rpc_page.set_rpc_server(self._rpc_server if ok else None)
            self._footer.set_connection("rpc", ok)
            if not ok:
                logger.warning("[GUI] RPC server failed to start — footer pill set to red")
        else:
            self._rpc_page.set_rpc_server(None)
            self._footer.set_connection("rpc", False)

        logger.info("[GUI] Ready — all pages initialized")

    def _apply_stylesheet(self) -> None:
        """Apply global QSS built from theme tokens — called once at startup."""
        self.setStyleSheet(build_stylesheet(arrow_svg_path=_ARROW_SVG))

    def _build_ui(self) -> None:
        central = QWidget()
        central.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._top_header = TopHeader()
        root.addWidget(self._top_header)
        root.addWidget(RedSepH(height=3))

        mid = QWidget()
        mid.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mid_row = QHBoxLayout(mid)
        mid_row.setContentsMargins(0, 0, 0, 0)
        mid_row.setSpacing(0)

        sidebar = Sidebar(can_channel_count=len(self._can_channels))
        self._sidebar = sidebar
        sidebar.page_requested.connect(self._switch_page)
        mid_row.addWidget(sidebar)
        mid_row.addWidget(RedSepV())

        self._stack = QStackedWidget()

        self._home              = HomePage()
        self._can_page          = CanPage(self._can_channels, profile=self._profile)
        self._sensors_page      = SensorsPage()
        self._playback_page     = PlaybackPage()
        self._rpc_page          = RpcPage()
        self._settings          = SettingsLandingPage()
        self._about             = AboutPage()
        self._calibration_page  = CalibrationPage()
        self._can_tools_page    = CanToolsPage(
            profile=self._profile,
            can_channels=self._can_channels,
        )

        self._page_guide     = _ProductPage("GUIDE",       "#FFD100")
        self._page_control   = _ProductPage("CONTROL",     "#CC1020")
        self._page_tipbywire = _ProductPage("TIP BY WIRE", "#FFD100")
        self._page_epto      = _ProductPage("EPTO",        "#CC1020")

        self._settings_general = _GeneralSettingsPage(profile=self._profile)
        self._settings_windows = _WindowsSettingsPage(profile=self._profile)
        self._settings_linux   = _LinuxSettingsPage(profile=self._profile)
        self._settings_raspi   = _RaspiSettingsPage(profile=self._profile)

        self._can_page.baudrate_changed.connect(self._on_baudrate_changed)

        for page in (
            self._home,             # 0
            self._can_page,         # 1
            self._sensors_page,     # 2
            self._playback_page,    # 3
            self._rpc_page,         # 4
            self._settings,         # 5
            self._about,            # 6
            self._page_guide,       # 7
            self._page_control,     # 8
            self._page_tipbywire,   # 9
            self._page_epto,        # 10
            self._settings_general, # 11
            self._settings_windows, # 12
            self._settings_linux,   # 13
            self._settings_raspi,   # 14
            self._calibration_page, # 15
            self._can_tools_page,   # 16
        ):
            self._stack.addWidget(page)

        self._home.product_requested.connect(self._on_product_requested)
        self._settings.setting_requested.connect(self._on_setting_requested)
        self._can_page.tools_requested.connect(lambda: self._switch_page(16))

        # ── Easter egg: logo 6-click → Credits dialog ─────────────
        # _LogoLabel.credits_triggered is emitted on the 6th consecutive
        # logo click within the 2-second timeout window.
        # AboutPage.open_credits() opens _CreditsDialog modally.
        self._top_header._logo_lbl.credits_triggered.connect(
            self._about.open_credits
        )

        mid_row.addWidget(self._stack)
        root.addWidget(mid)

        self._footer = FooterBar(
            platform_label=self._profile.display_label,
            can_channels=self._can_channels,
        )
        root.addWidget(self._footer)

    PAGE_NAMES: dict[int, str] = {
        0: "HOME",      1: "CAN",       2: "SENSORS",    3: "PLAYBACK",
        4: "RPC",       5: "SETTINGS",  6: "ABOUT",
        7: "GUIDE",     8: "CONTROL",   9: "TIP BY WIRE", 10: "EPTO",
        11: "SETTINGS/GENERAL", 12: "SETTINGS/WINDOWS",
        13: "SETTINGS/LINUX",   14: "SETTINGS/RASPI",
        15: "CALIBRATIONS",     16: "CAN TOOLS",
    }

    _PRODUCT_INDEX: dict[str, int] = {
        "GUIDE": 7, "CONTROL": 8, "TIP BY WIRE": 9, "EPTO": 10,
    }

    _SETTING_INDEX: dict[str, int] = {
        "general": 11, "windows": 12, "linux": 13, "raspi": 14,
    }

    def _switch_page(self, index: int) -> None:
        name = self.PAGE_NAMES.get(index, f"PAGE_{index}")
        logger.info(f"[NAV] → {name} page")
        self._stack.setCurrentIndex(index)

    def _on_product_requested(self, product_name: str) -> None:
        idx = self._PRODUCT_INDEX.get(product_name)
        if idx is not None:
            logger.info(f"[NAV] Product card → {product_name} (index {idx})")
            self._stack.setCurrentIndex(idx)

    def _on_setting_requested(self, key: str) -> None:
        idx = self._SETTING_INDEX.get(key)
        if idx is not None:
            logger.info(f"[NAV] Settings card → {key} (index {idx})")
            self._stack.setCurrentIndex(idx)

    def _on_baudrate_changed(self, node_id: str, bitrate: int) -> None:
        if bitrate >= 1_000_000:
            label = f"{bitrate // 1_000_000} Mbps"
        elif bitrate >= 1_000:
            label = f"{bitrate // 1_000} kbps"
        else:
            label = f"{bitrate} bps"
        logger.info(f"[CAN] Footer pill update: {node_id} → {label}")
        self._footer.update_baudrate(node_id, label)

    def set_connection(self, node_id: str, connected: bool) -> None:
        """Called by ConnectionMonitor via Qt signal to update all nodes."""
        self._footer.set_connection(node_id, connected)
        self._can_page.set_connection(node_id, connected)
        self._can_tools_page.set_connection(node_id, connected)

        if node_id == "lucid_aovo" and not connected:
            if getattr(self, "_lucid_sensor_output", None) is not None:
                logger.warning(
                    "[GUI] Lucid AOVO disconnected — "
                    "marking sensor voltage output disconnected"
                )
                self._lucid_sensor_output.mark_disconnected()

        can_ids = {ch.node_id for ch in self._can_channels}
        if node_id in can_ids:
            if connected:
                self._can_connected_count = min(
                    self._can_connected_count + 1, len(self._can_channels)
                )
                ch = next(c for c in self._can_channels if c.node_id == node_id)
                logger.info(
                    f"[CAN] {node_id} reconnected — "
                    f"re-applying saved baudrate {ch.bitrate_label}"
                )
                self._on_baudrate_changed(node_id, ch.bitrate)
            else:
                self._can_connected_count = max(self._can_connected_count - 1, 0)

            self._sidebar.update_can_badge(
                self._can_connected_count, len(self._can_channels)
            )

    def get_obu_bridge(self) -> "ObuBridge | None":
        """Return the ObuBridge instance, or None if not yet initialised."""
        return getattr(self, "_obu_bridge", None)

    def _on_node_state_changed(self, node_id: str, state: str) -> None:
        """Forward CAN node state from OBU bridge → footer pills."""
        self._footer.set_node_state(node_id, state)

    def closeEvent(self, event) -> None:
        if getattr(self, "_goodbye_shown", False):
            event.accept()
            return

        self._goodbye_shown = True
        logger.info("[GUI] Window closed by user — showing goodbye screen")
        event.ignore()

        if self._ign_ctrl:
            try:
                self._ign_ctrl.close()
            except Exception as ex:
                logger.warning(f"[GUI] Ignition controller close error: {ex}")

        if getattr(self, "_obu_bridge", None):
            try:
                self._obu_bridge.stop_bridge()
            except Exception as ex:
                logger.warning(f"[GUI] OBU bridge stop error: {ex}")

        logo_path = PROJECT_ROOT / "assets" / "logo" / "hyva_logo.jpg"
        self._goodbye = GoodbyeScreen(logo_path, parent=self)
        self._goodbye.setGeometry(self.geometry())
        self._goodbye.show()
        self._goodbye.raise_()

        goodbye_ms = int(GoodbyeScreen._PHASE_FADE_END * 1000) + 200
        QTimer.singleShot(goodbye_ms, self._do_close)

    def _do_close(self) -> None:
        """Called once the goodbye animation has finished — quit the app."""
        logger.info("[GUI] Goodbye animation complete — quitting")

        # Wait for ObuBridge QThread to finish.
        # stop_bridge() was called in closeEvent — give the thread up to
        # 2 s to drain its CAN loop before we forcibly quit.
        obu = getattr(self, "_obu_bridge", None)
        if obu is not None and obu.isRunning():
            logger.debug("[GUI] Waiting for ObuBridge thread to exit...")
            if not obu.wait(2000):
                logger.warning("[GUI] ObuBridge thread did not stop in 2 s — terminating")
                obu.terminate()
                obu.wait(500)

        # Stop and wait for the InternetMonitor QThread owned by TopHeader.
        # TopHeader.closeEvent() is never called for child widgets, so we
        # must stop the monitor explicitly here.
        top_header = getattr(self, "_top_header", None)
        if top_header is not None:
            net_mon = getattr(top_header, "_net_monitor", None)
            if net_mon is not None and net_mon.isRunning():
                logger.debug("[GUI] Stopping InternetMonitor...")
                net_mon.stop()
                if not net_mon.wait(2000):
                    logger.warning("[GUI] InternetMonitor did not stop in 2 s — terminating")
                    net_mon.terminate()
                    net_mon.wait(500)

        if getattr(self, "_goodbye", None):
            self._goodbye.close()

        app = QApplication.instance()
        if app:
            app.quit()
