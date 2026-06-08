"""
can_detector.py

Detects available CAN channels for the current platform at startup.
Returns a list of CanChannel objects shown as dots in the GUI footer.

Windows     → can.detect_available_configs('pcan')
              finds PCAN_USBBUS1, PCAN_USBBUS2, etc. via the PEAK driver
RasPi       → scans /sys/class/net/ for can* interfaces (CAN HAT)
              reads actual baudrate from 'ip link' output
Linux       → placeholder (hardware not yet determined)
"""

import os
import re
import subprocess
from dataclasses import dataclass
from loguru import logger

from simulator.platform.platform_detector import PlatformProfile, OperatingSystem

DEFAULT_BITRATE = 250_000


@dataclass
class CanChannel:
    node_id: str  # unique key used in monitor + GUI  e.g. "PCAN_USBBUS1"
    name:    str  # display name in footer           e.g. "PCAN_USBBUS1"
    bitrate: int  # configured bitrate in bps — can be changed by the user

    @property
    def bitrate_label(self) -> str:
        """Human-readable bitrate e.g. '250 kbps', '1 Mbps'."""
        if self.bitrate == 0:
            return "—"
        if self.bitrate >= 1_000_000:
            return f"{self.bitrate // 1_000_000} Mbps"
        return f"{self.bitrate // 1000} kbps"


def detect_can_channels(profile: PlatformProfile, bitrate: int = DEFAULT_BITRATE) -> list[CanChannel]:
    """
    Detect available CAN channels for the current platform.
    Called once at startup. Returns whatever is plugged in right now.
    """
    if profile.operating_system == OperatingSystem.WINDOWS:
        return _detect_windows(bitrate)
    if profile.operating_system == OperatingSystem.RASPBERRY_PI:
        return _detect_raspi(bitrate)
    return _detect_linux_placeholder()


# Standard PCAN USB channel names on Windows (always shown so hot-plug works).
# The ConnectionMonitor polls their presence every second and fires
# connected/disconnected as adapters are plugged or unplugged.
_WINDOWS_PCAN_CHANNELS = [
    "PCAN_USBBUS1",
    "PCAN_USBBUS2",
    "PCAN_USBBUS3",
    "PCAN_USBBUS4",
]

# How many PCAN channels are always shown in the UI regardless of what the
# driver reports — ensures the footer has cards even before hardware is plugged in.
_WINDOWS_PCAN_DEFAULT_COUNT = 2


def _detect_windows(bitrate: int) -> list[CanChannel]:
    """
    Build the channel list for Windows / PCAN-USB.

    Strategy:
      1. Ask the PCAN driver which channels are currently present.
      2. Always include at least PCAN_USBBUS1 and PCAN_USBBUS2 so the GUI
         shows cards even when no adapter is plugged in at startup.
         The ConnectionMonitor turns the dots red/green as adapters come and go.
      3. Any extra channels reported by the driver (USBBUS3, USBBUS4 …)
         are appended so users with more hardware see all their adapters.
    """
    # --- query driver ---
    driver_names: list[str] = []
    try:
        import can
        configs = can.detect_available_configs(interfaces="pcan")
        driver_names = [c["channel"] for c in configs]
        logger.info(f"[CAN] PCAN driver reports: {driver_names or 'none'}")
    except Exception as ex:
        logger.warning(f"[CAN] PCAN driver query failed: {ex}")

    # --- build deduped ordered list ---
    # Always start with the two standard channels, then append any extra
    # channels the driver found that are not already in the list.
    seen: set[str] = set()
    ordered: list[str] = []
    for name in _WINDOWS_PCAN_CHANNELS[:_WINDOWS_PCAN_DEFAULT_COUNT]:   # always show first N channels
        seen.add(name)
        ordered.append(name)
    for name in driver_names:                  # extra from driver (e.g. USBBUS3)
        if name not in seen:
            seen.add(name)
            ordered.append(name)

    channels = [
        CanChannel(node_id=name, name=name, bitrate=bitrate)
        for name in ordered
    ]
    logger.info(
        f"[CAN] Channels registered for monitoring: {[c.name for c in channels]}"
        f" (driver currently sees: {driver_names or 'none'})"
    )
    return channels


def _detect_raspi(bitrate: int) -> list[CanChannel]:
    """
    Scan /sys/class/net/ for can* network interfaces (SocketCAN / CAN HAT).
    Tries to read the actual configured baudrate from 'ip link' output.
    """
    try:
        channels = []
        for iface in sorted(os.listdir("/sys/class/net/")):
            if iface.startswith("can"):
                actual_bitrate = _socketcan_bitrate(iface) or bitrate
                channels.append(CanChannel(node_id=iface, name=iface, bitrate=actual_bitrate))
        if channels:
            logger.info(f"CAN channels detected: {[c.name for c in channels]}")
        else:
            logger.warning("No SocketCAN interfaces found — check CAN HAT is installed and interface is up")
        return channels
    except Exception as ex:
        logger.warning(f"SocketCAN detection failed: {ex}")
        return []


def _detect_linux_placeholder() -> list[CanChannel]:
    """
    Linux desktop — scan for any socketcan interfaces first,
    fall back to a 'can0' placeholder if none found.
    Always uses DEFAULT_BITRATE so the monitor can attempt to open it.
    """
    try:
        channels = []
        for iface in sorted(os.listdir("/sys/class/net/")):
            if iface.startswith("can"):
                actual_bitrate = _socketcan_bitrate(iface) or DEFAULT_BITRATE
                channels.append(CanChannel(node_id=iface, name=iface, bitrate=actual_bitrate))
        if channels:
            logger.info(f"CAN channels detected (Linux): {[c.name for c in channels]}")
            return channels
    except Exception as ex:
        logger.debug(f"Linux CAN scan failed: {ex}")

    # No interfaces found — show a placeholder so the UI doesn't look broken
    logger.info("CAN detection on Linux: no interfaces found, showing placeholder")
    return [CanChannel(node_id="can0", name="can0", bitrate=DEFAULT_BITRATE)]


def _socketcan_bitrate(iface: str) -> int | None:
    """Read the baudrate of a SocketCAN interface using 'ip -d link show <iface>'."""
    try:
        result = subprocess.run(
            ["ip", "-d", "link", "show", iface],
            capture_output=True, text=True, timeout=2,
        )
        match = re.search(r"bitrate\s+(\d+)", result.stdout)
        if match:
            return int(match.group(1))
    except Exception as ex:
        logger.debug(f"[CAN] Could not read bitrate for {iface}: {ex}")
    return None
