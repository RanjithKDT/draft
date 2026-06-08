"""
simulator/rpc/rpc_server.py
===========================
rpyc-based RPC server for the Hyva Simulator.
Listens on 0.0.0.0:18200.

Exposes 22 functions for automation / pytest / behave hooks.

Usage from test code:
    import rpyc
    conn = rpyc.connect("localhost", 18200)
    r    = conn.root

    r.ping()                                 # "pong @ 2026-03-13T08:00:00+00:00"
    r.set_ignition(True)                     # bool — hardware ack
    r.set_sensor_target(0x04, 5.0)          # INCLINO_LAT = 5°
    r.get_all_sensor_values()               # dict {sid: {current, target}}
    r.load_playback("/path/to/file.csv")    # dict — load summary
    r.start_playback()
    r.get_playback_status()                 # dict — {state, row, total, speed, …}
    r.stop_playback()
    conn.close()

All methods return plain Python types (dict, list, str, float, int, bool).
rpyc serialises these transparently; no netref / remote objects are returned.

Architecture notes
------------------
- SimulatorService is instantiated per connection by rpyc.ThreadedServer.
- All shared mutable state lives in the module-level _Context singleton.
- Every subsystem method called from here is already thread-safe in its own
  module, so this layer only needs locks for its own counters / log.
- The RpcServer wrapper never imports rpyc at module level — the import is
  deferred to start() so missing rpyc never crashes startup.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

# ── Constants ─────────────────────────────────────────────────────────────────

RPC_HOST = "0.0.0.0"   # listen on all interfaces (localhost + LAN)
RPC_PORT = 18200


# ── Shared context (module-level singleton) ───────────────────────────────────
# Set once by RpcServer before start(); read many times by service instances.

@dataclass
class _Context:
    bridge:    Any = None    # ObuBridge | None
    ign_ctrl:  Any = None    # IgnitionController | None
    profile:   Any = None    # PlatformProfile | None

    # CsvPlayer owned by RPC (independent from the GUI PlaybackPage player)
    csv_player:       Any           = None
    csv_player_wired: bool          = False   # prevent double-connect on Signal

    # Ring-buffer call log — polled by RpcPage every 500ms
    call_log:  deque                = field(default_factory=lambda: deque(maxlen=100))
    log_lock:  threading.Lock       = field(default_factory=threading.Lock)

    # Active connection count
    conn_count: int                 = 0
    conn_lock:  threading.Lock      = field(default_factory=threading.Lock)


_ctx = _Context()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _log_call(func: str, args: str, result: str) -> None:
    """Append a record to the ring buffer and emit a DEBUG log line."""
    record = {
        "time":   datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "func":   func,
        "args":   args,
        "result": result,
    }
    with _ctx.log_lock:
        _ctx.call_log.appendleft(record)   # newest first — GUI shows row 0 at top
    logger.debug(f"[RPC] {func}({args}) → {result}")


def _require_bridge(name: str) -> None:
    """Raise a descriptive RuntimeError if the ObuBridge is not running."""
    if _ctx.bridge is None:
        raise RuntimeError(
            f"[RPC] {name}: ObuBridge is not running. "
            "Start the bridge via the CAN page or connect a CAN adapter."
        )


def _require_ign(name: str) -> None:
    """Raise a descriptive RuntimeError if IgnitionController is unavailable."""
    if _ctx.ign_ctrl is None:
        raise RuntimeError(
            f"[RPC] {name}: IgnitionController is not available on this platform."
        )


def _require_player(name: str) -> None:
    """Raise a descriptive RuntimeError if no CSV file has been loaded."""
    if _ctx.csv_player is None:
        raise RuntimeError(
            f"[RPC] {name}: No CSV file loaded. "
            "Call load_playback('/path/to/file.csv') first."
        )


# ── Service class (one instance per rpyc connection) ─────────────────────────

class SimulatorService:   # rpyc.Service injected at start-time; see RpcServer.start()
    """
    Exposed RPC surface — 22 functions.

    Named with the rpyc convention:  exposed_<name>  →  conn.root.<name>()
    Only methods prefixed with exposed_ are accessible from the network.
    All other methods / attributes are private and never serialised.
    """

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def on_connect(self, conn: object) -> None:  # noqa: N802 — rpyc naming
        with _ctx.conn_lock:
            _ctx.conn_count += 1
        logger.info(f"[RPC] Client connected   — active: {_ctx.conn_count}")

    def on_disconnect(self, conn: object) -> None:  # noqa: N802
        with _ctx.conn_lock:
            _ctx.conn_count = max(0, _ctx.conn_count - 1)
        logger.info(f"[RPC] Client disconnected — active: {_ctx.conn_count}")

    # ── 1. ping ───────────────────────────────────────────────────────────────

    def exposed_ping(self) -> str:
        """Health check. Returns 'pong @ <ISO-UTC-timestamp>'."""
        ts     = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result = f"pong @ {ts}"
        _log_call("ping", "", result)
        return result

    # ── 2. get_status ─────────────────────────────────────────────────────────

    def exposed_get_status(self) -> dict:
        """
        Full simulator snapshot.

        Returns:
            bridge_running (bool)
            ign_on         (bool)
            sensors        {sid_hex: {current: float, target: float, label: str, unit: str}}
            nodes          {sa_hex:  {name: str, present: bool}}
            playback       {state: str, total_rows: int, speed: float, duration_s: float}
            rpc_clients    (int)
        """
        bridge_ok = _ctx.bridge is not None

        # Sensors
        if bridge_ok:
            raw_sensors = _ctx.bridge.get_all_sensor_values()
            from simulator.obu.obu_bridge import SENSOR_DEFS
            label_map = {sid: (lbl, unit) for sid, lbl, unit, *_ in SENSOR_DEFS}
            sensors = {
                f"0x{sid:02X}": {
                    "current": vals["current"],
                    "target":  vals["target"],
                    "label":   label_map.get(sid, ("", ""))[0],
                    "unit":    label_map.get(sid, ("", ""))[1],
                }
                for sid, vals in raw_sensors.items()
            }
        else:
            sensors = {}

        # Nodes
        if bridge_ok:
            raw_nodes = _ctx.bridge.get_node_status()
            from simulator.obu.obu_bridge import NODE_DEFS
            name_map  = {sa: name for sa, name in NODE_DEFS}
            nodes = {
                f"0x{sa:02X}": {"name": name_map.get(sa, f"SA_{sa}"), "present": present}
                for sa, present in raw_nodes.items()
            }
        else:
            nodes = {}

        # Playback
        player = _ctx.csv_player
        info   = player.get_playback_info() if player is not None else None
        if info is None:
            playback = {"state": "unloaded", "total_rows": 0, "speed": 1.0, "duration_s": 0.0}
        else:
            playback = {
                "state":      player.playback_state(),
                "total_rows": info.total_rows,
                "speed":      player.get_speed(),
                "duration_s": info.duration_s,
            }

        result = {
            "bridge_running": bridge_ok,
            "ign_on":         _ctx.ign_ctrl.is_on() if _ctx.ign_ctrl else False,
            "sensors":        sensors,
            "nodes":          nodes,
            "playback":       playback,
            "rpc_clients":    _ctx.conn_count,
        }
        _log_call("get_status", "", f"bridge={'on' if bridge_ok else 'off'}")
        return result

    # ── 3. get_platform_info ──────────────────────────────────────────────────

    def exposed_get_platform_info(self) -> dict:
        """OS, CAN backend, display label from the PlatformProfile."""
        p = _ctx.profile
        if p is None:
            result = {"error": "No platform profile available"}
        else:
            result = {
                "operating_system":     p.operating_system.name,
                "can_backend":          p.can_backend.value,
                "can_channel":          p.can_channel,
                "hal_type":             p.hal_type.name,
                "display_label":        p.display_label,
                "hardware_description": p.hardware_description,
            }
        _log_call("get_platform_info", "", result.get("display_label", "?"))
        return result

    # ── 4. set_ignition ───────────────────────────────────────────────────────

    def exposed_set_ignition(self, on: bool) -> bool:
        """
        Set ignition (K15).

        Returns:
            True if hardware acknowledged, False if software-only mode.
        """
        _require_ign("set_ignition")
        on  = bool(on)
        ok  = _ctx.ign_ctrl.set_ignition(on)
        _log_call("set_ignition", str(on), str(ok))
        return ok

    # ── 5. get_ignition ───────────────────────────────────────────────────────

    def exposed_get_ignition(self) -> bool:
        """Return current ignition state (True = ON)."""
        result = _ctx.ign_ctrl.is_on() if _ctx.ign_ctrl else False
        _log_call("get_ignition", "", str(result))
        return result

    # ── 6. set_sensor_target ─────────────────────────────────────────────────

    def exposed_set_sensor_target(self, sensor_id: int, value: float,
                                   direct: bool = False) -> None:
        """
        Set a sensor ramp target.

        Args:
            sensor_id: e.g. 0x04 (INCLINO_LAT), 0x03 (INCLINO_LONG),
                            0x01 (PRESSURE_400), 0x09 (JOYSTICK_POS)
            value:     target value in the sensor's native unit
            direct:    True = jump immediately (no ramp); False = ramp (default)
        """
        _require_bridge("set_sensor_target")
        _ctx.bridge.set_sensor_target(int(sensor_id), float(value), bool(direct))
        _log_call("set_sensor_target",
                  f"0x{sensor_id:02X}, {value:.3f}, direct={direct}", "ok")

    # ── 7. get_sensor_value ───────────────────────────────────────────────────

    def exposed_get_sensor_value(self, sensor_id: int) -> float:
        """Return the current (ramped) value for one sensor."""
        _require_bridge("get_sensor_value")
        result = _ctx.bridge.get_sensor_value(int(sensor_id))
        _log_call("get_sensor_value", f"0x{sensor_id:02X}", f"{result:.4f}")
        return result

    # ── 8. get_all_sensor_values ──────────────────────────────────────────────

    def exposed_get_all_sensor_values(self) -> dict:
        """
        Return current + target values for all 4 sensors.

        Returns:
            {sensor_id (int): {"current": float, "target": float}}
        """
        _require_bridge("get_all_sensor_values")
        result = _ctx.bridge.get_all_sensor_values()
        _log_call("get_all_sensor_values", "", f"{len(result)} sensors")
        return result

    # ── 9. reset_all_sensors ─────────────────────────────────────────────────

    def exposed_reset_all_sensors(self) -> None:
        """Set all sensor targets to 0.0 (bridge ramps toward zero)."""
        _require_bridge("reset_all_sensors")
        _ctx.bridge.reset_all_sensors()
        _log_call("reset_all_sensors", "", "ok")

    # ── 9a. set_jitter ───────────────────────────────────────────────────────

    def exposed_set_jitter(self, sensor_id: int, enabled: bool) -> None:
        """
        Enable or disable jitter for one sensor.

        Jitter adds small Gaussian noise to the sensor reading every tick —
        mirrors real sensor noise and the Dev Simulator's jitter feature.

        Args:
            sensor_id: sensor to configure (e.g. 0x04 for INCLINO_LAT)
            enabled:   True = add noise, False = clean output
        """
        _require_bridge("set_jitter")
        _ctx.bridge.set_jitter(int(sensor_id), bool(enabled))
        _log_call("set_jitter", f"0x{sensor_id:02X}, {enabled}", "ok")

    # ── 9b. set_jitter_all ───────────────────────────────────────────────────

    def exposed_set_jitter_all(self, enabled: bool) -> None:
        """Enable or disable jitter for all sensors at once."""
        _require_bridge("set_jitter_all")
        _ctx.bridge.set_jitter_all(bool(enabled))
        _log_call("set_jitter_all", str(enabled), "ok")

    # ── 10. set_system_state ─────────────────────────────────────────────────

    def exposed_set_system_state(
        self, state: int, sub_state: Optional[int] = None
    ) -> None:
        """
        Set the SystemState broadcast by the simulator.

        Args:
            state:     SystemState int (0=INITIALIZATION … 8=IGNITION_OFF)
            sub_state: SystemSubState int (0=DEACTIVATED, 1=IDLE) — optional
        """
        _require_bridge("set_system_state")
        _ctx.bridge.set_system_state(int(state), sub_state)
        _log_call("set_system_state", f"{state}, {sub_state}", "ok")

    # ── 11. get_system_state ─────────────────────────────────────────────────

    def exposed_get_system_state(self) -> dict:
        """Return {"state": int, "sub_state": int}."""
        _require_bridge("get_system_state")
        state, sub = _ctx.bridge.get_system_state()
        result = {"state": state, "sub_state": sub}
        _log_call("get_system_state", "", str(result))
        return result

    # ── 12. set_dts_mode ─────────────────────────────────────────────────────

    def exposed_set_dts_mode(self, mode: int) -> None:
        """Set DtsMode (0=UNKNOWN, 1=CONNECT, 6=CONTROL)."""
        _require_bridge("set_dts_mode")
        _ctx.bridge.set_dts_mode(int(mode))
        _log_call("set_dts_mode", str(mode), "ok")

    # ── 13. get_dts_mode ─────────────────────────────────────────────────────

    def exposed_get_dts_mode(self) -> int:
        """Return current DtsMode int."""
        _require_bridge("get_dts_mode")
        result = _ctx.bridge.get_dts_mode()
        _log_call("get_dts_mode", "", str(result))
        return result

    # ── 14. set_body_tipped ──────────────────────────────────────────────────

    def exposed_set_body_tipped(self, tipped: bool) -> None:
        """Set the BodyTipped flag in CAN broadcasts."""
        _require_bridge("set_body_tipped")
        _ctx.bridge.set_body_tipped(bool(tipped))
        _log_call("set_body_tipped", str(tipped), "ok")

    # ── 15. get_body_tipped ──────────────────────────────────────────────────

    def exposed_get_body_tipped(self) -> bool:
        """Return current BodyTipped flag."""
        _require_bridge("get_body_tipped")
        result = _ctx.bridge.get_body_tipped()
        _log_call("get_body_tipped", "", str(result))
        return result

    # ── 16. get_node_status ───────────────────────────────────────────────────

    def exposed_get_node_status(self) -> dict:
        """
        Return presence status for all tracked J1939 nodes.

        Returns:
            {"0x01": {"name": "Trailer Controller", "present": False}, …}
        """
        _require_bridge("get_node_status")
        raw = _ctx.bridge.get_node_status()
        from simulator.obu.obu_bridge import NODE_DEFS
        name_map = {sa: name for sa, name in NODE_DEFS}
        result = {
            f"0x{sa:02X}": {"name": name_map.get(sa, f"SA_{sa}"), "present": present}
            for sa, present in raw.items()
        }
        _log_call("get_node_status", "", f"{len(result)} nodes")
        return result

    # ── 17. load_playback ────────────────────────────────────────────────────

    def exposed_load_playback(self, path: str) -> dict:
        """
        Validate a CSV scenario file and prepare it for playback.
        Must be called before start_playback().

        Args:
            path: absolute or relative path to the CSV file

        Returns:
            {path, total_rows, duration_s, has_time_col, sensor_ids, unmapped}

        Raises:
            ValueError if the file is invalid (not found, no sensor columns, etc.)
        """
        from simulator.playback.csv_player import CsvPlayer
        p      = Path(path)
        player = CsvPlayer()
        try:
            info = player.load(p)
        except ValueError as ex:
            _log_call("load_playback", str(p.name), f"ERROR: {ex}")
            raise

        # Discard any previous player (stop it first if running)
        if _ctx.csv_player is not None:
            _ctx.csv_player.stop()
        _ctx.csv_player       = player
        _ctx.csv_player_wired = False   # reset wire flag for new player

        result = {
            "path":         str(info.path),
            "total_rows":   info.total_rows,
            "duration_s":   round(info.duration_s, 3),
            "has_time_col": info.has_time_col,
            "sensor_ids":   [f"0x{sid:02X}" for sid in info.sensor_ids],
            "unmapped":     info.column_map.unmapped,
        }
        _log_call("load_playback", p.name, f"{info.total_rows} rows")
        return result

    # ── 18. start_playback ───────────────────────────────────────────────────

    def exposed_start_playback(self) -> None:
        """
        Start (or resume) CSV playback.
        Sensor values are forwarded to the ObuBridge on every row.

        Raises:
            RuntimeError if no file loaded or bridge not running
        """
        _require_player("start_playback")
        _require_bridge("start_playback")

        # Wire sensor values to bridge exactly once per player instance.
        # Use direct=True: the CSV player controls timing; ramping here
        # would fight the playback speed and give inaccurate results.
        if not _ctx.csv_player_wired:
            def _dispatch(values: dict) -> None:
                if _ctx.bridge:
                    for sid, val in values.items():
                        _ctx.bridge.set_sensor_target(sid, val, direct=True)
            _ctx.csv_player.sensor_values.connect(_dispatch)
            _ctx.csv_player_wired = True

        _ctx.csv_player.play()
        _log_call("start_playback", "", "ok")

    # ── 19. pause_playback ───────────────────────────────────────────────────

    def exposed_pause_playback(self) -> None:
        """Pause playback (thread stays alive, resumes on start_playback())."""
        _require_player("pause_playback")
        _ctx.csv_player.pause()
        _log_call("pause_playback", "", "ok")

    # ── 20. resume_playback ──────────────────────────────────────────────────

    def exposed_resume_playback(self) -> None:
        """Resume a paused playback. Equivalent to start_playback() when paused."""
        _require_player("resume_playback")
        _ctx.csv_player.play()
        _log_call("resume_playback", "", "ok")

    # ── 21. stop_playback ────────────────────────────────────────────────────

    def exposed_stop_playback(self) -> None:
        """Stop playback and terminate the player thread."""
        if _ctx.csv_player is not None:
            _ctx.csv_player.stop()
        _log_call("stop_playback", "", "ok")

    # ── 22. get_playback_status ───────────────────────────────────────────────

    def exposed_get_playback_status(self) -> dict:
        """
        Return current playback state.

        Returns:
            {state: "unloaded"|"stopped"|"playing"|"paused"|"finished",
             total_rows: int, speed: float, duration_s: float}
        """
        player = _ctx.csv_player
        info   = player.get_playback_info() if player is not None else None
        if info is None:
            result = {
                "state": "unloaded", "total_rows": 0,
                "speed": 1.0, "duration_s": 0.0,
            }
        else:
            result = {
                "state":      player.playback_state(),
                "total_rows": info.total_rows,
                "speed":      player.get_speed(),
                "duration_s": info.duration_s,
            }
        _log_call("get_playback_status", "", result["state"])
        return result


# ── RPC server wrapper ────────────────────────────────────────────────────────

class RpcServer:
    """
    Wraps rpyc.ThreadedServer in a background daemon thread.

    Lifecycle:
        server = RpcServer()
        server.set_bridge(bridge)
        server.set_ign_ctrl(ctrl)
        server.set_profile(profile)
        ok = server.start()         # False if rpyc not installed
        ...
        server.stop()               # called at shutdown

    rpyc is imported lazily in start() so a missing install never crashes startup.
    The GUI shows the server as "unavailable" if rpyc is missing.
    """

    def __init__(self, host: str = RPC_HOST, port: int = RPC_PORT) -> None:
        self._host    = host
        self._port    = port
        self._server  = None          # rpyc.ThreadedServer instance
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ── Dependency injection ──────────────────────────────────────────────────

    def set_bridge(self, bridge: "ObuBridge | None") -> None:
        """Inject (or clear) the ObuBridge reference. Safe to call at any time."""
        _ctx.bridge = bridge
        logger.debug(f"[RPC] ObuBridge {'injected' if bridge else 'cleared'}")

    def set_ign_ctrl(self, ctrl: "IgnitionController | None") -> None:
        """Inject (or clear) the IgnitionController reference."""
        _ctx.ign_ctrl = ctrl
        logger.debug(f"[RPC] IgnitionController {'injected' if ctrl else 'cleared'}")

    def set_profile(self, profile: "PlatformProfile | None") -> None:
        """Inject the PlatformProfile for exposed_get_platform_info()."""
        _ctx.profile = profile
        logger.debug(
            f"[RPC] PlatformProfile injected: "
            f"{profile.display_label if profile else 'None'}"
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> bool:
        """
        Start the rpyc ThreadedServer on a daemon thread.

        Returns:
            True  — server listening
            False — rpyc not installed, or port already in use
        """
        try:
            import rpyc
            from rpyc.utils.server import ThreadedServer
        except ImportError:
            logger.warning("[RPC] rpyc not installed — RPC server unavailable")
            logger.warning("[RPC] Install with:  pip install rpyc>=6.0.0")
            return False

        # Build a service class that rpyc can instantiate per-connection.
        # We inject the module-level context via class-level reference.
        service_cls = type(
            "HyvaSimulatorService",
            (rpyc.Service,),
            {k: v for k, v in vars(SimulatorService).items() if not k.startswith("__")},
        )

        try:
            self._server = ThreadedServer(
                service_cls,
                hostname=self._host,
                port=self._port,
                protocol_config={
                    "allow_all_attrs":    False,
                    "allow_public_attrs": True,
                    "sync_request_timeout": 30,
                },
            )
        except OSError as ex:
            logger.error(f"[RPC] Cannot bind {self._host}:{self._port} — {ex}")
            return False
        except Exception as ex:
            logger.error(f"[RPC] Server init failed: {ex}")
            return False

        self._thread = threading.Thread(
            target=self._server.start,
            name="RpcServer",
            daemon=True,     # exits automatically when main thread exits
        )
        self._running = True
        self._thread.start()
        logger.info(f"[RPC] Listening on {self._host}:{self._port}")
        return True

    def stop(self) -> None:
        """Close the server socket and let the daemon thread exit naturally."""
        if self._server is not None and self._running:
            try:
                self._server.close()
            except Exception as ex:
                logger.warning(f"[RPC] Stop error: {ex}")
            self._running = False
            self._server  = None
            logger.info("[RPC] Server stopped")

    # ── Status API (polled by RpcPage every 500ms) ────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def address(self) -> str:
        return f"{self._host}:{self._port}"

    def get_call_log(self) -> list[dict]:
        """Return a snapshot of the call ring-buffer (newest first, up to 100)."""
        with _ctx.log_lock:
            return list(_ctx.call_log)

    def get_conn_count(self) -> int:
        with _ctx.conn_lock:
            return _ctx.conn_count
