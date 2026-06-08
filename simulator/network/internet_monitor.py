"""
simulator/network/internet_monitor.py
======================================
Background QThread that continuously monitors internet connectivity.

How it works
------------
A socket connection attempt is made to a set of well-known hosts on port 80.
If ANY host responds within the timeout window, the machine is considered online.
The check is purely a TCP handshake — no HTTP data is sent, so it is:
  - Extremely lightweight  (< 1 ms on a live connection)
  - Cross-platform         (Windows / Linux / Raspberry Pi)
  - No extra dependencies  (stdlib ``socket`` only)

Status transitions
------------------
  CHECKING → ONLINE   : emits status_changed(True)
  CHECKING → OFFLINE  : emits status_changed(False)
  ONLINE   → OFFLINE  : emits status_changed(False)
  OFFLINE  → ONLINE   : emits status_changed(True)

All transitions (including re-confirmation of the same state after N polls)
are logged at DEBUG level. Only genuine flips are logged at INFO level and
cause a signal emission.

Thread safety
-------------
All Qt GUI updates must happen on the main thread.
This class NEVER touches any QWidget directly — it only emits signals.
The TopHeader widget connects those signals via a normal (queued) connection,
so Qt automatically marshals the callback onto the GUI thread.

Usage
-----
    monitor = InternetMonitor(parent=self)
    monitor.status_changed.connect(self._on_net_status)
    monitor.start()
    ...
    monitor.stop()      # request graceful exit
    monitor.wait(3000)  # block up to 3 s for thread to finish
"""

from __future__ import annotations

import socket
import time
from typing import Final

from loguru import logger
from PySide6.QtCore import QThread, Signal


# ── Poll configuration ────────────────────────────────────────────────────────

# How often (seconds) to re-check connectivity while already in a known state.
POLL_INTERVAL_SEC: Final[float] = 10.0

# How quickly to re-check immediately after a state transition (fast recovery).
RECHECK_INTERVAL_SEC: Final[float] = 3.0

# TCP connect timeout per probe host (seconds).
PROBE_TIMEOUT_SEC: Final[float] = 3.0

# Ordered list of (host, port) probes.  The check passes as soon as the first
# TCP handshake succeeds — remaining hosts are skipped.
# Hosts chosen for maximum availability and geographic spread:
#   1.1.1.1  — Cloudflare public DNS   (anycast, extremely reliable)
#   8.8.8.8  — Google public DNS       (globally distributed)
#   9.9.9.9  — Quad9 public DNS        (privacy-focused, global anycast)
PROBE_HOSTS: Final[tuple[tuple[str, int], ...]] = (
    ("1.1.1.1", 80),
    ("8.8.8.8", 80),
    ("9.9.9.9", 80),
)


# ── Internet status sentinel ──────────────────────────────────────────────────

class _Status:
    """Internal enum-like sentinel for the three monitor states."""
    CHECKING: Final[str] = "CHECKING"
    ONLINE:   Final[str] = "ONLINE"
    OFFLINE:  Final[str] = "OFFLINE"


# ── InternetMonitor ───────────────────────────────────────────────────────────

class InternetMonitor(QThread):
    """
    Background thread that probes internet connectivity and emits
    ``status_changed`` whenever the online/offline state flips.

    Signals
    -------
    status_changed(is_online: bool)
        Emitted once when the state first resolves from CHECKING, and
        again every time it flips between ONLINE and OFFLINE.
    """

    # Emitted on every genuine state change (CHECKING→*, ONLINE→OFFLINE, OFFLINE→ONLINE).
    status_changed = Signal(bool)

    def __init__(self, parent: object = None) -> None:
        super().__init__(parent)
        self._stop_requested: bool = False
        self._current_state: str = _Status.CHECKING
        logger.debug("[NET] InternetMonitor created — will start probing on run()")

    # ── Public API ────────────────────────────────────────────────────────────

    def stop(self) -> None:
        """
        Request the poll loop to exit on the next iteration.
        Call ``wait()`` after this to block until the thread finishes.
        """
        logger.debug("[NET] InternetMonitor stop requested")
        self._stop_requested = True

    # ── QThread entry point ───────────────────────────────────────────────────

    def run(self) -> None:
        """Main loop — probes connectivity at regular intervals."""
        logger.info(
            f"[NET] InternetMonitor started "
            f"(poll={POLL_INTERVAL_SEC:.0f}s, timeout={PROBE_TIMEOUT_SEC:.0f}s)"
        )
        self._stop_requested = False

        while not self._stop_requested:
            is_online: bool = self._probe_internet()
            self._handle_result(is_online)

            # Sleep in small increments so stop() takes effect quickly.
            interval = (
                RECHECK_INTERVAL_SEC
                if self._current_state == _Status.CHECKING
                else POLL_INTERVAL_SEC
            )
            self._interruptible_sleep(interval)

        logger.info("[NET] InternetMonitor stopped")

    # ── Connectivity probe ────────────────────────────────────────────────────

    def _probe_internet(self) -> bool:
        """
        Attempt a TCP handshake to each probe host in order.
        Returns True as soon as any host responds; False if all fail.
        """
        for host, port in PROBE_HOSTS:
            if self._tcp_connect(host, port):
                return True
        return False

    @staticmethod
    def _tcp_connect(host: str, port: int) -> bool:
        """
        Return True if a TCP connection to (host, port) succeeds within
        PROBE_TIMEOUT_SEC.  The socket is closed immediately after — no
        data is exchanged.
        """
        try:
            with socket.create_connection((host, port), timeout=PROBE_TIMEOUT_SEC) as _sock:
                pass  # connection established → online
            return True
        except OSError:
            # Covers: ConnectionRefusedError, timeout, network unreachable, etc.
            return False
        except Exception as exc:
            logger.warning(f"[NET] Unexpected error probing {host}:{port} — {exc!r}")
            return False

    # ── State machine ─────────────────────────────────────────────────────────

    def _handle_result(self, is_online: bool) -> None:
        """
        Compare the probe result against the known state.
        Emit status_changed and log only when the state genuinely changes.
        """
        new_state: str = _Status.ONLINE if is_online else _Status.OFFLINE

        if new_state == self._current_state:
            # State unchanged — no log, no signal.
            return

        # Genuine transition
        old_state = self._current_state
        self._current_state = new_state

        if is_online:
            logger.info(f"[NET]  Internet ONLINE  (was {old_state})")
        else:
            logger.warning(f"[NET]  Internet OFFLINE (was {old_state})")

        # Emit on the QThread — Qt will queue-marshal it to the GUI thread
        # because TopHeader connects with the default AutoConnection.
        self.status_changed.emit(is_online)

    # ── Interruptible sleep ───────────────────────────────────────────────────

    def _interruptible_sleep(self, total_seconds: float) -> None:
        """
        Sleep for ``total_seconds`` in 0.25-second slices so that a
        stop() call takes effect within a quarter-second.
        """
        SLICE: Final[float] = 0.25
        elapsed: float = 0.0
        while elapsed < total_seconds and not self._stop_requested:
            time.sleep(SLICE)
            elapsed += SLICE
