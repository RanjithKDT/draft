from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QLayout, QLayoutItem
from PySide6.QtCore import Qt, Signal, QTimer, QRect, QPoint, QSize
from PySide6.QtGui import QPixmap
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.icons import IconWidget
from simulator.gui.constants import PROJECT_ROOT
from simulator.network.internet_monitor import InternetMonitor


# ── Logo label with hidden 6-click easter egg ─────────────────────────────────

class _LogoLabel(QLabel):
    """
    Hyva logo label that tracks 6 consecutive left-clicks.

    Rules
    -----
    - Each click must arrive within 2 seconds of the previous one.
    - If the gap exceeds 2 seconds the counter resets to 1 (current click counts).
    - On the 6th valid click: ``credits_triggered`` is emitted and counter resets.
    - All state is instance-local — no globals, no class variables.
    - Runs entirely on the GUI thread (QTimer, mousePressEvent).
    """

    #: Emitted once when exactly 6 consecutive clicks are detected.
    credits_triggered = Signal()

    #: Max milliseconds between consecutive clicks before counter resets.
    _TIMEOUT_MS: int = 2000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._click_count: int = 0

        # Single-shot timer — fires if the user pauses > _TIMEOUT_MS.
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.setInterval(self._TIMEOUT_MS)
        self._reset_timer.timeout.connect(self._on_timeout)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            # Stop the pending timeout — we received a click in time.
            self._reset_timer.stop()

            self._click_count += 1
            logger.debug(f"[LOGO] Easter egg click {self._click_count}/6")

            if self._click_count >= 6:
                self._click_count = 0
                logger.info("[LOGO] Easter egg triggered — opening Credits")
                self.credits_triggered.emit()
            else:
                # Start (restart) the inter-click deadline.
                self._reset_timer.start()

        super().mousePressEvent(event)

    def _on_timeout(self) -> None:
        """Called when the user pauses > _TIMEOUT_MS between clicks."""
        if self._click_count > 0:
            logger.debug(
                f"[LOGO] Easter egg timeout — resetting ({self._click_count} clicks lost)"
            )
        self._click_count = 0


class TopHeader(QWidget):
    """
    A — Top header bar.

    Contains (left → right):
      • Hyva logo
      • Vertical divider
      • "HYVA SIMULATOR" title pill
      • Stretch
      • Local date + time pill
      • UTC time pill
      • Internet status pill  ← NEW in v2.0.3

    The internet status pill shows:
      • Amber dot + "CHECKING…" — initial state, probe in progress
      • Green dot  + "ONLINE"   — at least one probe host is reachable
      • Red dot    + "OFFLINE"  — all probe hosts unreachable

    The InternetMonitor background thread is owned by this widget and is
    started automatically.  It is stopped and joined when the widget is
    destroyed (``closeEvent`` / ``deleteLater``).
    """

    # ── Pill colour constants ─────────────────────────────────────────────────
    _NET_COLOUR_CHECKING: str = "#A38600"   # amber — probing in progress
    _NET_COLOUR_ONLINE:   str = "#22C55E"   # green — reachable
    _NET_COLOUR_OFFLINE:  str = "#CC1020"   # red   — unreachable

    _NET_BORDER_CHECKING: str = "#333333"
    _NET_BORDER_ONLINE:   str = "#14532D"   # subtle green tint
    _NET_BORDER_OFFLINE:  str = "#4A0000"   # subtle red tint

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(60)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 10, 20, 10)
        row.setSpacing(0)

        # ── Logo — tracks 6-click easter egg ────────────────────────
        # _LogoLabel emits credits_triggered after 6 consecutive clicks
        # within a 2-second inter-click window.  MainWindow wires this
        # signal to AboutPage.open_credits() after both widgets exist.
        self._logo_lbl = _LogoLabel(self)
        logo_path = PROJECT_ROOT / "assets" / "logo" / "hyva_logo.jpg"
        if logo_path.exists():
            px = QPixmap(str(logo_path))
            self._logo_lbl.setPixmap(px.scaledToHeight(38, Qt.SmoothTransformation))
        else:
            self._logo_lbl.setText("HYVA")
            self._logo_lbl.setStyleSheet("color:#CC1020; font-size:13px; font-weight:bold;")
            logger.warning(f"Logo not found: {logo_path}")
        self._logo_lbl.setFixedWidth(88)
        self._logo_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._logo_lbl.setCursor(Qt.PointingHandCursor)   # subtle affordance
        row.addWidget(self._logo_lbl)

        # Thin vertical divider
        div = QFrame()
        div.setObjectName("HeaderDivider")
        div.setFrameShape(QFrame.VLine)
        div.setFixedSize(1, 26)
        row.addWidget(div)

        row.addSpacing(18)

        # ── Title pill ────────────────────────────────────────────
        title_pill = QWidget()
        title_pill.setObjectName("TitlePill")
        title_pill.setAttribute(Qt.WA_StyledBackground, True)
        title_pill.setStyleSheet("""
            QWidget#TitlePill {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-left: 3px solid #FFD100;
                border-radius: 8px;
            }
        """)
        title_pill_row = QHBoxLayout(title_pill)
        title_pill_row.setContentsMargins(12, 0, 16, 0)
        title_pill_row.setSpacing(8)

        dot = IconWidget(fa="fa6s.diamond", fallback="◆", colour="#FFD100", size=6)
        title_pill_row.addWidget(dot)

        title = QLabel("HYVA SIMULATOR")
        title.setObjectName("HeaderTitle")
        title_pill_row.addWidget(title)

        row.addWidget(title_pill)

        row.addStretch()

        # ── Clock + status pills ──────────────────────────────────
        # Wrap all pills in a container with vertical padding so they
        # never touch the header top/bottom edges.
        clock_wrap = QWidget()
        clock_wrap.setStyleSheet("background: transparent;")
        clock_row = QHBoxLayout(clock_wrap)
        clock_row.setContentsMargins(0, 10, 0, 10)   # 10px top+bottom gap
        clock_row.setSpacing(8)

        # Pill 1: Date + local time
        self._local_pill = QWidget()
        self._local_pill.setObjectName("ClockPill")
        self._local_pill.setAttribute(Qt.WA_StyledBackground, True)
        self._local_pill.setStyleSheet("""
            QWidget#ClockPill {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        local_layout = QHBoxLayout(self._local_pill)
        local_layout.setContentsMargins(12, 0, 12, 0)
        local_layout.setSpacing(8)

        cal_icon = IconWidget(fa="fa6s.calendar-days", fallback="▦", colour="#666666", size=11)
        local_layout.addWidget(cal_icon)

        self._date_lbl = QLabel()
        self._date_lbl.setObjectName("ClockDate")
        local_layout.addWidget(self._date_lbl)

        vdiv1 = QFrame()
        vdiv1.setFrameShape(QFrame.VLine)
        vdiv1.setFixedSize(1, 16)
        vdiv1.setStyleSheet("color: #383838; background: #383838;")
        local_layout.addWidget(vdiv1)

        clk_icon = IconWidget(fa="fa6s.clock", fallback="◷", colour="#666666", size=11)
        local_layout.addWidget(clk_icon)

        self._time_lbl = QLabel()
        self._time_lbl.setObjectName("ClockTime")
        local_layout.addWidget(self._time_lbl)

        clock_row.addWidget(self._local_pill)

        # Pill 2: UTC time
        self._utc_pill = QWidget()
        self._utc_pill.setObjectName("UtcPill")
        self._utc_pill.setAttribute(Qt.WA_StyledBackground, True)
        self._utc_pill.setStyleSheet("""
            QWidget#UtcPill {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        utc_layout = QHBoxLayout(self._utc_pill)
        utc_layout.setContentsMargins(12, 0, 12, 0)
        utc_layout.setSpacing(8)

        utc_globe = IconWidget(fa="fa6s.globe", fallback="⊕", colour="#666666", size=11)
        utc_layout.addWidget(utc_globe)
        utc_badge = QLabel("UTC")
        utc_badge.setObjectName("UtcBadge")
        utc_layout.addWidget(utc_badge)

        vdiv2 = QFrame()
        vdiv2.setFrameShape(QFrame.VLine)
        vdiv2.setFixedSize(1, 16)
        vdiv2.setStyleSheet("color: #383838; background: #383838;")
        utc_layout.addWidget(vdiv2)

        self._utc_lbl = QLabel()
        self._utc_lbl.setObjectName("ClockTime")
        utc_layout.addWidget(self._utc_lbl)

        clock_row.addWidget(self._utc_pill)

        # Pill 3: Internet status  ─────────────────────────────────
        # Starts in CHECKING state (amber).  InternetMonitor updates it
        # dynamically via _on_internet_status_changed().
        self._net_pill = QWidget()
        self._net_pill.setObjectName("NetPill")
        self._net_pill.setAttribute(Qt.WA_StyledBackground, True)

        net_layout = QHBoxLayout(self._net_pill)
        net_layout.setContentsMargins(10, 0, 10, 0)
        net_layout.setSpacing(6)

        # WiFi icon — colour encodes status at a glance (amber/green/red)
        # Matches UTC globe and date calendar icon style exactly.
        self._net_icon = IconWidget(
            fa="fa6s.wifi",
            fallback="◎",
            colour=self._NET_COLOUR_CHECKING,
            size=11,
        )

        # Text label: CHECKING… / ONLINE / OFFLINE
        self._net_lbl = QLabel("CHECKING…")
        self._net_lbl.setObjectName("NetLabel")

        net_layout.addWidget(self._net_icon)
        net_layout.addWidget(self._net_lbl)

        clock_row.addWidget(self._net_pill)

        # Apply initial CHECKING style
        self._apply_net_pill_style(
            dot_colour=self._NET_COLOUR_CHECKING,
            border_colour=self._NET_BORDER_CHECKING,
        )

        row.addWidget(clock_wrap)

        # ── Clock tick timer ──────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

        # ── Internet monitor — background thread ──────────────────
        logger.info("[NET] Starting InternetMonitor thread")
        self._net_monitor = InternetMonitor(parent=self)
        self._net_monitor.status_changed.connect(self._on_internet_status_changed)
        self._net_monitor.start()
        logger.debug("[NET] InternetMonitor thread launched")

    # ── Clock tick ────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        """Update local date/time and UTC time labels every second."""
        from datetime import datetime, timezone
        now_local = datetime.now()
        now_utc   = datetime.now(timezone.utc)
        self._date_lbl.setText(now_local.strftime("%d %b %Y"))
        self._time_lbl.setText(now_local.strftime("%H:%M:%S"))
        self._utc_lbl.setText(now_utc.strftime("%H:%M:%S"))

    # ── Internet status callbacks ─────────────────────────────────────────────

    def _on_internet_status_changed(self, is_online: bool) -> None:
        """
        Slot — called on the GUI thread whenever InternetMonitor detects
        a genuine state flip (CHECKING→*, ONLINE→OFFLINE, OFFLINE→ONLINE).
        Updates the NetPill visual and logs the transition.
        """
        if is_online:
            logger.info("[NET] UI update → ONLINE")
            self._net_lbl.setText("ONLINE")
            self._apply_net_pill_style(
                dot_colour=self._NET_COLOUR_ONLINE,
                border_colour=self._NET_BORDER_ONLINE,
            )
        else:
            logger.warning("[NET] UI update → OFFLINE")
            self._net_lbl.setText("OFFLINE")
            self._apply_net_pill_style(
                dot_colour=self._NET_COLOUR_OFFLINE,
                border_colour=self._NET_BORDER_OFFLINE,
            )

    def _apply_net_pill_style(
        self,
        dot_colour: str,
        border_colour: str,
    ) -> None:
        """
        Apply pill + icon stylesheet atomically.
        Called from the GUI thread only — safe to touch QWidgets directly.
        """
        self._net_pill.setStyleSheet(f"""
            QWidget#NetPill {{
                background-color: #1E1E1E;
                border: 1px solid {border_colour};
                border-radius: 8px;
            }}
        """)
        # Recolour the WiFi icon — same pattern as UTC globe and date calendar
        self._net_icon.set_colour(dot_colour)
        self._net_lbl.setStyleSheet(
            f"color: {dot_colour}; font-size: 9px; "
            f"letter-spacing: 1px; font-weight: bold; background: transparent;"
        )

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Stop the background monitor thread before the widget is destroyed."""
        logger.debug("[NET] TopHeader closing — stopping InternetMonitor")
        self._net_monitor.stop()
        # Give the thread up to 3 seconds to exit cleanly.
        if not self._net_monitor.wait(3000):
            logger.warning("[NET] InternetMonitor did not stop within 3 s — terminating")
            self._net_monitor.terminate()
        super().closeEvent(event)


# ══════════════════════════════════════════════════════════════════
# SEPARATORS
# ══════════════════════════════════════════════════════════════════

# RedSepH imported from simulator.gui.components (QWidget-based, not QFrame)
# QFrame renders white on Windows/Fusion style — QWidget is cross-platform safe.


class FlowLayout(QLayout):
    """
    Wrapping flow layout — arranges widgets left-to-right, wraps to the
    next row when the available width is exhausted.  Used in the footer
    pill strip so all pills are always visible on any screen size.
    """

    def __init__(self, parent: "QWidget | None" = None, h_spacing: int = 6, v_spacing: int = 4) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> "QLayoutItem | None":
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> "QLayoutItem | None":
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> "Qt.Orientations":
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), dry_run=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, dry_run=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, dry_run: bool) -> int:
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        row_height = 0
        line_x = x

        for item in self._items:
            w = item.widget()
            hint = item.sizeHint()
            iw, ih = hint.width(), hint.height()

            if line_x + iw > rect.right() - m.right() and line_x > x:
                # wrap to next row
                y += row_height + self._v_spacing
                line_x = x
                row_height = 0

            if not dry_run:
                item.setGeometry(QRect(QPoint(line_x, y + (row_height - ih) // 2 if row_height > ih else y), hint))

            line_x += iw + self._h_spacing
            row_height = max(row_height, ih)

        return y + row_height - rect.y() + m.bottom()


# RedSepV imported from simulator.gui.components (QWidget-based, not QFrame)


# ══════════════════════════════════════════════════════════════════
# C — SIDEBAR  (plug card design)
# ══════════════════════════════════════════════════════════════════



# _repaint_icon removed — use IconWidget.set_colour() from simulator.gui.icons


