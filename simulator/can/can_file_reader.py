"""
simulator/can/can_file_reader.py
=================================
Reads CAN database files and CAN log files for the CAN Tools page.

Supported formats
-----------------
Database files (message definitions):
  .dbc   — Vector DBC format          (via cantools)
  .kcd   — Kvaser XML format          (via cantools)
  .arxml — AUTOSAR XML format         (via cantools)

Log files (recorded traffic):
  .asc   — Vector/Peak ASCII log      (via python-can LogReader)
  .blf   — Vector Binary Logging File (via python-can LogReader)
  .trc   — PEAK trace file            (via python-can LogReader)
  .log   — Generic text log           (via python-can; fallback: raw hex parser)
  .csv   — Comma-separated CAN log    (via python-can; fallback: custom CSV parser)
  .txt   — Generic hex lines          (raw hex parser)
  .json  — JSON array of CAN frames   (built-in JSON parser)

All external libraries (cantools, python-can) are imported lazily so a missing
library raises CanFileReadError with an actionable install hint instead of
crashing the application.

Public API
----------
  auto_read_can_file(path)              → (list[CanMessageDef], list[CanLogFrame])
  read_can_db_file(path)               → list[CanMessageDef]
  read_can_log_file(path, max_frames)  → list[CanLogFrame]
  supported_file_filter()              → str  (Qt file dialog filter)
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger


# ── Constants ─────────────────────────────────────────────────────────────────

# Safety cap: stop after this many frames to prevent OOM on large log files.
MAX_LOG_FRAMES = 10_000

# Supported file extension sets
_DB_EXTENSIONS  = {".dbc", ".kcd", ".arxml"}
_LOG_EXTENSIONS = {".asc", ".blf", ".trc", ".log", ".csv", ".txt", ".json"}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class CanSignalDef:
    """One signal inside a CAN message, from a database file."""
    name:       str
    start_bit:  int
    length:     int
    byte_order: str           # 'little_endian' or 'big_endian'
    is_signed:  bool
    factor:     float
    offset:     float
    unit:       str
    min_value:  Optional[float] = None
    max_value:  Optional[float] = None
    comment:    str = ""


@dataclass
class CanMessageDef:
    """A message definition loaded from a CAN database file (.dbc / .kcd)."""
    arb_id:      int
    name:        str
    dlc:         int
    is_extended: bool
    comment:     str = ""
    signals:     list[CanSignalDef] = field(default_factory=list)

    @property
    def arb_id_str(self) -> str:
        """Hex string: 8 digits for extended IDs, 3 for standard."""
        width = 8 if self.is_extended else 3
        return f"0x{self.arb_id:0{width}X}"

    @property
    def frame_type(self) -> str:
        return "EXT" if self.is_extended else "STD"

    @property
    def data_placeholder(self) -> str:
        """DLC-sized zero bytes as a space-separated hex string."""
        return " ".join("00" for _ in range(self.dlc))


@dataclass
class CanLogFrame:
    """A single recorded CAN frame from a log file."""
    timestamp:   float    # seconds since recording start
    arb_id:      int
    is_extended: bool
    dlc:         int
    data:        bytes
    channel:     str = ""

    @property
    def arb_id_str(self) -> str:
        width = 8 if self.is_extended else 3
        return f"0x{self.arb_id:0{width}X}"

    @property
    def data_str(self) -> str:
        return " ".join(f"{b:02X}" for b in self.data)

    @property
    def frame_type(self) -> str:
        return "EXT" if self.is_extended else "STD"


class CanFileReadError(Exception):
    """Raised when a CAN file cannot be read or parsed."""


# ── Database file reader (.dbc / .kcd / .arxml) ───────────────────────────────

def read_can_db_file(path: Path) -> list[CanMessageDef]:
    """
    Parse a CAN database file and return all message definitions.

    Returns a list sorted by arbitration ID.
    Raises CanFileReadError on file-not-found, bad extension, missing library,
    or parse failure.
    """
    if not path.exists():
        raise CanFileReadError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in _DB_EXTENSIONS:
        raise CanFileReadError(
            f"Unsupported database format: '{suffix}'. "
            f"Expected one of: {', '.join(sorted(_DB_EXTENSIONS))}"
        )

    try:
        import cantools  # noqa: PLC0415
    except ImportError:
        raise CanFileReadError(
            "cantools is not installed — required for .dbc / .kcd / .arxml files.\n"
            "Install with:  pip install cantools"
        )

    logger.info(f"[CAN FILE] Loading DB file: {path.name}")

    try:
        db = cantools.database.load_file(str(path))
    except Exception as ex:
        raise CanFileReadError(f"Cannot parse {path.name}: {ex}") from ex

    messages: list[CanMessageDef] = []

    for msg in db.messages:
        signals: list[CanSignalDef] = []
        for sig in msg.signals:
            signals.append(CanSignalDef(
                name       = sig.name or "",
                start_bit  = int(sig.start)   if sig.start   is not None else 0,
                length     = int(sig.length)  if sig.length  is not None else 1,
                byte_order = sig.byte_order   or "little_endian",
                is_signed  = bool(sig.is_signed),
                factor     = float(sig.scale)  if sig.scale  is not None else 1.0,
                offset     = float(sig.offset) if sig.offset is not None else 0.0,
                unit       = sig.unit or "",
                min_value  = float(sig.minimum) if sig.minimum is not None else None,
                max_value  = float(sig.maximum) if sig.maximum is not None else None,
                comment    = sig.comment or "",
            ))

        messages.append(CanMessageDef(
            arb_id      = int(msg.frame_id),
            name        = msg.name or f"MSG_{msg.frame_id:X}",
            dlc         = int(msg.length),
            is_extended = bool(
                getattr(msg, "is_extended_id", None)
                or (int(msg.frame_id) > 0x7FF)
            ),
            comment     = msg.comment or "",
            signals     = signals,
        ))

    messages.sort(key=lambda m: m.arb_id)

    logger.info(
        f"[CAN FILE] DB loaded: {path.name} — "
        f"{len(messages)} messages, "
        f"{sum(len(m.signals) for m in messages)} signals total"
    )
    return messages


# ── Log file reader (dispatcher) ──────────────────────────────────────────────

def read_can_log_file(
    path: Path,
    max_frames: int = MAX_LOG_FRAMES,
) -> list[CanLogFrame]:
    """
    Parse a CAN log file and return recorded frames.

    Parsing strategy per extension:
      .asc / .blf / .trc / .log — python-can LogReader (with raw-hex fallback for .log)
      .csv  — python-can LogReader first; custom CSV parser as fallback
      .txt  — raw hex-line parser
      .json — JSON array parser

    Returns frames oldest-first, capped at max_frames.
    Raises CanFileReadError on file-not-found, bad extension, missing library,
    or complete parse failure.
    """
    if not path.exists():
        raise CanFileReadError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in _LOG_EXTENSIONS:
        raise CanFileReadError(
            f"Unsupported log format: '{suffix}'.\n"
            f"Supported: {', '.join(sorted(_LOG_EXTENSIONS))}"
        )

    logger.info(f"[CAN FILE] Loading log file: {path.name} (cap={max_frames:,})")

    # JSON is handled entirely without python-can
    if suffix == ".json":
        return _parse_json_log(path, max_frames)

    # Plain text files — skip python-can entirely
    if suffix == ".txt":
        frames = _read_raw_hex_lines(path, max_frames)
        return _require_frames(frames, path, max_frames)

    # All others: try python-can's LogReader first
    try:
        import can  # noqa: PLC0415
    except ImportError:
        raise CanFileReadError(
            "python-can is not installed — required for CAN log files.\n"
            "Install with:  pip install python-can"
        )

    frames = _try_python_can_reader(can, path, max_frames)

    if frames is None:
        # LogReader failed — try format-specific fallback
        if suffix == ".csv":
            logger.debug(f"[CAN FILE] python-can LogReader failed for {path.name} — trying custom CSV parser")
            frames = _parse_custom_csv(path, max_frames)
        elif suffix == ".log":
            logger.debug(f"[CAN FILE] python-can LogReader failed for {path.name} — trying raw hex parser")
            frames = _read_raw_hex_lines(path, max_frames)
        else:
            raise CanFileReadError(
                f"Cannot read {path.name}.\n"
                "The file may be corrupt or use an unsupported variant of this format."
            )

    return _require_frames(frames, path, max_frames)


def _require_frames(frames: list[CanLogFrame], path: Path, max_frames: int = MAX_LOG_FRAMES) -> list[CanLogFrame]:
    """Raise CanFileReadError if the frame list is empty; warn if truncated."""
    if not frames:
        raise CanFileReadError(
            f"{path.name} was parsed but contains no CAN frames.\n"
            "Check that the file is not empty and uses a supported format."
        )
    if len(frames) >= max_frames:
        logger.warning(
            f"[CAN FILE] Log truncated at {max_frames:,} frames — "
            f"file '{path.name}' may contain more frames. "
            f"Increase MAX_LOG_FRAMES to see the full file."
        )
    logger.info(f"[CAN FILE] Log loaded: {path.name} — {len(frames):,} frames")
    return frames


# ── python-can LogReader ───────────────────────────────────────────────────────

def _try_python_can_reader(
    can_mod: object,
    path: Path,
    max_frames: int,
) -> Optional[list[CanLogFrame]]:
    """
    Try python-can's LogReader.  Returns a list on success, None on any exception.
    The caller decides which fallback parser to use on failure.
    """
    try:
        frames: list[CanLogFrame] = []
        with can_mod.LogReader(str(path)) as reader:
            t_start: Optional[float] = None
            for msg in reader:
                if msg is None:
                    continue
                if t_start is None:
                    t_start = float(msg.timestamp)
                frames.append(CanLogFrame(
                    timestamp   = float(msg.timestamp) - t_start,
                    arb_id      = int(msg.arbitration_id),
                    is_extended = bool(msg.is_extended_id),
                    dlc         = int(msg.dlc),
                    data        = bytes(msg.data),
                    channel     = str(getattr(msg, "channel", "") or ""),
                ))
                if len(frames) >= max_frames:
                    logger.warning(
                        f"[CAN FILE] Log truncated at {max_frames:,} frames — "
                        f"'{path.name}' may contain more. "
                        f"Increase MAX_LOG_FRAMES to see the full file."
                    )
                    break
        return frames
    except Exception as ex:
        logger.debug(f"[CAN FILE] python-can LogReader rejected {path.name}: {ex}")
        return None


# ── Custom CSV parser ─────────────────────────────────────────────────────────

def _parse_custom_csv(path: Path, max_frames: int) -> list[CanLogFrame]:
    """
    Parse a simple CAN CSV file with this header format:
        Timestamp,ID,DLC,Data

    Rules:
      - Header row is required; columns matched case-insensitively.
      - Timestamp: float seconds.
      - ID: hex string, with or without '0x' prefix.
      - DLC: integer (used only for validation; actual DLC taken from data bytes).
      - Data: space-separated hex bytes (e.g. "00 64 32 00").

    Rows that cannot be parsed are skipped with a DEBUG log.
    """
    frames: list[CanLogFrame] = []
    t_start: Optional[float] = None

    try:
        with path.open(newline="", encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)

            if reader.fieldnames is None:
                logger.debug(f"[CAN FILE] CSV {path.name}: no header row found")
                return frames

            # Normalise field names for case-insensitive matching
            norm = {k.strip().lower(): k for k in reader.fieldnames if k}

            # Locate required columns by common name variants
            col_ts   = _find_csv_col(norm, ("timestamp", "time", "t", "elapsed", "elapsed_s"))
            col_id   = _find_csv_col(norm, ("id", "canid", "arbitration_id", "arb_id"))
            col_data = _find_csv_col(norm, ("data", "payload", "bytes", "raw"))

            if col_id is None or col_data is None:
                logger.debug(
                    f"[CAN FILE] CSV {path.name}: missing required columns "
                    f"(need ID + Data). Headers: {list(reader.fieldnames)}"
                )
                return frames

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Timestamp (optional — use row index if absent)
                    if col_ts and col_ts in row and row[col_ts].strip():
                        ts_raw = float(row[col_ts].strip())
                    else:
                        ts_raw = float(row_num - 2) * 0.01

                    if t_start is None:
                        t_start = ts_raw
                    ts = ts_raw - t_start

                    # Arbitration ID
                    id_text = row[col_id].strip()
                    arb_id = int(id_text, 16) if id_text.startswith(("0x", "0X")) \
                             else int(id_text, 16)

                    # Data bytes
                    data_text = row[col_data].strip()
                    data_bytes = bytes(int(b, 16) for b in data_text.split() if b)

                    is_extended = arb_id > 0x7FF

                    frames.append(CanLogFrame(
                        timestamp   = ts,
                        arb_id      = arb_id,
                        is_extended = is_extended,
                        dlc         = len(data_bytes),
                        data        = data_bytes,
                    ))

                    if len(frames) >= max_frames:
                        logger.info(f"[CAN FILE] CSV cap reached at {max_frames:,} frames")
                        break

                except (ValueError, KeyError) as ex:
                    logger.debug(f"[CAN FILE] CSV {path.name} row {row_num}: skipped ({ex})")

    except OSError as ex:
        raise CanFileReadError(f"Cannot open {path.name}: {ex}") from ex

    return frames


def _find_csv_col(
    norm_map: dict[str, str],
    candidates: tuple[str, ...],
) -> Optional[str]:
    """Return the original column name that matches any of the candidate strings."""
    for candidate in candidates:
        if candidate in norm_map:
            return norm_map[candidate]
    return None


# ── JSON log parser ───────────────────────────────────────────────────────────

def _parse_json_log(path: Path, max_frames: int) -> list[CanLogFrame]:
    """
    Parse a JSON CAN log file.

    Expected format — array of objects:
    [
      { "timestamp": 0.0, "id": "0x100", "dlc": 8, "data": [0, 100, 50, 0, 0, 0, 0, 0] },
      { "timestamp": 0.1, "id": "0x200", "dlc": 2, "data": [1, 0] }
    ]

    Field name variants accepted (all case-insensitive):
      timestamp : "timestamp", "time", "t", "ts"
      id        : "id", "canid", "arbitration_id", "arb_id", "frame_id"
      data      : "data", "payload", "bytes"

    Data may be:
      - A list of integers: [0, 100, 50]
      - A hex string: "00 64 32" or "006432"
    """
    logger.info(f"[CAN FILE] Loading JSON log: {path.name}")

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        obj = json.loads(raw)
    except OSError as ex:
        raise CanFileReadError(f"Cannot open {path.name}: {ex}") from ex
    except json.JSONDecodeError as ex:
        raise CanFileReadError(f"Invalid JSON in {path.name}: {ex}") from ex

    if not isinstance(obj, list):
        raise CanFileReadError(
            f"{path.name} must contain a JSON array of frame objects.\n"
            'Example: [{"timestamp": 0.0, "id": "0x100", "dlc": 8, "data": [0,1,2]}]'
        )

    frames: list[CanLogFrame] = []
    t_start: Optional[float] = None

    for entry_num, entry in enumerate(obj):
        if not isinstance(entry, dict):
            logger.debug(f"[CAN FILE] JSON {path.name} entry {entry_num}: not a dict, skipped")
            continue

        # Normalise keys
        norm = {k.strip().lower(): v for k, v in entry.items()}

        try:
            # Timestamp
            ts_raw = _json_get_float(norm, ("timestamp", "time", "t", "ts"))
            if ts_raw is None:
                ts_raw = float(entry_num) * 0.01
            if t_start is None:
                t_start = ts_raw
            ts = ts_raw - t_start

            # Arbitration ID
            id_raw = _json_get_any(norm, ("id", "canid", "arbitration_id", "arb_id", "frame_id"))
            if id_raw is None:
                logger.debug(f"[CAN FILE] JSON entry {entry_num}: no ID field, skipped")
                continue
            if isinstance(id_raw, str):
                arb_id = int(id_raw, 16) if id_raw.startswith(("0x", "0X")) \
                         else int(id_raw, 16)
            else:
                arb_id = int(id_raw)

            # Data bytes
            data_raw = _json_get_any(norm, ("data", "payload", "bytes"))
            if data_raw is None:
                data_bytes = b""
            elif isinstance(data_raw, list):
                data_bytes = bytes(int(b) & 0xFF for b in data_raw)
            elif isinstance(data_raw, str):
                # Accept both "00 64 32" and "006432"
                text = data_raw.strip()
                if " " in text:
                    data_bytes = bytes(int(b, 16) for b in text.split())
                else:
                    data_bytes = bytes.fromhex(text)
            else:
                data_bytes = b""

            is_extended = arb_id > 0x7FF

            frames.append(CanLogFrame(
                timestamp   = ts,
                arb_id      = arb_id,
                is_extended = is_extended,
                dlc         = len(data_bytes),
                data        = data_bytes,
            ))

            if len(frames) >= max_frames:
                logger.info(f"[CAN FILE] JSON cap reached at {max_frames:,} frames")
                break

        except (ValueError, TypeError) as ex:
            logger.debug(f"[CAN FILE] JSON {path.name} entry {entry_num}: skipped ({ex})")

    return _require_frames(frames, path, max_frames)


def _json_get_float(d: dict, keys: tuple[str, ...]) -> Optional[float]:
    """Return the first matching key's value as float, or None."""
    for k in keys:
        if k in d:
            try:
                return float(d[k])
            except (ValueError, TypeError) as ex:
                logger.debug(f"[CAN FILE] JSON field '{k}' is not a valid float: {d[k]!r} ({ex})")
    return None


def _json_get_any(d: dict, keys: tuple[str, ...]) -> object:
    """Return the first matching key's raw value, or None."""
    for k in keys:
        if k in d:
            return d[k]
    return None


# ── Raw hex-line fallback parser ──────────────────────────────────────────────

def _read_raw_hex_lines(path: Path, max_frames: int) -> list[CanLogFrame]:
    """
    Best-effort parser for plain-text CAN logs.

    Each data line looks like:
        [optional_float_timestamp]  <hex_id>  <hex_byte> <hex_byte> ...

    Comment lines (#, //, ;) and blank lines are skipped.
    Lines that do not match are skipped silently.
    """
    frames: list[CanLogFrame] = []
    t_start: Optional[float] = None

    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith(("#", "//", ";")):
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                ts_raw: Optional[float] = None
                id_idx = 0

                # Leading token may be a float timestamp — try, fall back to treating as ID
                try:
                    ts_raw = float(parts[0])
                    id_idx = 1
                except ValueError:
                    logger.debug(
                        f"[CAN FILE] {path.name}: first token '{parts[0]}' "
                        "is not a float timestamp — treating as ID"
                    )

                try:
                    arb_id = int(parts[id_idx], 16)
                except (ValueError, IndexError):
                    continue

                data_bytes: list[int] = []
                for p in parts[id_idx + 1:]:
                    try:
                        data_bytes.append(int(p, 16))
                    except ValueError:
                        break   # stop at first non-hex token

                if t_start is None:
                    t_start = ts_raw or 0.0
                ts = (ts_raw - t_start) if ts_raw is not None else float(len(frames)) * 0.01

                frames.append(CanLogFrame(
                    timestamp   = ts,
                    arb_id      = arb_id,
                    is_extended = arb_id > 0x7FF,
                    dlc         = len(data_bytes),
                    data        = bytes(data_bytes),
                ))

                if len(frames) >= max_frames:
                    logger.warning(
                        f"[CAN FILE] Log truncated at {max_frames:,} frames — "
                        f"'{path.name}' may contain more. "
                        f"Increase MAX_LOG_FRAMES to see the full file."
                    )
                    break

    except OSError as ex:
        raise CanFileReadError(f"Cannot open {path.name}: {ex}") from ex

    return frames


# ── Public entry point ────────────────────────────────────────────────────────

def auto_read_can_file(
    path: Path,
    max_log_frames: int = MAX_LOG_FRAMES,
) -> tuple[list[CanMessageDef], list[CanLogFrame]]:
    """
    Auto-detect file type from extension and parse it.

    Returns:
        (message_defs, log_frames) — exactly one list will be non-empty.

    Raises:
        CanFileReadError on any failure.
    """
    suffix = path.suffix.lower()

    if suffix in _DB_EXTENSIONS:
        return read_can_db_file(path), []

    if suffix in _LOG_EXTENSIONS:
        return [], read_can_log_file(path, max_frames=max_log_frames)

    raise CanFileReadError(
        f"Unknown file extension: '{suffix}'.\n"
        f"Database files: {', '.join(sorted(_DB_EXTENSIONS))}\n"
        f"Log files:      {', '.join(sorted(_LOG_EXTENSIONS))}"
    )


def supported_file_filter() -> str:
    """
    Return a Qt file-dialog filter string covering all supported formats.
    """
    all_exts = sorted(_DB_EXTENSIONS | _LOG_EXTENSIONS)
    ext_str  = " ".join(f"*{e}" for e in all_exts)
    db_str   = " ".join(f"*{e}" for e in sorted(_DB_EXTENSIONS))
    log_str  = " ".join(f"*{e}" for e in sorted(_LOG_EXTENSIONS))
    return (
        f"All CAN Files ({ext_str});;"
        f"CAN Database ({db_str});;"
        f"CAN Log ({log_str});;"
        f"All Files (*.*)"
    )
