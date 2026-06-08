from __future__ import annotations

"""
obu_bridge.py — OBU Bridge

Runs as a QThread. On start (IGN ON):
  - Opens the CAN bus
  - Sends cyclic heartbeat + status messages from SA=0x63 (Simulator)
  - Listens for heartbeats from real nodes; automatically fakes absent ones
  - Ramps sensor current values toward user-set targets (realistic behaviour)
  - Optionally applies per-sensor jitter (small noise, like a real sensor)

Cyclic schedule:
  100 ms  → HeartbeatEvent (all active SAs) + sensor ramp step
  500 ms  → all current sensor values + SensorDiagnostics
 1000 ms  → ProtocolVersion, StateUpdated, SafetyStatus, ToppleOver, DtsMode
             + node-presence check → auto-update fake set

Signals:
  sensor_reading_changed(sensor_id, current_value)  — emitted every ramp step
  node_status_changed(dict[int,bool])               — {SA: True=detected/False=faking}
"""

import random
import threading
import time

from PySide6.QtCore import QThread, Signal
from loguru import logger

from simulator.obu.j1939 import (
    SA_SIMULATOR,
    SensorId,
    SystemState, SystemSubState,
    DtsMode,
    encode_heartbeat,
    encode_protocol_version,
    encode_state_updated,
    encode_safety_status,
    encode_dts_mode,
    encode_topple_over_status,
    encode_body_tipped,
    encode_sensor,
    encode_sensor_diagnostics,
    PGN_EVENT,
    PGN_SENSOR,
)


# ── Node definitions (auto-detected + auto-faked) ─────────────────
NODE_DEFS = [
    (0x01, "Trailer Controller"),
    (0x02, "Gateway"),
    (0x03, "HMI"),
    (0x04, "Truck Controller"),
]

# How long without a heartbeat before we consider a node absent (seconds).
# 5 s matches the Dev Simulator and gives 50 heartbeat slots to miss before
# declaring offline — resilient to brief CAN bus congestion.
NODE_TIMEOUT = 5.0

# ── Sensor definitions (4 sensors we expose) ─────────────────────
# (sensor_id, label, unit, min_val, max_val, default, ramp_rate_per_sec)
SENSOR_DEFS = [
    (SensorId.INCLINO_LAT,   "Lateral",          "°",   -18.75, 18.75,  0.0,  2.0),
    (SensorId.INCLINO_LONG,  "Longitudinal",      "°",   -20.0,  80.0,   0.0,  2.0),
    (SensorId.PRESSURE_400,  "Cylinder Pressure", "bar", -32.0,  500.0,  0.0, 10.0),
    (SensorId.JOYSTICK_POS,  "Joystick",          "",    -1.0,   1.0,    0.0,  0.5),
]

# Quick lookup: {sensor_id: ramp_rate_per_second}
SENSOR_RAMP: dict[int, float] = {sid: ramp for sid, *_, ramp in SENSOR_DEFS}

# Quick lookup: {sensor_id: display_label}  — avoids repeated linear searches
SENSOR_LABEL: dict[int, str] = {sid: lbl for sid, lbl, *_ in SENSOR_DEFS}

# Quick lookup: {sensor_id: (min_val, max_val)} for jitter clamping
_SENSOR_RANGE: dict[int, tuple[float, float]] = {
    sid: (mn, mx) for sid, _lbl, _unit, mn, mx, *_ in SENSOR_DEFS
}

# Jitter amplitude per sensor — small noise expressed as fraction of full range.
# Mirrors the Dev Simulator BehaviorSimulator jitter logic (stepSize/1000 × ±10).
# Only applied when jitter is enabled for that sensor.
_JITTER_SIGMA: dict[int, float] = {
    SensorId.INCLINO_LAT:  0.05,   # ±0.05°  — realistic inclinometer noise
    SensorId.INCLINO_LONG: 0.05,   # ±0.05°
    SensorId.PRESSURE_400: 0.5,    # ±0.5 bar
    SensorId.JOYSTICK_POS: 0.005,  # ±0.005
}


class ObuBridge(QThread):
    """Sends OBU Bridge CAN messages on a background thread."""

    # ── Qt signals ────────────────────────────────────────────────
    # sensor_reading_changed: fired every ramp tick when current != target
    sensor_reading_changed = Signal(int, float)   # (sensor_id, current_value)
    # node_status_changed: fired each second — {sa: True=present, False=absent/faking}
    node_status_changed    = Signal(object)        # dict[int, bool]

    def __init__(
        self,
        channel: str = "PCAN_USBBUS1",
        bitrate: int = 250_000,
        profile: "PlatformProfile | None" = None,
        parent: "QThread | None" = None,
    ) -> None:
        super().__init__(parent)
        self._channel  = channel
        self._bitrate  = bitrate
        self._profile  = profile   # PlatformProfile — used for authoritative CAN backend selection
        self._running        = False
        self._stop_requested = False   # set by stop_bridge() before run() starts
        self._bus            = None
        self._can            = None   # python-can module, cached in _open_bus()

        # sensor target (set by user) and current (ramped toward target)
        self._target_values:  dict[int, float] = {
            sid: default for sid, _, __, _min, _max, default, _ramp in SENSOR_DEFS
        }
        self._current_values: dict[int, float] = dict(self._target_values)
        self._sensor_lock = threading.Lock()

        # Per-sensor jitter flag — False by default (matches Dev Simulator default).
        # Enable with set_jitter(sensor_id, True).
        self._jitter_enabled: dict[int, bool] = {
            sid: False for sid, *_ in SENSOR_DEFS
        }

        # node tracking: {sa: last_seen_timestamp}  (absent if not seen within NODE_TIMEOUT)
        # Default 0.0 means age = uptime_seconds at first check, which is always > NODE_TIMEOUT.
        # So all nodes start as ABSENT and faked immediately — this is intentional.
        # They transition to PRESENT as soon as their first heartbeat arrives on the bus.
        self._node_last_seen: dict[int, float] = {}
        self._fake_nodes:     set[int]         = set()
        self._node_lock = threading.Lock()

        # Joystick: track last received sensor message (PGN_SENSOR, sensor_id=JOYSTICK_POS).
        # Used by ConnectionMonitor to show the joystick footer pill as connected/disconnected.
        self._last_joystick_ts: float = 0.0
        self._joystick_lock = threading.Lock()

        # body / system state — written from GUI/RPC thread, read from run() thread
        # _state_lock guards all four variables as a single atomic unit.
        self._body_tipped  = False
        self._dts_mode     = DtsMode.UNKNOWN
        self._system_state = SystemState.OPERATIONAL
        self._sub_state    = SystemSubState.IDLE
        self._state_lock   = threading.Lock()

        self._msg_count    = 0

    # ── Public API ────────────────────────────────────────────────

    def set_channel(self, channel: str, bitrate: int) -> None:
        logger.info(f"[OBU] Channel updated: {channel} @ {bitrate} bps")
        self._channel = channel
        self._bitrate = bitrate

    def set_sensor_target(self, sensor_id: int, value: float,
                          direct: bool = False) -> None:
        """
        Set a new target value.

        direct=False (default): bridge ramps current → target at the sensor's
                                configured rate.  Mirrors Dev Simulator ramping.
        direct=True:            current jumps to value immediately, no ramp.
                                Useful for tests and CSV playback fast-forward.
                                Mirrors Dev Simulator value.set(direct=True).

        Thread-safe.
        """
        label = SENSOR_LABEL.get(sensor_id, f"0x{sensor_id:02X}")
        with self._sensor_lock:
            current = self._current_values.get(sensor_id, 0.0)
            self._target_values[sensor_id] = value
            if direct:
                # Jump immediately — no ramp
                self._current_values[sensor_id] = value

        if direct:
            logger.info(
                f"[OBU] Sensor direct-set: {label} = {value:.3f} "
                f"(was {current:.3f}, skipped ramp)"
            )
            # Emit immediately so UI and Lucid voltage update without waiting
            self.sensor_reading_changed.emit(sensor_id, value)
        else:
            logger.info(
                f"[OBU] Sensor target: {label} = {value:.3f}  "
                f"(current: {current:.3f})"
            )

    def set_jitter(self, sensor_id: int, enabled: bool) -> None:
        """
        Enable or disable jitter for one sensor.

        Jitter adds a small Gaussian noise to the sensor reading every ramp
        tick — mirrors real sensor noise.  Mirrors Dev Simulator
        ValueSimulator.enableJitter().

        Thread-safe.
        """
        label = SENSOR_LABEL.get(sensor_id, f"0x{sensor_id:02X}")
        with self._sensor_lock:
            self._jitter_enabled[sensor_id] = enabled
        logger.info(
            f"[OBU] Jitter {'enabled' if enabled else 'disabled'} for {label}"
        )

    def set_jitter_all(self, enabled: bool) -> None:
        """Enable or disable jitter for all sensors at once."""
        with self._sensor_lock:
            for sid in self._jitter_enabled:
                self._jitter_enabled[sid] = enabled
        logger.info(
            f"[OBU] Jitter {'enabled' if enabled else 'disabled'} for all sensors"
        )

    def get_jitter(self, sensor_id: int) -> bool:
        """Return whether jitter is enabled for the given sensor. Thread-safe."""
        with self._sensor_lock:
            return self._jitter_enabled.get(sensor_id, False)

    def get_sensor_value(self, sensor_id: int) -> float:
        """Return the current (ramped) value for one sensor. Thread-safe."""
        with self._sensor_lock:
            return self._current_values.get(sensor_id, 0.0)

    def get_all_sensor_values(self) -> dict:
        """
        Return a snapshot of current + target for every sensor.
        Thread-safe.

        Returns:
            {sensor_id (int): {"current": float, "target": float}}
        """
        with self._sensor_lock:
            return {
                sid: {
                    "current": self._current_values.get(sid, 0.0),
                    "target":  self._target_values.get(sid, 0.0),
                }
                for sid, *_ in SENSOR_DEFS
            }

    def reset_all_sensors(self) -> None:
        """Set all sensor targets to 0.0 (bridge ramps toward zero). Thread-safe."""
        with self._sensor_lock:
            for sid in self._target_values:
                self._target_values[sid] = 0.0
        logger.info("[OBU] All sensor targets reset to 0.0")

    def get_node_status(self) -> dict:
        """
        Return {sa (int): present (bool)} for all tracked nodes.
        Thread-safe.
        """
        now = time.monotonic()
        with self._node_lock:
            return {
                sa: (now - self._node_last_seen.get(sa, 0.0)) < NODE_TIMEOUT
                for sa, _ in NODE_DEFS
            }

    def get_joystick_seen_age(self) -> float:
        """
        Return seconds since the last joystick CAN sensor message was received.
        Returns float('inf') when no message has been seen yet.
        Thread-safe.
        """
        with self._joystick_lock:
            last = self._last_joystick_ts
        if last == 0.0:
            return float("inf")
        return time.monotonic() - last

    def set_system_state(
        self, state: int, sub_state: int | None = None
    ) -> None:
        """Update the system state broadcast. Thread-safe."""
        with self._state_lock:
            self._system_state = state
            if sub_state is not None:
                self._sub_state = sub_state
            logged_sub = self._sub_state
        logger.info(f"[OBU] System state → {state}  sub_state → {logged_sub}")

    def get_system_state(self) -> tuple[int, int]:
        """Return (system_state, sub_state) as a tuple of ints. Thread-safe."""
        with self._state_lock:
            return (self._system_state, self._sub_state)

    def set_dts_mode(self, mode: int) -> None:
        """Set DtsMode broadcast value. Thread-safe."""
        with self._state_lock:
            self._dts_mode = mode
        logger.info(f"[OBU] DTS mode → {mode}")

    def get_dts_mode(self) -> int:
        """Return current DtsMode int. Thread-safe."""
        with self._state_lock:
            return self._dts_mode

    def set_body_tipped(self, tipped: bool) -> None:
        """Set the BodyTipped flag. Thread-safe."""
        with self._state_lock:
            self._body_tipped = tipped
        logger.info(f"[OBU] Body tipped → {tipped}")

    def get_body_tipped(self) -> bool:
        """Return current BodyTipped flag. Thread-safe."""
        with self._state_lock:
            return self._body_tipped

    def broadcast_ignition_off(self) -> None:
        """
        Send one IGNITION_OFF StateUpdated message on the bus before stopping.

        Called by IGN OFF handler so the GW/HMI receives a clean shutdown
        notification.  Mirrors Dev Simulator behaviour where SystemState
        transitions to IGNITION_OFF before the bridge halts.
        """
        logger.info("[OBU] Broadcasting IGNITION_OFF state before shutdown")
        with self._state_lock:
            self._system_state = SystemState.IGNITION_OFF
            self._sub_state    = SystemSubState.DEACTIVATED
        if self._bus:
            with self._node_lock:
                fake_sas = frozenset(self._fake_nodes)
            all_sas = {SA_SIMULATOR} | fake_sas
            for sa in sorted(all_sas):
                self._tx(*encode_state_updated(
                    SystemState.IGNITION_OFF, SystemSubState.DEACTIVATED, sa=sa
                ))
        logger.debug("[OBU] IGNITION_OFF CAN frame(s) sent")

    def stop_bridge(self) -> None:
        logger.info("[OBU] stop_bridge() called")
        self._stop_requested = True   # safe to call before or during run()
        self._running = False

    # ── QThread run ───────────────────────────────────────────────

    def run(self) -> None:
        logger.info(f"[OBU] Starting on {self._channel} @ {self._bitrate} bps")
        # Reset state for clean start — protected by _state_lock
        self._stop_requested = False
        with self._state_lock:
            self._system_state = SystemState.OPERATIONAL
            self._sub_state    = SystemSubState.IDLE

        if not self._open_bus():
            return

        # Guard: stop_bridge() may have been called while bus was opening
        if self._stop_requested:
            logger.info("[OBU] Stop requested before loop — aborting start")
            self._close_bus()
            return

        self._running = True
        logger.info("[OBU] Bridge running")

        sensor_tick = 0
        second_tick = 0
        t_msg_stat  = time.monotonic()

        while self._running:
            t0 = time.monotonic()

            # ── Receive — detect real nodes ───────────────────────
            self._rx_drain()

            # ── Ramp sensors (+ optional jitter) ──────────────────
            self._ramp_sensors()

            # ── 100ms: heartbeat (simulator + fake nodes) ─────────
            with self._node_lock:
                fake_sas = frozenset(self._fake_nodes)

            self._tx(*encode_heartbeat(SA_SIMULATOR))
            for sa in fake_sas:
                self._tx(*encode_heartbeat(sa))

            # ── 500ms: sensor broadcast ───────────────────────────
            sensor_tick += 1
            if sensor_tick >= 5:
                sensor_tick = 0
                self._send_all_sensors()

            # ── 1000ms: state msgs + node check ───────────────────
            second_tick += 1
            if second_tick >= 10:
                second_tick = 0
                all_sas = {SA_SIMULATOR} | fake_sas
                for sa in sorted(all_sas):
                    self._send_1s_messages(sa)
                self._update_fake_nodes()

            # ── Stats: log messages/sec every second at DEBUG level ──
            now = time.monotonic()
            if now - t_msg_stat >= 1.0:
                logger.debug(f"[OBU] TX rate: {self._msg_count} msg/s")
                self._msg_count = 0
                t_msg_stat = now

            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, 0.100 - elapsed))

        self._close_bus()
        logger.info("[OBU] Bridge stopped")

    # ── Sensor ramping + jitter ───────────────────────────────────

    def _ramp_sensors(self) -> None:
        """Step each sensor current value toward its target; apply jitter if enabled."""
        TICK = 0.100   # seconds per ramp step
        with self._sensor_lock:
            targets  = dict(self._target_values)
            currents = dict(self._current_values)
            jitter   = dict(self._jitter_enabled)

        changed = {}
        for sid, target in targets.items():
            current   = currents.get(sid, target)
            ramp_rate = SENSOR_RAMP.get(sid, 1.0)
            step      = ramp_rate * TICK
            diff      = target - current

            if abs(diff) <= step:
                new_val = target
            else:
                new_val = current + step * (1.0 if diff > 0 else -1.0)

            # Apply jitter after ramping (like Dev Simulator __applyJitter after __applyRamping)
            if jitter.get(sid, False):
                sigma   = _JITTER_SIGMA.get(sid, 0.01)
                new_val = new_val + random.gauss(0.0, sigma)
                # Clamp to sensor range using pre-built range lookup
                if sid in _SENSOR_RANGE:
                    mn, mx = _SENSOR_RANGE[sid]
                    new_val = max(mn, min(mx, new_val))

            if abs(new_val - current) > 1e-6:
                changed[sid] = new_val

        if changed:
            with self._sensor_lock:
                self._current_values.update(changed)
            for sid, val in changed.items():
                # Log when sensor reaches its target (no jitter, exact match)
                target = targets.get(sid, val)
                if abs(val - target) < 1e-6:
                    label = SENSOR_LABEL.get(sid, f"0x{sid:02X}")
                    logger.debug(f"[OBU] Sensor {label} reached target {val:.3f}")
                self.sensor_reading_changed.emit(sid, val)

    # ── Node detection ────────────────────────────────────────────

    def _rx_drain(self) -> None:
        """Read all pending messages; record heartbeats and joystick frames."""
        if not self._bus:
            return
        try:
            while True:
                msg = self._bus.recv(timeout=0)
                if msg is None:
                    break
                sa  = msg.arbitration_id & 0xFF
                pgn = (msg.arbitration_id >> 8) & 0xFFFF

                # Track nodes that send PGN_EVENT heartbeats (SA must be in NODE_DEFS)
                if pgn == PGN_EVENT and sa in {nd[0] for nd in NODE_DEFS}:
                    with self._node_lock:
                        self._node_last_seen[sa] = time.monotonic()

                # Track joystick presence via PGN_SENSOR messages.
                # Wire format: bytes 0-1 = sensor_id (uint16 LE).
                if pgn == PGN_SENSOR and len(msg.data) >= 2:
                    sensor_id_in_msg = int.from_bytes(msg.data[:2], "little")
                    if sensor_id_in_msg == SensorId.JOYSTICK_POS:
                        with self._joystick_lock:
                            self._last_joystick_ts = time.monotonic()
                        logger.debug("[OBU] Joystick CAN frame received")

        except Exception as e:
            logger.debug(f"[OBU] RX drain error: {e}")

    def _update_fake_nodes(self) -> None:
        """Determine absent nodes → update fake set → emit only on change."""
        now   = time.monotonic()
        status: dict[int, bool] = {}
        new_fake: set[int] = set()

        with self._node_lock:
            for sa, name in NODE_DEFS:
                last    = self._node_last_seen.get(sa, 0.0)
                age     = now - last
                present = age < NODE_TIMEOUT
                status[sa] = present
                if not present:
                    new_fake.add(sa)
                logger.debug(
                    f"[OBU] Node {name} (SA=0x{sa:02X}): "
                    f"{'PRESENT' if present else 'ABSENT'} "
                    f"(last seen {age:.1f}s ago)"
                )

            changed = new_fake != self._fake_nodes
            self._fake_nodes = new_fake

        if changed:
            faking = [name for sa, name in NODE_DEFS if sa in new_fake]
            present_names = [name for sa, name in NODE_DEFS if sa not in new_fake]
            logger.info(
                f"[OBU] Node status changed → "
                f"present: {present_names or ['none']}  "
                f"faking: {faking or ['none']}"
            )
            self.node_status_changed.emit(status)

    # ── Private CAN helpers ───────────────────────────────────────

    def _open_bus(self) -> bool:
        try:
            import can as _can_mod
            self._can = _can_mod
            self._bus = _can_mod.Bus(
                channel=self._channel,
                interface=self._detect_interface(),
                bitrate=self._bitrate,
            )
            logger.info(f"[OBU] CAN bus open: {self._channel}")
            return True
        except ImportError:
            logger.warning("[OBU] python-can not installed — dry-run mode")
            self._bus = _DryRunBus()
            self._can = None
            return True
        except Exception as e:
            logger.error(f"[OBU] Failed to open CAN bus: {e}")
            return False

    def _detect_interface(self) -> str:
        """
        Resolve the python-can interface name.
        Uses profile.can_backend if available (preferred — authoritative).
        Falls back to channel name heuristic for tests / scripts without a profile.
        """
        if self._profile is not None:
            iface = self._profile.can_backend.value
            logger.debug(f"[OBU] Interface resolved from PlatformProfile: {iface}")
            return iface
        ch = self._channel.lower()
        if ch.startswith("pcan"):
            logger.debug("[OBU] Interface resolved by channel name heuristic: pcan")
            return "pcan"
        if ch.startswith("vector"):
            logger.debug("[OBU] Interface resolved by channel name heuristic: vector")
            return "vector"
        logger.debug("[OBU] Interface resolved by channel name heuristic: socketcan")
        return "socketcan"

    def _close_bus(self) -> None:
        try:
            if self._bus:
                self._bus.shutdown()
                self._bus = None
        except Exception as e:
            logger.warning(f"[OBU] Bus shutdown error: {e}")

    def _tx(self, arb_id: int, data: bytes) -> None:
        if self._can is None:
            return   # dry-run mode — discard silently
        try:
            msg = self._can.Message(
                arbitration_id=arb_id, data=data, is_extended_id=True
            )
            self._bus.send(msg)
            self._msg_count += 1
            self._tx_error_count = 0   # reset on successful send
        except Exception as e:
            self._tx_error_count = getattr(self, "_tx_error_count", 0) + 1
            # Log on first error and every 100th repeat to avoid flooding
            if self._tx_error_count == 1 or self._tx_error_count % 100 == 0:
                logger.warning(
                    f"[OBU] TX error (×{self._tx_error_count}): {e} "
                    f"— arb_id=0x{arb_id:08X} data={data.hex()}"
                )

    def _send_all_sensors(self) -> None:
        with self._sensor_lock:
            snapshot = dict(self._current_values)
        for sid, val in snapshot.items():
            self._tx(*encode_sensor(sid, val))
            self._tx(*encode_sensor_diagnostics(sid))

    def _send_1s_messages(self, sa: int) -> None:
        with self._state_lock:
            system_state = self._system_state
            sub_state    = self._sub_state
            dts_mode     = self._dts_mode
            body_tipped  = self._body_tipped
        self._tx(*encode_protocol_version(sa=sa))
        self._tx(*encode_state_updated(system_state, sub_state, sa=sa))
        self._tx(*encode_safety_status(sa=sa))
        self._tx(*encode_topple_over_status(sa=sa))
        self._tx(*encode_dts_mode(dts_mode, sa=sa))
        if sa == SA_SIMULATOR:
            self._tx(*encode_body_tipped(body_tipped))


# ── Dry-run bus for no-hardware mode ─────────────────────────────

class _DryRunBus:
    """
    No-op CAN bus used when python-can is not installed.

    All methods silently discard their arguments so the bridge runs
    through its full cyclic loop without hardware.  recv() always
    returns None so no real nodes are ever detected.
    """

    def recv(self, timeout: float = 0) -> None:
        return None

    def send(self, msg: "can.Message") -> None:
        pass

    def shutdown(self) -> None:
        pass
