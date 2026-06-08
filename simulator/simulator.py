from __future__ import annotations

"""
simulator.py

Wires all subsystems together for v2.0.5.

Start order:  HAL → CAN channel detection → GUI (creates ObuBridge) →
              ConnectionMonitor (receives ObuBridge ref) → RPC server
Stop order:   GUI closes → RPC server → ConnectionMonitor → HAL

The ConnectionMonitor is started AFTER MainWindow so it can receive the
ObuBridge reference via window.get_obu_bridge() — needed for joystick
detection and for immediate Lucid error reporting.
"""

import sys
import signal
import time
from typing import Callable
from loguru import logger

from simulator.platform.platform_detector import PlatformProfile
from simulator.platform.can_detector import CanChannel, detect_can_channels
from simulator.monitor.connection_monitor import ConnectionMonitor
from simulator.rpc.rpc_server import RpcServer


class Simulator:

    def __init__(self, profile: PlatformProfile, hal: "IHal", no_gui: bool = False) -> None:
        self._profile    = profile
        self._hal        = hal
        self._no_gui     = no_gui
        self._monitor    = None
        self._rpc_server = RpcServer()   # created here; started after bridge is wired

    def start(self) -> None:
        logger.info("[SIM] Starting subsystems...")
        self._hal.start()
        logger.info("[SIM] HAL started")

        # Detect which CAN channels exist — passed to GUI and monitor
        can_channels = detect_can_channels(self._profile)
        logger.info(
            f"[SIM] CAN channels: {[ch.node_id for ch in can_channels] or ['none']}"
        )

        # Inject platform profile into RPC context now (before start)
        self._rpc_server.set_profile(self._profile)

        exit_code = (
            self._run_headless(can_channels) if self._no_gui
            else self._run_gui(can_channels)
        )
        self._shutdown()
        sys.exit(exit_code)

    def _run_gui(self, can_channels: list[CanChannel]) -> int:
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QObject, Signal, Qt
            from simulator.gui.main_window import MainWindow
        except ImportError as ex:
            logger.error(f"PySide6 not available: {ex}")
            return 1

        from simulator.gui._version import APP_VERSION
        app = QApplication.instance() or QApplication(sys.argv)
        app.setApplicationName("Hyva Simulator")
        app.setOrganizationName("Hyva")
        app.setApplicationVersion(APP_VERSION)
        app.setStyle("Fusion")
        logger.info("[SIM] Qt application created")

        # Pass RpcServer to MainWindow so _init_subsystems can wire it after
        # the bridge and ign_ctrl are ready, then call rpc_server.start().
        window = MainWindow(
            profile      = self._profile,
            can_channels = can_channels,
            rpc_server   = self._rpc_server,
        )
        window.show()
        logger.info("[SIM] MainWindow shown")

        # Monitor: on_change bridged via Qt QueuedConnection so GUI updates
        # always happen on the main thread regardless of which thread fires.
        class _Bridge(QObject):
            connection_changed = Signal(str, bool)

        bridge = _Bridge()
        bridge.connection_changed.connect(window.set_connection, Qt.QueuedConnection)

        # Pass the ObuBridge to ConnectionMonitor for joystick detection.
        # window.get_obu_bridge() is safe here — MainWindow.__init__ has completed.
        self._start_monitor(
            can_channels,
            on_change  = bridge.connection_changed.emit,
            obu_bridge = window.get_obu_bridge(),
        )

        logger.info("GUI open — close the window to stop")
        return app.exec()

    def _run_headless(self, can_channels: list[CanChannel]) -> int:
        logger.info("Headless mode — no GUI (Ctrl+C to stop)")
        # No ObuBridge available in headless mode — joystick stays disconnected
        self._start_monitor(can_channels, on_change=self._log_change, obu_bridge=None)
        # Start RPC immediately (bridge not yet wired, but the server accepts
        # connections and returns errors for bridge operations)
        self._rpc_server.start()
        # Install SIGINT handler so Ctrl+C triggers clean shutdown.
        # guard: signal.signal raises ValueError when called from a non-main thread.
        try:
            signal.signal(signal.SIGINT, self._handle_sigint)
        except (ValueError, OSError) as ex:
            logger.warning(f"[SIM] Could not install SIGINT handler: {ex}")
        while True:
            time.sleep(0.5)

    def _start_monitor(
        self,
        can_channels: list[CanChannel],
        on_change: Callable[[str, bool], None],
        obu_bridge: "ObuBridge | None" = None,
    ) -> None:
        self._monitor = ConnectionMonitor(
            on_change    = on_change,
            can_channels = can_channels,
            profile      = self._profile,
            obu_bridge   = obu_bridge,
        )
        self._monitor.start()

    def _shutdown(self) -> None:
        logger.info("Shutting down...")
        self._rpc_server.stop()
        if self._monitor:
            self._monitor.stop()
            self._monitor.join(timeout=2.0)   # wait up to 2 s for poll loop to exit
            if self._monitor.is_alive():
                logger.warning("[SIM] ConnectionMonitor did not stop in 2 s")
        self._hal.stop()
        self._hal.join()
        logger.info("Done")

    def _handle_sigint(self, signum: int, frame: object) -> None:
        self._shutdown()
        sys.exit(0)

    @staticmethod
    def _log_change(node_id: str, connected: bool) -> None:
        logger.info(f"[{node_id}] {'CONNECTED' if connected else 'disconnected'}")
