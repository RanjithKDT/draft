"""
simulator/lucid/sensor_output.py
=================================
Writes simulated sensor voltages to the Lucid AOVO (Analogue Output Voltage)
module on channels 0–2.

Background
----------
The physical DTS testbench uses a Lucid LucidControlAO4 with 4 channels:
  Channel 0 → Cylinder Pressure  (pressureCyl)
  Channel 1 → Lateral Tilt       (inclinationLat)
  Channel 2 → Longitudinal Tilt  (inclinationLong)
  Channel 3 → Ignition relay     (relayPower) — owned by IgnitionController

All four channels share ONE serial port connection.  This class receives the
already-open LucidControlAO4 and ValueVOS4 objects from the ignition backend
(_LucidBackend) so the port is never opened twice.

Voltage formula (from Dev Simulator config-testbench-sioux-tb3.json):
  voltage = logical_value * gain + offset   (clamped to 0.0 – 5.0 V)

Per-sensor parameters (verified against Dev Simulator testbench config):
  pressureCyl    (PRESSURE_400, ch 0):  gain=0.016   offset=0.5
  inclinationLat (INCLINO_LAT,  ch 1):  gain=0.132   offset=2.46
  inclinationLong(INCLINO_LONG, ch 2):  gain=0.05    offset=1.0

Usage
-----
  # Created by IgnitionController.make_sensor_output() — never instantiate directly.
  output = ign_ctrl.make_sensor_output()
  if output:
      obu_bridge.sensor_reading_changed.connect(output.update)
"""

from __future__ import annotations

from loguru import logger

from simulator.obu.j1939 import SensorId


# ── AOVO voltage clamp — hardware limit of the LucidControlAO4 ────
_AOVO_V_MIN = 0.0    # V
_AOVO_V_MAX = 5.0    # V

# ── Sensor → (channel, gain, offset) mapping ──────────────────────
# Source: config-testbench-sioux-tb3.json  /  config-dts2.0-protobuf.yaml
# Only sensors that have a physical voltage wire are listed.
# JOYSTICK_POS is a Makersan digital joystick — no AOVO channel.
_SENSOR_CHANNEL_MAP: dict[int, tuple[int, float, float]] = {
    SensorId.PRESSURE_400: (0, 0.016, 0.5),    # ch0 — pressureCyl
    SensorId.INCLINO_LAT:  (1, 0.132, 2.46),   # ch1 — inclinationLat
    SensorId.INCLINO_LONG: (2, 0.05,  1.0),    # ch2 — inclinationLong
}


class LucidSensorOutput:
    """
    Converts logical sensor values to voltages and writes them to the
    Lucid AOVO module.

    Thread-safety note: this class is called from ObuBridge (a QThread) via
    Qt signal → the slot runs on the main (GUI) thread via QueuedConnection.
    All writes therefore happen on the main thread — no locking needed.
    """

    def __init__(self, control: "LucidControlAO4", value_objs: list) -> None:
        """
        Args:
            control:    LucidControlAO4 instance (already open).
            value_objs: list of 4 ValueVOS4 objects shared with the ignition backend.
        """
        self._control    = control
        self._value_objs = value_objs
        self._connected  = True
        logger.info("[LUCID] LucidSensorOutput ready — channels 0/1/2 wired")

    # ── Public API ────────────────────────────────────────────────

    def update(self, sensor_id: int, logical_value: float) -> None:
        """
        Called whenever ObuBridge emits sensor_reading_changed.
        Converts the logical value to a voltage and writes it to the AOVO.

        Sensors without an AOVO channel (e.g. joystick) are silently ignored.
        """
        if not self._connected:
            return

        mapping = _SENSOR_CHANNEL_MAP.get(sensor_id)
        if mapping is None:
            return   # joystick or unknown sensor — no voltage output needed

        channel, gain, offset = mapping
        voltage = self._to_voltage(logical_value, gain, offset)

        self._write_channel(sensor_id, channel, voltage)

    def mark_disconnected(self) -> None:
        """
        Called when the Lucid port fails mid-session.
        Stops further writes without raising exceptions.
        """
        if self._connected:
            logger.warning(
                "[LUCID] LucidSensorOutput marked disconnected — "
                "voltage output stopped"
            )
        self._connected = False

    # ── Private helpers ───────────────────────────────────────────

    @staticmethod
    def _to_voltage(logical: float, gain: float, offset: float) -> float:
        """Apply gain/offset and clamp to hardware limits."""
        raw = logical * gain + offset
        return max(_AOVO_V_MIN, min(_AOVO_V_MAX, raw))

    def _write_channel(self, sensor_id: int, channel: int,
                       voltage: float) -> None:
        """Write voltage to one AOVO channel using a single-channel mask."""
        try:
            self._value_objs[channel].setVoltage(voltage)
            # Only write the one target channel — ignition relay (ch 3) is
            # managed by _LucidBackend and must not be disturbed.
            enabled        = [False, False, False, False]
            enabled[channel] = True
            self._control.setIoGroup(tuple(enabled), tuple(self._value_objs))
            logger.debug(
                f"[LUCID] Sensor 0x{sensor_id:02X} → ch{channel} = {voltage:.4f}V"
            )
        except Exception as ex:
            logger.error(
                f"[LUCID] Failed to write sensor 0x{sensor_id:02X} "
                f"ch{channel}: {ex}"
            )
            self._connected = False
            logger.warning(
                "[LUCID] LucidSensorOutput disconnected after write error"
            )
