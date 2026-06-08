from __future__ import annotations

"""
monitor_worker.py

Background QThread that opens a CAN bus, receives frames, and emits
them to the GUI via Qt signals (safe cross-thread delivery).

Supports:
  - Standard CAN  (11-bit and 29-bit IDs)
  - CAN-FD        (up to 64 byte payload, optional BRS)
  - J1939         (29-bit ID decoded into PGN / SA / DA / Priority)

Frame type detection:
  - is_fd=True                   → CAN-FD
  - is_extended_id=True and
    (id >> 16) & 0xFF in 0..255  → heuristic J1939 (PGN in upper bytes)
  - else                         → Standard CAN

Sending:
  build_standard() / build_fd() / build_j1939() produce can.Message
  objects that the caller sends via an already-open bus.
"""

import time
from dataclasses import dataclass
from PySide6.QtCore import QThread, Signal
from loguru import logger


# ── Frame dataclass passed via signal ─────────────────────────────

@dataclass
class CanFrame:
    timestamp:   float   # seconds since monitor started
    arb_id:      int     # arbitration ID (raw)
    is_extended: bool    # 29-bit extended ID
    is_fd:       bool    # CAN-FD frame
    is_j1939:    bool    # J1939 heuristic match
    dlc:         int     # data length code
    data:        bytes   # payload

    # J1939 decoded fields (only meaningful when is_j1939=True)
    pgn:      int = 0
    sa:       int = 0    # source address
    da:       int = 0    # destination address
    priority: int = 0

    @property
    def frame_type(self) -> str:
        if self.is_fd:
            return "CAN-FD"
        if self.is_j1939:
            return "J1939"
        return "STD" if not self.is_extended else "EXT"

    @property
    def id_str(self) -> str:
        if self.is_j1939:
            return f"PGN {self.pgn:05X}h"
        width = 8 if self.is_extended else 3
        return f"{self.arb_id:0{width}X}h"

    @property
    def data_str(self) -> str:
        return " ".join(f"{b:02X}" for b in self.data)


def _decode_j1939(arb_id: int) -> tuple[int, int, int, int]:
    """Decode a 29-bit J1939 arbitration ID into (priority, pgn, da, sa)."""
    priority = (arb_id >> 26) & 0x07
    pf       = (arb_id >> 16) & 0xFF   # PDU format
    ps       = (arb_id >>  8) & 0xFF   # PDU specific
    sa       =  arb_id        & 0xFF   # source address

    if pf < 0xF0:
        # PDU1: peer-to-peer, PS = destination address
        pgn = (arb_id >> 8) & 0x03FF00
        da  = ps
    else:
        # PDU2: broadcast, PS part of PGN
        pgn = (arb_id >> 8) & 0x03FFFF
        da  = 0xFF  # global

    return priority, pgn, da, sa


def _is_j1939(frame: "can.Message") -> bool:
    """Heuristic: treat all 29-bit non-FD frames as J1939."""
    return frame.is_extended_id and not frame.is_fd

def _to_frame(msg: "can.Message", t0: float) -> CanFrame:
    """
    Convert a python-can Message to a CanFrame.

    t0 is a time.monotonic() reference captured when the bus opened.
    We use time.monotonic() to compute elapsed seconds so the timestamp
    column in the GUI is always a non-negative relative offset, immune to
    NTP wall-clock jumps that would make msg.timestamp unreliable.
    """
    j1939 = _is_j1939(msg)
    pgn = sa = da = priority = 0

    if j1939:
        priority, pgn, da, sa = _decode_j1939(msg.arbitration_id)

    return CanFrame(
        timestamp   = time.monotonic() - t0,
        arb_id      = msg.arbitration_id,
        is_extended = msg.is_extended_id,
        is_fd       = getattr(msg, "is_fd", False),
        is_j1939    = j1939,
        dlc         = msg.dlc,
        data        = bytes(msg.data),
        pgn         = pgn,
        sa          = sa,
        da          = da,
        priority    = priority,
    )


# ── Monitor worker ────────────────────────────────────────────────

class CanMonitorWorker(QThread):
    """
    Opens a CAN bus on the given channel, polls for frames,
    emits frame_received(CanFrame) for each one.

    Usage:
      worker = CanMonitorWorker(channel="PCAN_USBBUS1", interface="pcan", bitrate=250000)
      worker.frame_received.connect(my_slot)
      worker.error_occurred.connect(my_error_slot)
      worker.start()
      ...
      worker.stop()
    """

    frame_received = Signal(object)   # CanFrame
    error_occurred = Signal(str)      # error message

    def __init__(self, channel: str, interface: str, bitrate: int, parent: "QThread | None" = None) -> None:
        super().__init__(parent)
        self._channel   = channel
        self._interface = interface
        self._bitrate   = bitrate
        self._running   = False

    def run(self) -> None:
        bus = None
        try:
            import can
        except ImportError:
            self.error_occurred.emit("python-can not installed")
            return

        # Try FD-capable first (works on FD hardware and socketcan).
        # Fall back to non-FD for standard PCAN adapters on Windows.
        for fd_mode in (True, False):
            try:
                kwargs = dict(
                    interface = self._interface,
                    channel   = self._channel,
                    bitrate   = self._bitrate,
                )
                if fd_mode:
                    kwargs["fd"] = True
                bus = can.Bus(**kwargs)
                logger.info(
                    f"CAN monitor: opened {self._channel} @ {self._bitrate} bps "
                    f"({'FD' if fd_mode else 'classic'})"
                )
                break
            except Exception as ex:
                if fd_mode:
                    logger.debug(f"CAN monitor: FD mode rejected ({ex}), retrying classic")
                else:
                    logger.error(f"CAN monitor: failed to open bus: {ex}")
                    self.error_occurred.emit(str(ex))
                    return

        if bus is None:
            self.error_occurred.emit("Could not open CAN bus")
            return

        self._running = True
        # Use monotonic clock — immune to NTP jumps that would produce
        # negative or wildly incorrect relative timestamps in the frame table.
        t0 = time.monotonic()

        try:
            while self._running:
                msg = bus.recv(timeout=0.1)
                if msg is not None:
                    self.frame_received.emit(_to_frame(msg, t0))
        except Exception as ex:
            if self._running:
                logger.warning(f"CAN monitor: recv error: {ex}")
                self.error_occurred.emit(str(ex))
        finally:
            try:
                bus.shutdown()
            except Exception as ex:
                logger.warning(f"CAN monitor: bus shutdown error: {ex}")
            logger.info("CAN monitor: stopped")

    def stop(self) -> None:
        logger.info(f"CAN monitor: stop requested for {self._channel}")
        self._running = False


# ── Frame builders (for Send panel) ──────────────────────────────

def build_standard(arb_id: int, data: bytes, is_extended: bool = False) -> "can.Message":
    """Build a standard CAN message."""
    import can
    return can.Message(
        arbitration_id = arb_id,
        is_extended_id = is_extended,
        data           = data,
        is_fd          = False,
    )


def build_fd(arb_id: int, data: bytes, brs: bool = True, is_extended: bool = True) -> "can.Message":
    """Build a CAN-FD message."""
    import can
    return can.Message(
        arbitration_id  = arb_id,
        is_extended_id  = is_extended,
        data            = data,
        is_fd           = True,
        bitrate_switch  = brs,
    )


def build_j1939(pgn: int, sa: int, da: int, priority: int, data: bytes) -> "can.Message":
    """
    Build a J1939 message.
    Encodes priority/PGN/DA/SA into a 29-bit arbitration ID.

    Encoding mirrors _decode_j1939() exactly:
      bits 28-26 : priority  (3 bits)
      bits 25-16 : PF byte   (8 bits, upper 8 of PGN)
      bits 15-8  : PS byte   (DA for PDU1, or lower PGN byte for PDU2)
      bits  7-0  : SA        (8 bits)
    """
    import can
    pf = (pgn >> 8) & 0xFF
    if pf < 0xF0:
        # PDU1: peer-to-peer — PS encodes destination address (DA)
        arb_id = ((priority & 0x07) << 26) | (pf << 16) | (da << 8) | (sa & 0xFF)
    else:
        # PDU2: broadcast — PS is part of PGN (no separate DA)
        ps = pgn & 0xFF
        arb_id = ((priority & 0x07) << 26) | (pf << 16) | (ps << 8) | (sa & 0xFF)

    return can.Message(
        arbitration_id=arb_id,
        is_extended_id=True,
        data=data,
        is_fd=False,
    )
