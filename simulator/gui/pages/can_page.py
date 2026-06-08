from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.icons import IconWidget
from simulator.gui.components import PageTitleBar, HSep, Card
from simulator.gui.constants import BAUDRATE_OPTIONS
from simulator.platform.platform_detector import PlatformProfile
from simulator.platform.can_detector import CanChannel


class CanChannelCard(QWidget):
    """
    Card for one CAN channel.
    Shows: channel name, connection status, baudrate dropdown, Apply button.
    Emits baudrate_changed(node_id, new_bitrate) on Apply.
    """

    baudrate_changed = Signal(str, int)

    def __init__(self, channel: CanChannel, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._channel = channel
        self.setObjectName("CanCard")
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        # Single horizontal row: ● PCAN_USBBUS1  [250 kbps ▼]
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(8)

        # Connection icon — plug icon, red=disconnected green=connected
        self._dot = IconWidget(fa="fa6s.plug", fallback="●", colour=t.RED, size=11)
        self._dot.setFixedSize(16, 16)
        self._dot.setAlignment(Qt.AlignCenter)
        row.addWidget(self._dot, 0, Qt.AlignVCenter)

        # Channel name
        name_lbl = QLabel(channel.name)
        name_lbl.setObjectName("CanCardTitle")
        name_lbl.setStyleSheet(
            f"color: {t.TEXT_BRIGHT}; font-size: 11px; "
            "letter-spacing: 0.5px; background: transparent;"
        )
        row.addWidget(name_lbl, 0, Qt.AlignVCenter)

        # Baudrate selector — QPushButton + QMenu (reliable on all platforms)
        # QComboBox popup was broken on Windows first-open; QMenu just works.
        self._baud_btn = QPushButton(channel.bitrate_label + "  ▼")
        self._baud_btn.setObjectName("BaudBtn")
        self._baud_btn.setCursor(Qt.PointingHandCursor)
        self._baud_btn.clicked.connect(self._show_baudrate_menu)

        logger.debug(f"[CAN] Card built: {channel.name} @ {channel.bitrate_label}")
        row.addWidget(self._baud_btn, 0, Qt.AlignVCenter)

    def _show_baudrate_menu(self) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #111111;
                border: 1px solid #FFD100;
                border-radius: 10px;
                padding: 6px 6px;
            }
            QMenu::item {
                background-color: transparent;
                color: #F5F5F5;
                padding: 7px 24px 7px 14px;
                margin: 0px;
                font-size: 11px;
            }
            QMenu::item:selected {
                background-color: #1E1600;
                color: #FFD100;
            }
            QMenu::item:checked {
                color: #FFD100;
                font-weight: bold;
            }
        """)
        for lbl, value in BAUDRATE_OPTIONS:
            action = menu.addAction(lbl)
            action.setData(value)
            action.setCheckable(True)
            action.setChecked(value == self._channel.bitrate)

        # Show menu anchored below the button
        pos = self._baud_btn.mapToGlobal(
            self._baud_btn.rect().bottomLeft()
        )
        chosen = menu.exec(pos)
        if chosen is not None:
            self._on_apply(chosen.data(), chosen.text())

    def set_connected(self, connected: bool) -> None:
        color = t.GREEN if connected else t.RED
        self._dot.set_colour(color)

    def _on_apply(self, new_bitrate: int, label: str) -> None:
        old_label = self._channel.bitrate_label
        if new_bitrate == self._channel.bitrate:
            logger.debug(f"[CAN] Baudrate unchanged for {self._channel.name} ({old_label}) — skip")
            return
        self._channel.bitrate = new_bitrate
        self._baud_btn.setText(label + "  ▼")
        logger.info(f"[CAN] Baudrate changed: {self._channel.name}  {old_label} → {label}")
        self.baudrate_changed.emit(self._channel.node_id, self._channel.bitrate)


class CanMonitorWidget(QWidget):
    """
    Full CAN monitor + sender panel embedded in the CAN page.

    Top half  : live message log table (timestamp, ID, type, DLC, data)
    Bottom half: send frame panel with Standard / CAN-FD / J1939 tabs

    profile is passed in from MainWindow — never re-detected at runtime.
    """

    def __init__(self, can_channels: list[CanChannel], profile: PlatformProfile, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._channels  = can_channels
        self._profile   = profile          # ← stored, never re-detected
        self._worker    = None
        self._bus       = None
        self._row_count = 0
        self._selected_channel: CanChannel | None = (
            can_channels[0] if can_channels else None
        )
        # Tracks node_ids that are physically disconnected right now.
        # START is blocked for any channel in this set.
        self._disconnected_channels: set[str] = set()
        # True when the user explicitly pressed STOP.
        # Prevents auto-restart when the channel reconnects after a manual stop.
        self._user_stopped: bool = False
        self._max_rows  = 500

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── Monitor card ──────────────────────────────────────────
        mon_card = QWidget()
        mon_card.setObjectName("MonCard")
        mon_card.setAttribute(Qt.WA_StyledBackground, True)
        mon_card.setStyleSheet(f"""
            QWidget#MonCard {{
                background-color: #161616;
                border: 1px solid #2A2A2A;
                border-top: 2px solid {t.YELLOW};
                border-radius: 8px;
            }}
        """)
        mon_layout = QVBoxLayout(mon_card)
        mon_layout.setContentsMargins(14, 12, 14, 12)
        mon_layout.setSpacing(8)

        # Monitor toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        mon_ic = IconWidget(fa="fa6s.wave-square", fallback="⬡", colour=t.YELLOW, size=13)
        toolbar.addWidget(mon_ic)
        mon_title = QLabel("CAN MONITOR")
        mon_title.setStyleSheet(
            f"color: {t.YELLOW}; font-size: 11px; "
            f"letter-spacing: 2px; font-weight: bold; background: transparent;"
        )
        toolbar.addWidget(mon_title)
        toolbar.addSpacing(12)

        ch_lbl = QLabel("CHANNEL")
        ch_lbl.setStyleSheet("color: #555; font-size: 9px; letter-spacing: 1px; background: transparent;")
        toolbar.addWidget(ch_lbl)

        # Channel selector — QPushButton + QMenu
        first_name = can_channels[0].name if can_channels else "No channels"
        self._ch_btn = QPushButton(first_name + "  ▼")
        self._ch_btn.setObjectName("MonChBtn")
        self._ch_btn.setCursor(Qt.PointingHandCursor)
        self._ch_btn.setEnabled(bool(can_channels))
        self._ch_btn.clicked.connect(self._show_channel_menu)
        toolbar.addWidget(self._ch_btn)

        toolbar.addSpacing(8)

        self._start_btn = QPushButton("▶  START")
        self._start_btn.setObjectName("MonStartBtn")
        self._start_btn.setFixedHeight(28)
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.clicked.connect(self._on_start)
        self._start_btn.setEnabled(bool(can_channels))
        toolbar.addWidget(self._start_btn)

        self._stop_btn = QPushButton("⬛  STOP")
        self._stop_btn.setObjectName("MonStopBtn")
        self._stop_btn.setFixedHeight(28)
        self._stop_btn.setCursor(Qt.PointingHandCursor)
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)
        toolbar.addWidget(self._stop_btn)

        clear_btn = QPushButton("✕  CLEAR")
        clear_btn.setObjectName("MonClearBtn")
        clear_btn.setFixedHeight(28)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        mon_layout.addLayout(toolbar)

        # Message table
        self._table = QTableWidget(0, 5)
        self._table.setObjectName("MonTable")
        self._table.setHorizontalHeaderLabels(["TIME (s)", "ID", "TYPE", "DLC", "DATA"])
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._table.horizontalHeader().setDefaultSectionSize(90)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 80)
        self._table.setColumnWidth(1, 110)
        self._table.setColumnWidth(2, 72)
        self._table.setColumnWidth(3, 44)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mon_layout.addWidget(self._table)

        root.addWidget(mon_card)

    # ── Panel builders ────────────────────────────────────────────

    def _show_channel_menu(self) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #111111;
                border: 1px solid #FFD100;
                border-radius: 10px;
                padding: 6px 6px;
            }
            QMenu::item {
                background-color: transparent;
                color: #F5F5F5;
                padding: 7px 24px 7px 14px;
                margin: 0px;
                font-size: 11px;
            }
            QMenu::item:selected {
                background-color: #1E1600;
                color: #FFD100;
            }
            QMenu::item:checked {
                color: #FFD100;
                font-weight: bold;
            }
        """)
        for ch in self._channels:
            action = menu.addAction(ch.name)
            action.setData(ch)
            action.setCheckable(True)
            action.setChecked(ch is self._selected_channel)

        pos = self._ch_btn.mapToGlobal(self._ch_btn.rect().bottomLeft())
        chosen = menu.exec(pos)
        if chosen is not None:
            self._selected_channel = chosen.data()
            self._ch_btn.setText(self._selected_channel.name + "  ▼")
            logger.debug(f"[CAN] Monitor channel selected: {self._selected_channel.name}")

    def _on_start(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        ch: CanChannel = self._selected_channel
        if not ch:
            return

        # Guard: channel must be physically connected before we open the bus.
        # Catches disconnected PCAN adapters before the driver raises a raw error.
        if ch.node_id in self._disconnected_channels:
            logger.warning(f"[CAN] Start blocked — {ch.name} is not connected")
            return

        from simulator.can.monitor_worker import CanMonitorWorker

        self._worker = CanMonitorWorker(
            channel   = ch.node_id,
            interface = self._profile.can_backend.value,
            bitrate   = ch.bitrate if ch.bitrate > 0 else 250_000,
        )
        self._worker.frame_received.connect(self._on_frame, Qt.QueuedConnection)
        self._worker.error_occurred.connect(self._on_mon_error, Qt.QueuedConnection)
        self._worker.start()

        self._user_stopped = False
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        logger.info(f"[CAN] Monitor started on {ch.name}")

    def _on_stop(self) -> None:
        # Mark as user-intentional stop — prevents auto-restart on next poll
        self._user_stopped = True
        if self._worker:
            self._worker.stop()
            self._worker.wait(2000)
            self._worker = None
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        logger.info("[CAN] Monitor stopped by user")

    def notify_channel_connection(self, node_id: str, connected: bool) -> None:
        """Called by CanPage when a CAN channel is plugged or unplugged.

        - Disconnect: if currently monitoring that channel → stop the worker
          (the hardware is gone; the worker would error immediately anyway).
        - Reconnect:  update internal state only — monitor does NOT auto-start.
          The user must press START explicitly.
        """
        # Keep the disconnected set current so START button guard works correctly
        if connected:
            self._disconnected_channels.discard(node_id)
            logger.debug(f"[CAN] {node_id} connected — ready to monitor (press START)")
        else:
            self._disconnected_channels.add(node_id)

        is_monitoring_this = (
            self._worker is not None
            and self._worker.isRunning()
            and self._selected_channel is not None
            and self._selected_channel.node_id == node_id
        )

        if not connected and is_monitoring_this:
            # Hardware was physically removed while monitoring — stop the worker.
            # This is not a user-intentional stop, so _user_stopped stays False,
            # allowing the user to press START again once the cable is re-plugged.
            self._worker.stop()
            self._worker.wait(2000)
            self._worker = None
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            logger.warning(f"[CAN] {node_id} disconnected — monitor stopped (cable pulled)")

    def _on_mon_error(self, msg: str) -> None:
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        logger.warning(f"[CAN] Monitor error: {msg}")

    def _clear(self) -> None:
        self._table.setRowCount(0)
        self._row_count = 0

    # ── Frame received ────────────────────────────────────────────

    def _on_frame(self, frame: object) -> None:
        if self._row_count >= self._max_rows:
            self._table.removeRow(0)
            self._row_count -= 1

        row = self._table.rowCount()
        self._table.insertRow(row)

        def cell(text: str, color: str | None = None) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            if color:
                item.setForeground(QColor(color))
            return item

        type_color = {
            "CAN-FD": "#38BDF8",
            "J1939":  "#A78BFA",
            "STD":    "#F2F2F2",
            "EXT":    "#FCD34D",
        }.get(frame.frame_type, "#F2F2F2")

        self._table.setItem(row, 0, cell(f"{frame.timestamp:9.3f}"))
        self._table.setItem(row, 1, cell(frame.id_str))
        self._table.setItem(row, 2, cell(frame.frame_type, type_color))
        self._table.setItem(row, 3, cell(str(frame.dlc)))
        self._table.setItem(row, 4, cell(frame.data_str))
        self._table.setRowHeight(row, 22)

        self._table.scrollToBottom()
        self._row_count += 1


class CanPage(QWidget):
    """Page 1 — CAN settings + monitor."""

    baudrate_changed = Signal(str, int)   # (node_id, bitrate)
    tools_requested  = Signal()           # navigate to CAN Tools page

    def __init__(self, can_channels: list[CanChannel], profile: PlatformProfile, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._cards: dict[str, CanChannelCard] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(0)

        # ── Title bar row ─────────────────────────────────────────
        # PageTitleBar has show_separator=False so its internal HSep is
        # suppressed.  A standalone HSep is added BELOW this entire row
        # (root.addWidget(HSep())) so the separator line runs full-width —
        # spanning both the title pill column AND the CAN TOOLS button.
        # Without this, the separator would stop at the pill's right edge
        # and leave the button floating on an empty background.
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)
        header_row.addWidget(
            PageTitleBar("CAN", show_separator=False),
            stretch=1,
        )

        tools_btn = QPushButton("  CAN TOOLS  ⟶")
        tools_btn.setCursor(Qt.PointingHandCursor)
        tools_btn.setFixedHeight(28)
        tools_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1C1C1C;
                color: {t.YELLOW};
                border: 1px solid {t.YELLOW};
                border-radius: 14px;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background-color: #1A1200;
                color: #E8BA00;
                border-color: #E8BA00;
            }}
            QPushButton:pressed {{
                background-color: #141000;
            }}
        """)
        tools_btn.clicked.connect(self.tools_requested.emit)
        header_row.addWidget(tools_btn, stretch=0, alignment=Qt.AlignVCenter)

        root.addLayout(header_row)
        root.addSpacing(t.SPACE_XS)  # 4px — match PageTitleBar internal spacing
        # Full-width separator — spans the title pill AND the CAN TOOLS button.
        # Must be added here (outside header_row) so it occupies the full
        # page width rather than only the width of the PageTitleBar column.
        root.addWidget(HSep())
        root.addSpacing(14)  # 14px — spacing before cards/message section
        logger.debug("[UI] CanPage: full-width HSep added after header row")

        # Channel cards — all on one horizontal line
        if can_channels:
            cards_widget = QWidget()
            cards_widget.setStyleSheet("background: transparent;")
            cards_row = QHBoxLayout(cards_widget)
            cards_row.setContentsMargins(0, 0, 0, 0)
            cards_row.setSpacing(16)
            cards_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            for ch in can_channels:
                card = CanChannelCard(ch)
                card.baudrate_changed.connect(self.baudrate_changed)
                cards_row.addWidget(card)
                self._cards[ch.node_id] = card

            cards_row.addStretch()
            root.addWidget(cards_widget)
        else:
            msg = QLabel("No CAN channels detected.\nPlug in a PCAN adapter — it will be picked up automatically.")
            msg.setObjectName("CanNoneMsg")
            msg.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            root.addWidget(msg)

        # CAN monitor — profile passed so it never re-detects the OS
        self._monitor = CanMonitorWidget(can_channels, profile=profile)
        root.addWidget(self._monitor)

    def set_connection(self, node_id: str, connected: bool) -> None:
        if node_id in self._cards:
            self._cards[node_id].set_connected(connected)
        self._monitor.notify_channel_connection(node_id, connected)


# ══════════════════════════════════════════════════════════════════
# CAN TOOLS PAGE  (stack index 16)
# ══════════════════════════════════════════════════════════════════

