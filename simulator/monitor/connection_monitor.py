from __future__ import annotations

"""
connection_monitor.py

Background daemon — polls all hardware connections every 1 second.
Fires on_change(node_id, connected) only when the state flips.

Detection per device:
  CAN channels    → re-run detect_available_configs (Windows) or check /sys/class/net (Linux/Pi)
  lucid_aovo      → pyserial: VID 16D0 / PID 0821, first matched port
  lucid_aivo      → pyserial: VID 16D0 / PID 0821, second matched port
  gw              → TCP connect to 172.16.0.1:22  (network-level check)
  hmi             → TCP connect to 192.168.82.70:22  (network-level check)
  trailer_ctrl    → CAN heartbeat via ObuBridge (always disconnected when IGN OFF)
  truck_ctrl      → CAN heartbeat via ObuBridge (always disconnected when IGN OFF)
  joystick        → PGN_SENSOR message with sensor_id=JOYSTICK_POS via ObuBridge;
                    requires ObuBridge running (IGN ON) to show as connected
"""

import os
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from loguru import logger

from simulator.config import GW_HOST, GW_PORT, HMI_HOST, HMI_PORT
from simulator.platform.can_detector import CanChannel


# ── Config ────────────────────────────────────────────────────────

LUCID_VID = "16D0"
LUCID_PID = "0821"

POLL_INTERVAL_SEC    = 1.0
TCP_TIMEOUT_SEC      = 0.8

# Joystick is considered online if a CAN sensor message was received
# within this many seconds.
JOYSTICK_CAN_TIMEOUT = 2.0


# ── CAN channel presence helpers ─────────────────────────────────

def _present_can_channels_windows() -> set[str]:
    """Return set of channel names currently seen by the PEAK driver."""
    try:
        import can
        configs = can.detect_available_configs(interfaces="pcan")
        return {c["channel"] for c in configs}
    except Exception:
        return set()


def _present_can_channels_linux() -> set[str]:
    """Return set of can* interface names present in /sys/class/net/."""
    try:
        return {i for i in os.listdir("/sys/class/net/") if i.startswith("can")}
    except Exception:
        return set()


# ── Lucid ─────────────────────────────────────────────────────────

def _lucid_ports() -> list[str]:
    """
    Return sorted list of COM/tty port names that match Lucid VID/PID.
    First match = AOVO, second match = AIVO.
    """
    try:
        import serial.tools.list_ports
        return sorted(
            p.device
            for p in serial.tools.list_ports.comports()
            if LUCID_VID in p.hwid.upper() and LUCID_PID in p.hwid.upper()
        )
    except ImportError:
        logger.warning("pyserial not found — Lucid detection unavailable")
        return []
    except Exception as ex:
        logger.debug(f"Lucid port scan failed: {ex}")
        return []


# ── TCP reachability ──────────────────────────────────────────────

def _tcp_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=TCP_TIMEOUT_SEC):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


# ── Connection Monitor ────────────────────────────────────────────

# Non-CAN nodes always registered in the ConnectionMonitor state dict.
# trailer_ctrl and truck_ctrl are driven by ObuBridge CAN heartbeats, not
# by this monitor directly — their entries ensure footer pills start in the
# disconnected state before the first CAN heartbeat arrives.
_FIXED_NODES: tuple[str, ...] = (
    "lucid_aovo",
    "lucid_aivo",
    "gw",
    "hmi",
    "trailer_ctrl",
    "truck_ctrl",
    "joystick",
)


class ConnectionMonitor(threading.Thread):
    """
    Polls all hardware nodes every POLL_INTERVAL_SEC.
    Calls on_change(node_id, connected) only when the state changes.

    The monitor runs on a background thread. In GUI mode, simulator.py
    bridges on_change through a Qt QueuedConnection so the GUI update
    always happens on the main thread.

    obu_bridge (optional): reference to ObuBridge for joystick detection and
    is also used to track trailer_ctrl / truck_ctrl via CAN heartbeats.
    Pass None when running headless or in tests.
    """

    def __init__(
        self,
        on_change: "Callable[[str, bool], None]",
        can_channels: list[CanChannel],
        profile: "PlatformProfile | None" = None,
        obu_bridge: "ObuBridge | None" = None,
    ) -> None:
        super().__init__(daemon=True, name="ConnectionMonitor")
        self._on_change    = on_change
        self._can_channels = can_channels
        self._obu_bridge   = obu_bridge   # ObuBridge | None — for joystick detection
        self._running      = False

        # Derive platform string from profile — single OS detection path.
        # Falls back to sys.platform if no profile is passed (e.g. in tests).
        if profile is not None:
            from simulator.platform.platform_detector import OperatingSystem
            self._platform = (
                "windows" if profile.operating_system == OperatingSystem.WINDOWS
                else "raspberry_pi" if profile.operating_system == OperatingSystem.RASPBERRY_PI
                else "linux"
            )
        else:
            self._platform = "windows" if sys.platform == "win32" else "linux"

        # Build initial state — None means "not yet polled"
        all_ids = [ch.node_id for ch in can_channels] + list(_FIXED_NODES)
        self._state: dict[str, bool | None] = {nid: None for nid in all_ids}

        logger.info(
            f"ConnectionMonitor ready — platform: {self._platform}  "
            f"obu_bridge: {'wired' if obu_bridge else 'not wired'}"
        )

    def run(self) -> None:
        logger.info(f"ConnectionMonitor started (every {POLL_INTERVAL_SEC}s)")
        self._running = True
        while self._running:
            try:
                self._poll_all()
            except Exception as ex:
                logger.warning(f"Poll error: {ex}")
            time.sleep(POLL_INTERVAL_SEC)
        logger.info("ConnectionMonitor stopped")

    def stop(self) -> None:
        self._running = False

    def _update(self, node_id: str, connected: bool) -> None:
        """Fire on_change only when state actually changes."""
        if self._state.get(node_id) != connected:
            self._state[node_id] = connected
            logger.info(
                f"[{node_id:<16}] {'● CONNECTED' if connected else '○ disconnected'}"
            )
            try:
                self._on_change(node_id, connected)
            except Exception as ex:
                logger.warning(f"on_change error for {node_id}: {ex}")

    def _poll_all(self) -> None:
        # ── CAN channels ─────────────────────────────────────────
        if self._platform == "windows":
            present = _present_can_channels_windows()
        else:
            present = _present_can_channels_linux()

        # Update known channels
        for ch in self._can_channels:
            self._update(ch.node_id, ch.node_id in present)

        # Discover channels that appeared AFTER startup (hot-plug).
        # Register them in _state so _update fires connected for them too.
        known_ids = {ch.node_id for ch in self._can_channels}
        for node_id in present:
            if node_id not in known_ids and node_id not in self._state:
                logger.info(f"[CAN] Hot-plug detected: {node_id} — registering")
                self._state[node_id] = None   # force a fired event on next update
            if node_id not in known_ids:
                self._update(node_id, True)

        # ── Lucid AOVO / AIVO ────────────────────────────────────
        ports = _lucid_ports()
        self._update("lucid_aovo", len(ports) >= 1)
        self._update("lucid_aivo", len(ports) >= 2)

        # ── GW + HMI — TCP reachability (run both concurrently) ────
        # Sequential checks could block for up to 2×TCP_TIMEOUT_SEC when both
        # hosts are offline.  Running in parallel halves the worst case to
        # one TCP_TIMEOUT_SEC slot.
        with ThreadPoolExecutor(max_workers=2) as pool:
            gw_future  = pool.submit(_tcp_reachable, GW_HOST,  GW_PORT)
            hmi_future = pool.submit(_tcp_reachable, HMI_HOST, HMI_PORT)
            gw_ok  = gw_future.result()
            hmi_ok = hmi_future.result()
        self._update("gw",  gw_ok)
        self._update("hmi", hmi_ok)

        # ── Trailer / Truck Controller ────────────────────────────
        # Driven entirely by ObuBridge CAN heartbeats (node_status_changed signal).
        # The monitor only sets the initial disconnected state ONCE at startup
        # (when _state[node_id] is still None) so the pills start red.
        # All subsequent state changes come from ObuBridge, not this loop.
        for node_id in ("trailer_ctrl", "truck_ctrl"):
            if self._state.get(node_id) is None:
                self._update(node_id, False)

        # ── Joystick ─────────────────────────────────────────────
        self._update("joystick", self._poll_joystick())

    def _poll_joystick(self) -> bool:
        """
        Return True when a joystick CAN sensor message was received within
        JOYSTICK_CAN_TIMEOUT seconds.

        Requires ObuBridge to be running (IGN ON).  Returns False when no
        ObuBridge is wired or when no joystick frame has been seen yet.
        """
        if self._obu_bridge is None:
            return False
        try:
            return self._obu_bridge.get_joystick_seen_age() < JOYSTICK_CAN_TIMEOUT
        except Exception as ex:
            logger.warning(f"[joystick] poll error: {ex}")
            return False
