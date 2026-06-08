"""
simulator/ign/ignition_controller.py
=====================================
Platform-aware ignition (relayPower / K15) controller.

Mirrors the dev-team DTS simulator's relayPower logic:
  - Windows / Linux  : LucidIO AOVO (LucidControlAO4), channel 3
                       IGN ON  → 0.0 V  (relay closed,  K15 active)
                       IGN OFF → 5.0 V  (relay open,    K15 inactive)
                       Relay is inverted → digital-true-value = 0.0 V
  - Raspberry Pi     : GPIO pin 27 (BCM), inverted output
                       IGN ON  → pin LOW   (inverted_output = true)
                       IGN OFF → pin HIGH
  - No hardware      : Software-only — state tracked, nothing written

Usage
-----
    ctrl = IgnitionController(profile)
    ctrl.set_ignition(True)    # IGN ON
    ctrl.set_ignition(False)   # IGN OFF
    state = ctrl.is_on()       # bool
"""

from __future__ import annotations

import sys
from loguru import logger

# ── constants matching dev-team config ───────────────────────────────────────
_LUCID_CHANNEL      = 3          # 0-indexed channel on AOVO module
_LUCID_VOLTAGE_ON   = 0.0        # V — relay closed (inverted)
_LUCID_VOLTAGE_OFF  = 5.0        # V — relay open   (inverted)
_GPIO_PIN_BCM       = 27         # BCM GPIO pin on Raspberry Pi
_LUCID_AOVO_VID     = 0x16D0     # USB Vendor  ID for Lucid AOVO
_LUCID_AOVO_PID     = 0x0821     # USB Product ID for Lucid AOVO


# ══════════════════════════════════════════════════════════════════════════════
# BACKENDS
# ══════════════════════════════════════════════════════════════════════════════

class _SoftwareBackend:
    """No hardware — just logs the state change."""
    name = "Software (no hardware)"

    def set(self, on: bool) -> bool:
        logger.info(f"[IGN][Software] Ignition {'ON' if on else 'OFF'} (no hardware output)")
        return True

    def close(self) -> None: pass


class _LucidBackend:
    """
    Controls the AOVO (LucidControlAO4) on Windows / Linux.
    Auto-detects the correct COM port / ttyACM port by scanning
    serial ports for the Lucid AOVO USB VID:PID.

    on_lucid_error: optional callable(node_id, connected).  Called with
    (\"lucid_aovo\", False) when a mid-session serial failure is detected so
    the ConnectionMonitor (and footer pill) can be updated immediately.
    """
    name = "LucidIO AOVO"

    def __init__(self, on_lucid_error: "Callable[[], None] | None" = None) -> None:
        self._control        = None
        self._value_objs     = None
        self._port_str       = None
        self._connected      = False
        self._on_lucid_error = on_lucid_error   # callable(node_id, connected) | None
        self._connect()

    # ── internal ─────────────────────────────────────────────────
    def _find_port(self) -> str | None:
        """Scan serial ports for the Lucid AOVO by VID/PID."""
        try:
            import serial.tools.list_ports
            for p in serial.tools.list_ports.comports():
                if p.vid == _LUCID_AOVO_VID and p.pid == _LUCID_AOVO_PID:
                    logger.info(f"[IGN][Lucid] Found AOVO on {p.device}")
                    return p.device
        except Exception as ex:
            logger.warning(f"[IGN][Lucid] Port scan failed: {ex}")
        return None

    def _connect(self) -> None:
        try:
            import os
            import importlib

            # The bundled package folder is 'ign_lucidio' but its files import
            # each other as 'lucidIo'. Register under both names so internal
            # imports resolve correctly.
            lucid_parent = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..")
            )
            if lucid_parent not in sys.path:
                sys.path.insert(0, lucid_parent)

            # Import once under the folder name, then alias to 'lucidIo'.
            pkg = importlib.import_module("ign_lucidio")
            if "lucidIo" not in sys.modules:
                sys.modules["lucidIo"] = pkg

            from ign_lucidio.LucidControlAO4 import LucidControlAO4
            from ign_lucidio.Values import ValueVOS4

            port = self._find_port()
            if not port:
                logger.warning("[IGN][Lucid] AOVO not detected — falling back to software")
                return

            self._port_str   = port
            self._control    = LucidControlAO4(port)
            self._value_objs = [ValueVOS4() for _ in range(4)]

            self._control.open()
            self._connected = True
            logger.info(f"[IGN][Lucid] AOVO connected on {port}")

        except Exception as ex:
            logger.warning(f"[IGN][Lucid] Connection failed: {ex} — falling back to software")
            self._connected = False

    # ── public ───────────────────────────────────────────────────
    def set(self, on: bool) -> bool:
        voltage = _LUCID_VOLTAGE_ON if on else _LUCID_VOLTAGE_OFF
        label   = "ON" if on else "OFF"

        if not self._connected:
            logger.warning(f"[IGN][Lucid] Not connected — IGN {label} not sent")
            return False

        try:
            self._value_objs[_LUCID_CHANNEL].setVoltage(voltage)
            enabled = [False, False, False, False]
            enabled[_LUCID_CHANNEL] = True
            self._control.setIoGroup(tuple(enabled), tuple(self._value_objs))
            logger.info(f"[IGN][Lucid] IGN {label} → channel {_LUCID_CHANNEL} = {voltage}V")
            return True
        except Exception as ex:
            logger.error(
                f"[IGN][Lucid] Failed to set IGN {label} on port {self._port_str}: {ex}"
            )
            self._connected = False
            # Notify ConnectionMonitor (and the footer pill) immediately.
            if self._on_lucid_error is not None:
                try:
                    self._on_lucid_error("lucid_aovo", False)
                except Exception as cb_ex:
                    logger.warning(f"[IGN][Lucid] on_lucid_error callback failed: {cb_ex}")
            return False

    def get_shared_resources(self) -> tuple:
        """
        Return (control, value_objs) so sensor voltage output can share
        the already-open serial port.

        Returns (None, None) if the backend is not connected — callers must
        check the first element before creating a LucidSensorOutput.

        The serial port is exclusive — opening it a second time would fail on
        all platforms.  Sharing resources is the only correct approach.
        """
        if not self._connected:
            logger.debug("[IGN][Lucid] get_shared_resources: not connected")
            return None, None
        logger.debug(
            f"[IGN][Lucid] Sharing control on {self._port_str} "
            "for sensor voltage output"
        )
        return self._control, self._value_objs

    def close(self) -> None:
        if self._control and self._connected:
            try:
                self._control.close()
            except Exception as ex:
                logger.warning(f"[IGN][Lucid] Close error: {ex}")
        self._connected = False


class _GpioBackend:
    """
    Controls GPIO pin 27 (BCM) on Raspberry Pi via gpiod.
    Inverted output: IGN ON → pin LOW, IGN OFF → pin HIGH.
    """
    name = "GPIO (Raspberry Pi)"

    def __init__(self, gpio_chip: str = "gpiochip0") -> None:
        self._chip_name = gpio_chip
        self._chip      = None
        self._session   = None
        self._gpio      = None
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        try:
            import gpiod
            self._gpio = gpiod

            # chip name already resolved by platform_detector — no re-detection needed
            self._chip = gpiod.Chip(f"/dev/{self._chip_name}")

            # Request pin 27 as output, initial HIGH (relay open = IGN OFF)
            settings = gpiod.LineSettings(
                direction=gpiod.line.Direction.OUTPUT,
                output_value=gpiod.line.Value.ACTIVE,   # HIGH = OFF (inverted)
                active_low=True,                          # inverted_output = true
            )
            self._session = self._chip.request_lines(
                consumer="hyva-simulator-ign",
                config={_GPIO_PIN_BCM: settings},
            )
            self._connected = True
            logger.info(f"[IGN][GPIO] Pin {_GPIO_PIN_BCM} ready")

        except Exception as ex:
            logger.warning(f"[IGN][GPIO] Init failed: {ex} — falling back to software")
            self._connected = False

    def set(self, on: bool) -> bool:
        label = "ON" if on else "OFF"
        if not self._connected:
            logger.warning(f"[IGN][GPIO] Not connected — IGN {label} not sent")
            return False
        try:
            # active_low=True means ACTIVE = LOW physically
            # IGN ON  → we want relay closed → pin LOW  → set ACTIVE
            # IGN OFF → we want relay open   → pin HIGH → set INACTIVE
            val = self._gpio.line.Value.ACTIVE if on else self._gpio.line.Value.INACTIVE
            self._session.set_value(_GPIO_PIN_BCM, val)
            logger.info(f"[IGN][GPIO] Pin {_GPIO_PIN_BCM} → {val.name} (IGN {label})")
            return True
        except Exception as ex:
            logger.error(f"[IGN][GPIO] Failed: {ex}")
            return False

    def close(self) -> None:
        try:
            if self._session:
                self._session.release()
        except Exception as ex:
            logger.warning(f"[IGN][GPIO] Session release error: {ex}")


# ══════════════════════════════════════════════════════════════════════════════
# CONTROLLER — public API
# ══════════════════════════════════════════════════════════════════════════════

class IgnitionController:
    """
    Platform-aware ignition controller.
    Instantiate once and call set_ignition(True/False).

    on_lucid_error: optional callable(node_id, connected) fired immediately
    when the Lucid AOVO backend detects a mid-session serial failure.
    Wire this to ConnectionMonitor.on_change so the footer pill turns red
    without waiting for the next 1-second poll cycle.
    """

    def __init__(self, profile: "PlatformProfile", on_lucid_error: "Callable[[], None] | None" = None) -> None:
        self._on      = False
        self._profile = profile
        self._backend = self._create_backend(profile, on_lucid_error)
        logger.info(f"[IGN] Backend: {self._backend.name}")

    # ── backend selection ─────────────────────────────────────────
    def _create_backend(self, profile: "PlatformProfile", on_lucid_error: "Callable[[], None] | None") -> "_IBackend":
        from simulator.platform.platform_detector import OperatingSystem

        cur_os = getattr(profile, "operating_system", None)

        # Raspberry Pi → GPIO pin 27
        if cur_os == OperatingSystem.RASPBERRY_PI:
            logger.info("[IGN] Raspberry Pi detected — using GPIO backend")
            chip = getattr(profile, "gpio_chip", None) or "gpiochip0"
            backend = _GpioBackend(gpio_chip=chip)
            if backend._connected:
                return backend
            logger.warning("[IGN] GPIO failed — falling back to software")
            return _SoftwareBackend()

        # Windows / Linux → try LucidIO AOVO first
        try:
            import serial.tools.list_ports
            lucid_found = any(
                p.vid == _LUCID_AOVO_VID and p.pid == _LUCID_AOVO_PID
                for p in serial.tools.list_ports.comports()
            )
            if lucid_found:
                logger.info("[IGN] Lucid AOVO detected — using LucidIO backend")
                return _LucidBackend(on_lucid_error=on_lucid_error)
        except Exception as ex:
            logger.debug(f"[IGN] Serial port scan failed: {ex} — skipping LucidIO")

        logger.warning("[IGN] No hardware detected — using Software backend (visual only)")
        return _SoftwareBackend()

    # ── public ────────────────────────────────────────────────────
    def set_ignition(self, on: bool) -> bool:
        """Set ignition state. Returns True if hardware acknowledged."""
        self._on = on
        return self._backend.set(on)

    def is_on(self) -> bool:
        return self._on

    def make_sensor_output(self) -> "LucidSensorOutput | None":
        """
        Create a LucidSensorOutput that shares the AOVO serial port.

        Returns a LucidSensorOutput when using the Lucid backend and the
        device is connected.  Returns None for GPIO (Raspberry Pi) and
        Software backends — sensor voltage output is not available there.

        The returned object's update(sensor_id, value) slot should be
        connected to ObuBridge.sensor_reading_changed so voltages stay in
        sync with the CAN sensor messages.
        """
        if not isinstance(self._backend, _LucidBackend):
            logger.info(
                "[IGN] make_sensor_output: backend is not LucidIO — "
                "sensor voltage output unavailable"
            )
            return None

        control, value_objs = self._backend.get_shared_resources()
        if control is None:
            logger.warning(
                "[IGN] make_sensor_output: Lucid not connected — "
                "sensor voltage output unavailable"
            )
            return None

        from simulator.lucid.sensor_output import LucidSensorOutput
        return LucidSensorOutput(control, value_objs)

    def close(self) -> None:
        """Call on shutdown to release hardware resources."""
        self._backend.close()
