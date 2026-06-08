"""
simulator/playback/csv_player.py
=================================
QThread that replays a CSV scenario file by emitting sensor values at the
correct wall-clock intervals, scaled by a user-selectable speed factor.

CSV format
----------
The file must have a header row.  Column names are matched case-insensitively
with common aliases so the team can use whatever logging tool produced the file.

Recognised column aliases (any unambiguous prefix also works):
  timestamp / time / t / elapsed_s        → time column (seconds, float)
  inclino_lat   / lateral   / lat          → SensorId 0x04
  inclino_long  / longitudinal / long      → SensorId 0x03
  pressure_400  / pressure  / cyl_press   → SensorId 0x01
  joystick_pos  / joystick  / joy          → SensorId 0x09

Unmapped columns are silently ignored.
Missing sensor columns in a row are silently skipped (last value held).

Signals
-------
  row_changed(int, int)         current_row, total_rows — for scrubber / progress
  sensor_values(dict)           {sensor_id: float}      — connect to bridge
  playback_finished()           end of file reached
  error_occurred(str)           fatal parse / IO error

Public API
----------
  load(path)              → PlaybackInfo | raises ValueError
  play() / pause() / stop()
  set_speed(float)        0.25 … 10.0
  seek(row_index)
"""

from __future__ import annotations

import csv
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from loguru import logger

from simulator.obu.j1939 import SensorId
from simulator.obu.obu_bridge import SENSOR_DEFS as _SENSOR_DEFS


# ── Column alias tables ───────────────────────────────────────────────────────

_TIME_ALIASES: tuple[str, ...] = (
    "timestamp", "time", "elapsed", "elapsed_s", "t", "ts",
)

_SENSOR_ALIASES: dict[int, tuple[str, ...]] = {
    SensorId.INCLINO_LAT:  ("inclino_lat",  "lateral",       "lat",  "inclinolat"),
    SensorId.INCLINO_LONG: ("inclino_long", "longitudinal",  "long", "inclinolong"),
    SensorId.PRESSURE_400: ("pressure_400", "pressure",      "cyl",  "cyl_press", "cylpressure"),
    SensorId.JOYSTICK_POS: ("joystick_pos", "joystick",      "joy",  "joystickpos"),
}

_SENSOR_META: dict[int, tuple[str, str, float, float]] = {
    sid: (label, unit, mn, mx)
    for sid, label, unit, mn, mx, *_ in _SENSOR_DEFS
}

SPEED_OPTIONS: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 5.0, 10.0)

# Maximum rows accepted into RAM.  A 50 Hz × 4-sensor CSV for 30 minutes
# is ~90 000 rows / ~20 MB — well within limits.  1 000 000 rows > 200 MB;
# refuse early with a clear message rather than silently OOM.
MAX_CSV_ROWS = 1_000_000


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class ColumnMap:
    """Which CSV column index maps to which sensor id."""
    time_col:    Optional[int]              # None → use row index × default dt
    sensor_cols: dict[int, int]             # {sensor_id: col_index}
    all_headers: list[str]                  = field(default_factory=list)
    unmapped:    list[str]                  = field(default_factory=list)


@dataclass
class PlaybackInfo:
    """Metadata returned by load() so the UI can show a preview."""
    path:           Path
    total_rows:     int
    duration_s:     float           # 0.0 if no time column
    column_map:     ColumnMap
    has_time_col:   bool
    sensor_ids:     list[int]       # which sensors are covered by this file


# ── Column header matcher ─────────────────────────────────────────────────────

def _normalise(h: str) -> str:
    """Lowercase, strip spaces and underscores for fuzzy matching."""
    return h.lower().replace(" ", "").replace("_", "").replace("-", "")


def _match_time(header: str) -> bool:
    n = _normalise(header)
    return any(n == _normalise(a) or n.startswith(_normalise(a)) for a in _TIME_ALIASES)


def _match_sensor(header: str) -> Optional[int]:
    """Return sensor_id if header matches any alias, else None."""
    n = _normalise(header)
    for sid, aliases in _SENSOR_ALIASES.items():
        for alias in aliases:
            na = _normalise(alias)
            if n == na or n.startswith(na):
                return sid
    return None


def _build_column_map(headers: list[str]) -> ColumnMap:
    time_col:    Optional[int]    = None
    sensor_cols: dict[int, int]   = {}
    unmapped:    list[str]        = []

    for i, h in enumerate(headers):
        if time_col is None and _match_time(h):
            time_col = i
            continue
        sid = _match_sensor(h)
        if sid is not None:
            if sid not in sensor_cols:   # first match wins
                sensor_cols[sid] = i
        else:
            unmapped.append(h)

    return ColumnMap(
        time_col    = time_col,
        sensor_cols = sensor_cols,
        all_headers = headers,
        unmapped    = unmapped,
    )


# ── CSV loader ────────────────────────────────────────────────────────────────

def load_csv(path: Path) -> PlaybackInfo:
    """
    Parse the CSV file and return a PlaybackInfo.
    Raises ValueError with a user-readable message on any error.
    Does NOT store all rows in memory during load — just reads headers + row count.
    """
    if not path.exists():
        raise ValueError(f"File not found: {path}")

    if path.stat().st_size == 0:
        raise ValueError("File is empty")

    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:   # utf-8-sig strips BOM
            reader = csv.reader(fh)

            # Header row
            try:
                raw_headers = next(reader)
            except StopIteration:
                raise ValueError("File has no header row")

            if not raw_headers:
                raise ValueError("Header row is empty")

            headers = [h.strip() for h in raw_headers]
            col_map = _build_column_map(headers)

            if not col_map.sensor_cols:
                raise ValueError(
                    "No recognised sensor columns found.\n"
                    f"Headers: {headers}\n"
                    "Expected columns like: inclino_lat, inclino_long, pressure_400, joystick_pos"
                )

            # Count rows and read last timestamp for duration
            first_ts: Optional[float] = None
            last_ts:  Optional[float] = None
            row_count = 0

            for row in reader:
                row_count += 1
                if col_map.time_col is not None and len(row) > col_map.time_col:
                    try:
                        ts = float(row[col_map.time_col])
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts
                    except (ValueError, TypeError) as ex:
                        logger.debug(
                            f"[PLAYBACK] Scan: row {row_count} "
                            f"timestamp column is not a valid float: {ex}"
                        )

    except (OSError, UnicodeDecodeError) as ex:
        raise ValueError(f"Cannot read file: {ex}") from ex

    if row_count == 0:
        raise ValueError("File has a header but no data rows")

    if row_count > MAX_CSV_ROWS:
        raise ValueError(
            f"File has {row_count:,} rows which exceeds the {MAX_CSV_ROWS:,}-row safety limit.\n"
            "Split the file into smaller segments before loading."
        )

    has_time = col_map.time_col is not None and first_ts is not None
    if has_time:
        duration = (last_ts - first_ts) if last_ts != first_ts else 0.0  # type: ignore[operator]
    else:
        duration = 0.0

    logger.info(
        f"[CSV] Loaded {path.name}: {row_count} rows, "
        f"{len(col_map.sensor_cols)} sensors, "
        f"duration={duration:.1f}s, time_col={'yes' if has_time else 'no'}"
    )

    return PlaybackInfo(
        path         = path,
        total_rows   = row_count,
        duration_s   = duration,
        column_map   = col_map,
        has_time_col = has_time,
        sensor_ids   = sorted(col_map.sensor_cols.keys()),
    )


# ── Playback worker ───────────────────────────────────────────────────────────

class CsvPlayer(QThread):
    """
    Background thread that drives CSV playback.

    Usage:
        player = CsvPlayer()
        info = player.load(path)          # validate + parse headers
        player.sensor_values.connect(bridge.set_sensor_target)
        player.play()                     # starts QThread.start() internally
        player.pause()
        player.seek(row_index)
        player.stop()
    """

    row_changed       = Signal(int, int)    # (current_row, total_rows)
    sensor_values     = Signal(object)      # dict[int, float]
    playback_finished = Signal()
    error_occurred    = Signal(str)

    # ── Init ─────────────────────────────────────────────────────

    def __init__(self, parent: "QThread | None" = None) -> None:
        super().__init__(parent)
        self._info:     Optional[PlaybackInfo] = None
        self._speed:    float         = 1.0
        self._running:  bool          = False
        self._paused:   bool          = False
        self._finished: bool          = False   # True once EOF is reached naturally
        self._seek_row: Optional[int] = None

        self._pause_event = threading.Event()
        self._pause_event.set()    # not paused initially

        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────

    def load(self, path: Path) -> PlaybackInfo:
        """
        Validate and parse the CSV header.  Must be called before play().
        Raises ValueError on any problem.  Safe to call from the GUI thread.
        """
        info = load_csv(path)
        self._info     = info
        self._finished = False   # reset so playback_state() reports correctly
        return info

    def play(self) -> None:
        """Start (or resume) playback."""
        if self.isRunning():
            # Already running — just resume if paused
            self._paused   = False
            self._finished = False
            self._pause_event.set()
            logger.info("[CSV] Resumed")
        else:
            if self._info is None:
                logger.warning("[CSV] play() called with no file loaded")
                return
            self._running  = True
            self._paused   = False
            self._finished = False
            self._pause_event.set()
            self.start()
            logger.info(f"[CSV] Playing {self._info.path.name} at {self._speed}×")

    def pause(self) -> None:
        """Pause playback (thread stays alive, wakes on resume)."""
        self._paused = True
        self._pause_event.clear()
        logger.info("[CSV] Paused")

    def stop(self) -> None:
        """Stop playback and terminate the thread."""
        self._running  = False
        self._finished = False
        self._pause_event.set()   # unblock if paused
        logger.info("[CSV] Stop requested")

    def set_speed(self, speed: float) -> None:
        """Set playback speed. Thread-safe, takes effect immediately."""
        speed = max(0.1, min(100.0, speed))
        with self._lock:
            self._speed = speed
        logger.info(f"[CSV] Speed → {speed}×")

    def get_speed(self) -> float:
        """Return current playback speed multiplier. Thread-safe."""
        with self._lock:
            return self._speed

    def get_playback_info(self) -> "PlaybackInfo | None":
        """Return the loaded PlaybackInfo, or None if no file is loaded."""
        return self._info

    def playback_state(self) -> str:
        """
        Return a string describing the current playback state.
        One of: "unloaded", "stopped", "playing", "paused", "finished".
        Thread-safe.
        """
        if self._info is None:
            return "unloaded"
        if not self.isRunning():
            return "finished" if self._finished else "stopped"
        if self._paused:
            return "paused"
        return "playing"

    def seek(self, row_index: int) -> None:
        """
        Seek to a specific row.  Thread-safe.
        If paused, update the scrubber position immediately.
        Takes effect on next tick if running.
        """
        if self._info is None:
            return
        row_index = max(0, min(self._info.total_rows - 1, row_index))
        with self._lock:
            self._seek_row = row_index
        logger.debug(f"[CSV] Seek → row {row_index}")

    # ── QThread.run ───────────────────────────────────────────────

    def run(self) -> None:
        if self._info is None:
            self.error_occurred.emit("No file loaded")
            return

        info  = self._info
        path  = info.path
        col   = info.column_map
        total = info.total_rows

        logger.info(f"[CSV] Playback thread started: {path.name}")

        try:
            with path.open(newline="", encoding="utf-8-sig") as fh:
                reader      = csv.reader(fh)
                next(reader)           # skip header

                rows: list[list[str]] = list(reader)    # load into RAM once
                                                         # typical file < 100 k rows ≈ a few MB

        except (OSError, UnicodeDecodeError) as ex:
            self.error_occurred.emit(f"Cannot read file: {ex}")
            return

        if not rows:
            self.error_occurred.emit("File has no data rows")
            return

        current_row = 0
        prev_ts: Optional[float] = None
        t_real_prev = time.monotonic()

        while self._running and current_row < len(rows):

            # ── Seek ──────────────────────────────────────────────
            with self._lock:
                if self._seek_row is not None:
                    current_row = self._seek_row
                    self._seek_row = None
                    prev_ts = None          # reset timing after seek
                    t_real_prev = time.monotonic()

            # ── Pause ─────────────────────────────────────────────
            self._pause_event.wait()        # blocks until not paused
            if not self._running:
                break

            row = rows[current_row]

            # ── Parse timestamp ───────────────────────────────────
            ts: Optional[float] = None
            if col.time_col is not None and len(row) > col.time_col:
                try:
                    ts = float(row[col.time_col])
                except (ValueError, TypeError) as ex:
                    logger.debug(
                        f"[PLAYBACK] Row {current_row}: "
                        f"timestamp column is not a valid float: {ex}"
                    )

            # ── Sleep to maintain timing ───────────────────────────
            if ts is not None and prev_ts is not None:
                dt_data = ts - prev_ts            # seconds in recording
                with self._lock:
                    speed = self._speed
                dt_wall = dt_data / speed         # seconds to sleep
                if dt_wall > 0:
                    elapsed = time.monotonic() - t_real_prev
                    sleep_s = max(0.0, dt_wall - elapsed)
                    if sleep_s > 0:
                        # Sleep in small chunks so pause/stop are responsive
                        deadline = time.monotonic() + sleep_s
                        while time.monotonic() < deadline:
                            if not self._running:
                                break
                            self._pause_event.wait(timeout=0.02)
                            if not self._pause_event.is_set():
                                self._pause_event.wait()   # fully paused

            # ── Extract sensor values ──────────────────────────────
            values: dict[int, float] = {}
            for sid, ci in col.sensor_cols.items():
                if ci < len(row):
                    try:
                        values[sid] = float(row[ci])
                    except (ValueError, TypeError):
                        pass    # hold previous value

            # ── Emit ──────────────────────────────────────────────
            if values:
                self.sensor_values.emit(values)

            self.row_changed.emit(current_row, total)

            prev_ts     = ts
            t_real_prev = time.monotonic()
            current_row += 1

            # Fallback timing when there is no time column (20 ms/row = 50 Hz)
            if ts is None:
                with self._lock:
                    speed = self._speed
                time.sleep(max(0.0, 0.02 / speed))

        # ── End of file ───────────────────────────────────────────
        if self._running:
            logger.info(f"[CSV] Playback complete: {path.name}")
            self._finished = True
            self.row_changed.emit(total, total)
            self.playback_finished.emit()

        self._running = False
        logger.info("[CSV] Thread exiting")
