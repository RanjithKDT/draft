from __future__ import annotations

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QFrame, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QButtonGroup, QRadioButton, QAbstractItemView, QFileDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.icons import IconWidget
from simulator.gui.components import PageTitleBar, HSep
from simulator.platform.platform_detector import PlatformProfile
from simulator.platform.can_detector import CanChannel

# DLC values allowed in the frame builder (CAN + CAN-FD)
_DLC_OPTIONS: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64)

# ── Button stylesheets — defined once, applied to every CanToolsPage instance ─
_CONT_BTN_SS_OFF = f"""
    QPushButton {{
        background-color: {t.BG_PILL_NEUTRAL};
        color: {t.TEXT_LABEL};
        border: 1px solid {t.BORDER_SOFT};
        border-radius: {t.RADIUS_SM}px;
        font-size: {t.SIZE_SM}px;
        font-weight: bold;
        letter-spacing: {t.TRACKING_NORMAL};
        padding: 0 14px;
    }}
    QPushButton:hover {{
        background-color: {t.NEUTRAL_HOVER};
        border-color: {t.BORDER_STRONG};
        color: {t.TEXT_BRIGHT};
    }}
    QPushButton:pressed {{ background-color: {t.NEUTRAL_PRESSED}; }}
"""

_CONT_BTN_SS_ON = f"""
    QPushButton {{
        background-color: {t.RED};
        color: {t.TEXT_ON_RED};
        border: none;
        border-radius: {t.RADIUS_SM}px;
        font-size: {t.SIZE_SM}px;
        font-weight: bold;
        letter-spacing: {t.TRACKING_NORMAL};
        padding: 0 14px;
    }}
    QPushButton:hover   {{ background-color: {t.RED_HOVER}; }}
    QPushButton:pressed {{ background-color: {t.RED_PRESSED}; }}
"""

_SEND_FRAME_SS = f"""
    QPushButton {{
        background-color: {t.YELLOW};
        color: {t.TEXT_ON_YELLOW};
        border: none;
        border-radius: {t.RADIUS_SM}px;
        font-size: {t.SIZE_MD}px;
        font-weight: bold;
        letter-spacing: {t.TRACKING_WIDE};
    }}
    QPushButton:hover    {{ background-color: {t.YELLOW_HOVER}; }}
    QPushButton:pressed  {{ background-color: {t.YELLOW_PRESSED}; }}
    QPushButton:disabled {{
        background-color: {t.YELLOW_DISABLED_BG};
        color: {t.YELLOW_DISABLED_TEXT};
    }}
"""


class CanToolsPage(QWidget):
    """
    Dedicated page for CAN file analysis and message building.

    Layout
    ------
    Left panel  (45%) : File loader + CAN ID / message browser table
    Right panel (55%) : Message builder (channel, frame type, ID, data) + SEND

    File types supported
    --------------------
    Database (.dbc, .kcd, .arxml) — shows message definitions + signals.
    Log      (.asc, .blf, .trc, .log, .csv, .txt) — shows recorded frames.

    Interaction flow
    ----------------
    1. User clicks Browse → picks a file.
    2. File is parsed; messages or frames appear in the browser table.
    3. User clicks a row → arb ID, DLC, and data placeholder auto-fill on the right.
    4. User edits the data bytes if needed, picks a channel, and clicks SEND.
    5. One-shot python-can bus: open → send → close.

    Navigation
    ----------
    "← CAN" button walks up the widget tree to find MainWindow._switch_page(1).
    This reuses the same pattern as _ProductPage._go_home().
    """

    # Card accent colour for the left panel header
    _C_LEFT  = "#FFD100"    # Hyva yellow
    # Card accent colour for the right panel header
    _C_RIGHT = "#38BDF8"    # Sky blue — consistent with existing Send header

    def __init__(
        self,
        profile: PlatformProfile,
        can_channels: list[CanChannel],
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        self._profile      = profile
        self._can_channels = can_channels
        # Loaded message definitions — used for signal sub-table
        self._loaded_defs: list = []   # list[CanMessageDef]

        # Pill selector state — current value for each selector
        self._selected_channel  = can_channels[0] if can_channels else None
        self._selected_dlc_val: int = 8

        # Continuous send timer — started/stopped by _toggle_continuous()
        self._cont_timer = QTimer(self)
        self._cont_timer.timeout.connect(self._on_continuous_tick)

        # Tracks connection state per channel node_id — drives the send button dot
        self._channel_states: dict[str, bool] = {
            ch.node_id: False for ch in can_channels
        }

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)

        # ── Title bar row ─────────────────────────────────────────
        # PageTitleBar has show_separator=False so its internal HSep is
        # suppressed.  A standalone HSep is added BELOW this entire row
        # so the separator line runs full-width — spanning both the title
        # pill column AND the back button.
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(12)

        title_row.addWidget(
            PageTitleBar("CAN TOOLS", show_separator=False),
            stretch=1,
        )

        back_btn = QPushButton("← CAN")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedHeight(26)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t.TEXT_DIM};
                border: 1px solid {t.BORDER_STRONG};
                border-radius: 13px;
                font-size: 10px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                color: {t.RED};
                border-color: {t.RED};
                background-color: #1A0000;
            }}
        """)
        back_btn.clicked.connect(self._go_can)
        title_row.addWidget(back_btn, stretch=0, alignment=Qt.AlignVCenter)

        root.addLayout(title_row)
        # Full-width separator — spans the title pill AND the back button.
        root.addWidget(HSep())
        logger.debug("[UI] CanToolsPage: full-width HSep added after title row")

        # ── Two-panel body ────────────────────────────────────────
        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(12)

        body_row.addWidget(self._build_left_panel(),  stretch=45)
        body_row.addWidget(self._build_right_panel(), stretch=55)

        root.addLayout(body_row)

    # ── Navigation ────────────────────────────────────────────────

    def _go_can(self) -> None:
        """Walk up the widget tree to find MainWindow and switch to CAN page."""
        obj = self
        while obj is not None:
            switch_fn = getattr(obj, "_switch_page", None)
            if callable(switch_fn):
                switch_fn(1)
                return
            obj = obj.parent()
        logger.warning("[CAN TOOLS] MainWindow not found in widget tree — cannot navigate back")

    # ── Panel builders ────────────────────────────────────────────

    def _panel_card(self, accent: str) -> tuple[QWidget, QVBoxLayout]:
        """Return (card_widget, inner_layout) with a top accent border."""
        card = QWidget()
        card.setObjectName("CanToolsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            QWidget#CanToolsCard {{
                background-color: #161616;
                border: 1px solid #2A2A2A;
                border-top: 2px solid {accent};
                border-radius: 8px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(10)
        return card, lay

    def _panel_header(self, layout: QVBoxLayout, fa_icon: str,
                      fallback: str, title: str, color: str) -> None:
        """Add a standard section header (icon + title) to a panel layout."""
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(IconWidget(fa=fa_icon, fallback=fallback, colour=color, size=13))
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 11px; letter-spacing: 2px; "
            "font-weight: bold; background: transparent;"
        )
        row.addWidget(lbl)
        row.addStretch()
        layout.addLayout(row)

    # ── Left panel — file loader + browser ────────────────────────

    def _build_left_panel(self) -> QWidget:
        card, lay = self._panel_card(self._C_LEFT)
        self._panel_header(lay, "fa6s.folder-open", "📂",
                           "FILE BROWSER", self._C_LEFT)

        # File selection row
        file_row = QHBoxLayout()
        file_row.setSpacing(8)

        self._file_label = QLabel("No file loaded")
        self._file_label.setStyleSheet(
            f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;"
        )
        self._file_label.setMinimumWidth(100)
        file_row.addWidget(self._file_label, stretch=1)

        browse_btn = QPushButton("📁  Browse…")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setFixedHeight(26)
        browse_btn.setStyleSheet(self._btn_style(t.YELLOW))
        browse_btn.clicked.connect(self._on_browse)
        file_row.addWidget(browse_btn)

        clear_btn = QPushButton("✕")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setFixedSize(26, 26)
        clear_btn.setStyleSheet(self._btn_style(t.TEXT_DIM))
        clear_btn.clicked.connect(self._on_clear)
        file_row.addWidget(clear_btn)

        lay.addLayout(file_row)

        # Status label (row count / error)
        self._file_status = QLabel("")
        self._file_status.setStyleSheet(
            "font-size: 10px; background: transparent; "
            f"color: {t.TEXT_DIM};"
        )
        self._file_status.setWordWrap(True)
        lay.addWidget(self._file_status)

        # Browser table — shows message defs OR log frames
        self._browser_table = QTableWidget(0, 4)
        self._browser_table.setObjectName("MonTable")   # reuse existing MonTable QSS
        self._browser_table.verticalHeader().setVisible(False)
        self._browser_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._browser_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._browser_table.setAlternatingRowColors(True)
        self._browser_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._browser_table.setColumnWidth(0, 100)
        self._browser_table.setColumnWidth(2, 40)
        self._browser_table.setColumnWidth(3, 50)
        self._browser_table.itemSelectionChanged.connect(self._on_browser_selection)
        lay.addWidget(self._browser_table)

        # Signal sub-table (only populated for DB message defs)
        sig_lbl = QLabel("SIGNALS  (select a message above)")
        sig_lbl.setStyleSheet(
            f"color: {t.TEXT_DIM}; font-size: 9px; "
            "letter-spacing: 1px; background: transparent;"
        )
        lay.addWidget(sig_lbl)

        self._signal_table = QTableWidget(0, 5)
        self._signal_table.setObjectName("MonTable")
        self._signal_table.setHorizontalHeaderLabels(
            ["SIGNAL", "BITS", "FACTOR", "OFFSET", "UNIT"]
        )
        self._signal_table.verticalHeader().setVisible(False)
        self._signal_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._signal_table.setAlternatingRowColors(True)
        self._signal_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._signal_table.setColumnWidth(1, 55)
        self._signal_table.setColumnWidth(2, 60)
        self._signal_table.setColumnWidth(3, 60)
        self._signal_table.setColumnWidth(4, 50)
        self._signal_table.setFixedHeight(110)
        lay.addWidget(self._signal_table)

        return card

    # ── Right panel — message builder + send ──────────────────────

    def _build_right_panel(self) -> QWidget:
        """
        Build the Build & Send panel — coordinates three section builders.

        Layout:
          Section 1 — Frame Config  : CHANNEL pill + FRAME TYPE radio buttons
          Section 2 — Frame Data    : ARB ID field + DATA BYTES field + DLC row
          Section 3 — Actions       : SEND FRAME + Continuous + INTERVAL + status
        """
        card, lay = self._panel_card(self._C_RIGHT)
        self._panel_header(lay, "fa6s.paper-plane", "➤",
                           "BUILD & SEND", self._C_RIGHT)

        lay.addLayout(self._build_s1_frame_config())
        lay.addWidget(self._h_sep())
        lay.addLayout(self._build_s2_frame_data())
        lay.addWidget(self._h_sep())
        lay.addLayout(self._build_s3_actions())
        lay.addStretch()

        return card

    def _build_s1_frame_config(self) -> QVBoxLayout:
        """Build Section 1: CHANNEL pill and FRAME TYPE radio buttons."""
        first_label = (
            f"{self._can_channels[0].name}  —  {self._can_channels[0].bitrate_label}"
            if self._can_channels else "No channels"
        )
        self._ch_btn = QPushButton(first_label + "  ▼")
        self._ch_btn.setObjectName("MonChBtn")
        self._ch_btn.setCursor(Qt.PointingHandCursor)
        self._ch_btn.setEnabled(bool(self._can_channels))
        self._ch_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._ch_btn.setFixedHeight(28)
        self._ch_btn.clicked.connect(self._show_channel_pill_menu)

        self._type_grp = QButtonGroup(self)
        rb_row = QHBoxLayout()
        rb_row.setSpacing(16)
        rb_row.setContentsMargins(0, 0, 0, 0)
        for i, label in enumerate(["Standard", "Extended (29-bit)", "J1939"]):
            rb = QRadioButton(label)
            rb.setObjectName("FrameTypeRb")
            rb.setCursor(Qt.PointingHandCursor)
            if i == 0:
                rb.setChecked(True)
            self._type_grp.addButton(rb, i)
            rb_row.addWidget(rb)
        rb_row.addStretch()

        s1 = QVBoxLayout()
        s1.setContentsMargins(0, 8, 0, 8)
        s1.setSpacing(6)
        s1.addWidget(self._section_label("CHANNEL"))
        s1.addWidget(self._ch_btn)
        s1.addSpacing(4)
        s1.addWidget(self._section_label("FRAME TYPE"))
        s1.addLayout(rb_row)
        return s1

    def _build_s2_frame_data(self) -> QVBoxLayout:
        """Build Section 2: ARB ID field, DATA BYTES field, and DLC row."""
        # ARB ID field with 'hex' hint aligned right
        arb_id_header = QHBoxLayout()
        arb_id_header.setContentsMargins(0, 0, 0, 0)
        arb_id_header.addWidget(self._section_label("ARB ID"))
        arb_id_header.addStretch()
        hex_hint = QLabel("hex")
        hex_hint.setStyleSheet(
            f"color: {t.TEXT_DIM}; font-size: 9px; background: transparent;"
        )
        arb_id_header.addWidget(hex_hint)

        self._arb_id_edit = QLineEdit()
        self._arb_id_edit.setObjectName("SendField")
        self._arb_id_edit.setFixedHeight(28)
        self._arb_id_edit.setPlaceholderText("e.g.  7E8   or   18FF0063")

        # DATA BYTES — space-separated hex, e.g. "00 64 32 00 00 00 00 00"
        self._data_edit = QLineEdit()
        self._data_edit.setObjectName("SendField")
        self._data_edit.setFixedHeight(28)
        self._data_edit.setPlaceholderText("e.g.  00 64 32 00 00 00 00 00")
        self._data_edit.textChanged.connect(self._update_dlc_info)

        # DLC pill + Fill Zeros + byte count label
        self._dlc_btn = QPushButton(f"{self._selected_dlc_val}  ▼")
        self._dlc_btn.setObjectName("MonChBtn")
        self._dlc_btn.setCursor(Qt.PointingHandCursor)
        self._dlc_btn.setFixedWidth(72)
        self._dlc_btn.setFixedHeight(28)
        self._dlc_btn.clicked.connect(self._show_dlc_pill_menu)

        fill_btn = self._make_fill_zeros_btn()

        self._dlc_info_lbl = QLabel("0 bytes")
        self._dlc_info_lbl.setStyleSheet(
            f"color: {t.YELLOW}; font-size: 10px; "
            "font-weight: bold; background: transparent;"
        )

        dlc_row = QHBoxLayout()
        dlc_row.setContentsMargins(0, 0, 0, 0)
        dlc_row.setSpacing(8)
        dlc_row.addWidget(self._section_label("DLC"))
        dlc_row.addWidget(self._dlc_btn)
        dlc_row.addWidget(fill_btn)
        dlc_row.addStretch()
        dlc_row.addWidget(self._dlc_info_lbl)

        s2 = QVBoxLayout()
        s2.setContentsMargins(0, 8, 0, 8)
        s2.setSpacing(6)
        s2.addLayout(arb_id_header)
        s2.addWidget(self._arb_id_edit)
        s2.addSpacing(4)
        s2.addWidget(self._section_label("DATA BYTES"))
        s2.addWidget(self._data_edit)
        s2.addLayout(dlc_row)
        return s2

    def _make_fill_zeros_btn(self) -> QPushButton:
        """Create and return the styled FILL ZEROS button."""
        btn = QPushButton("FILL ZEROS")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(34)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.YELLOW};
                color: #111111;
                border: none;
                border-radius: 5px;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1.5px;
                padding: 0 16px;
            }}
            QPushButton:hover   {{ background-color: #E8BA00; }}
            QPushButton:pressed {{ background-color: #C9A000; }}
        """)
        btn.setToolTip(
            "Pad data bytes to the selected DLC with 00.\n"
            "Bytes you have already typed are preserved.\n"
            "Example:  '64' at DLC 8  →  '64 00 00 00 00 00 00 00'"
        )
        btn.clicked.connect(self._fill_zeros)
        return btn

    def _build_s3_actions(self) -> QVBoxLayout:
        """Build Section 3: SEND FRAME, Continuous, INTERVAL input, status label."""
        self._conn_dot_lbl = QLabel("●")
        self._conn_dot_lbl.setStyleSheet(
            f"color: {t.RED}; font-size: 10px; background: transparent;"
        )

        send_btn = QPushButton("SEND FRAME")
        send_btn.setFixedHeight(34)
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.setEnabled(bool(self._can_channels))
        send_btn.setStyleSheet(_SEND_FRAME_SS)
        send_btn.clicked.connect(self._on_send)

        self._cont_btn = QPushButton("⇄  Continuous")
        self._cont_btn.setFixedHeight(34)
        self._cont_btn.setCursor(Qt.PointingHandCursor)
        self._cont_btn.setEnabled(bool(self._can_channels))
        self._cont_btn.setCheckable(False)
        self._cont_btn.setStyleSheet(_CONT_BTN_SS_OFF)
        self._cont_btn.clicked.connect(self._toggle_continuous)

        send_row = QHBoxLayout()
        send_row.setSpacing(8)
        send_row.setContentsMargins(0, 0, 0, 0)
        send_row.addWidget(self._conn_dot_lbl)
        send_row.addWidget(send_btn, stretch=3)
        send_row.addWidget(self._cont_btn, stretch=2)

        # Interval text input — user types a number, "ms" label shows the unit
        self._interval_edit = QLineEdit("500")
        self._interval_edit.setObjectName("SendField")
        self._interval_edit.setFixedWidth(72)
        self._interval_edit.setFixedHeight(28)
        self._interval_edit.setPlaceholderText("500")
        self._interval_edit.setToolTip(
            "Continuous send interval in milliseconds.\n"
            "Valid range: 10 – 60000 ms."
        )
        # Accept only digits — unit label shows "ms"
        from PySide6.QtGui import QIntValidator
        self._interval_edit.setValidator(QIntValidator(10, 60000, self._interval_edit))
        # Update running timer when value changes mid-session
        self._interval_edit.textChanged.connect(self._on_interval_changed)

        ms_label = QLabel("ms")
        ms_label.setStyleSheet(
            f"color: {t.TEXT_DIM}; font-size: 10px; background: transparent;"
        )

        int_row = QHBoxLayout()
        int_row.setSpacing(6)
        int_row.setContentsMargins(0, 0, 0, 0)
        int_row.addWidget(self._section_label("INTERVAL"))
        int_row.addWidget(self._interval_edit)
        int_row.addWidget(ms_label)
        int_row.addStretch()

        self._send_result = QLabel("")
        self._send_result.setWordWrap(True)
        self._send_result.setAlignment(Qt.AlignCenter)
        self._send_result.setStyleSheet(
            f"font-size: 10px; background: transparent; color: {t.TEXT_DIM};"
        )
        self._send_result.setMinimumHeight(16)

        s3 = QVBoxLayout()
        s3.setContentsMargins(0, 8, 0, 4)
        s3.setSpacing(8)
        s3.addLayout(send_row)
        s3.addLayout(int_row)
        s3.addWidget(self._send_result)
        return s3

    def _section_label(self, text: str) -> QLabel:
        """Return a small uppercase dimmed label used as a field caption."""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {t.TEXT_DIM}; font-size: 9px; "
            "letter-spacing: 1px; background: transparent;"
        )
        return lbl

    def _h_sep(self) -> QFrame:
        """Thin horizontal separator between sections."""
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {t.BORDER_FAINT}; border: none;")
        sep.setFixedHeight(1)
        return sep

    @staticmethod
    def _btn_style(color: str) -> str:
        """Return QSS for a small bordered button with the given accent colour."""
        return f"""
            QPushButton {{
                background-color: #1C1C1C;
                color: {color};
                border: 1px solid {color};
                border-radius: 4px;
                font-size: 10px;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background-color: #1A1200;
                color: #E8BA00;
                border-color: #E8BA00;
            }}
        """

    # ── DLC info readout ──────────────────────────────────────────

    def _update_dlc_info(self, text: str) -> None:
        """Recompute DLC from the data bytes field and update the readout label."""
        n = len(text.split()) if text.strip() else 0
        self._dlc_info_lbl.setText(f"{n} byte{'s' if n != 1 else ''}")

    # ── Fill Zeros ────────────────────────────────────────────────

    def _sync_data_to_dlc(self, old_dlc: int, new_dlc: int) -> None:
        """
        Adjust the DATA BYTES field when the user changes the DLC.

        Rules:
          - New DLC < current token count  → trim to new_dlc bytes
          - New DLC > current token count  → pad with zeros up to new_dlc
          - New DLC == current token count → no change

        This keeps the field consistent with the selected DLC at all times.
        """
        tokens = self._data_edit.text().split()
        current = len(tokens)

        if current == new_dlc:
            return

        if current > new_dlc:
            # Trim excess bytes
            trimmed = tokens[:new_dlc]
            self._data_edit.setText(" ".join(trimmed))
            logger.info(
                f"[CAN TOOLS] DLC {old_dlc}→{new_dlc}: "
                f"trimmed {current - new_dlc} bytes (kept first {new_dlc})"
            )
        else:
            # Pad with zeros
            pad = new_dlc - current
            self._data_edit.setText(" ".join(tokens + ["00"] * pad))
            logger.info(
                f"[CAN TOOLS] DLC {old_dlc}→{new_dlc}: "
                f"padded {pad} zeros → {new_dlc} bytes"
            )

    def _fill_zeros(self) -> None:
        """
        Fill the DATA BYTES field to exactly the selected DLC.

        - If fewer bytes than DLC → pad trailing bytes with '00'
        - If more bytes than DLC  → trim to DLC (data was from a previous
          larger DLC and user pressed Fill Zeros to confirm the new size)
        - If equal                → no change needed

        The selected DLC is the single source of truth.
        """
        target = self._selected_dlc_val
        existing = self._data_edit.text().split()
        current = len(existing)

        if current == target:
            logger.debug(
                f"[CAN TOOLS] Fill Zeros: already {current} bytes "
                f"(target={target}) — no change"
            )
            return

        if current > target:
            # Trim to target — user switched to smaller DLC
            result = " ".join(existing[:target])
            self._data_edit.setText(result)
            logger.info(
                f"[CAN TOOLS] Fill Zeros: trimmed {current} → {target} bytes"
            )
        else:
            # Pad with zeros
            pad_count = target - current
            result = " ".join(existing + ["00"] * pad_count)
            self._data_edit.setText(result)
            logger.info(
                f"[CAN TOOLS] Fill Zeros: {current} existing + "
                f"{pad_count} zeros → {target} bytes"
            )

    # ── Data byte parser ──────────────────────────────────────────

    @staticmethod
    def _parse_data_bytes(text: str) -> bytes:
        """
        Parse a space-separated hex byte string into bytes.

        Args:
            text: e.g. "01 02 03 04"

        Returns:
            bytes object.

        Raises:
            ValueError with a clear message if any token is invalid.
        """
        tokens = text.split()
        result: list[int] = []
        for token in tokens:
            try:
                value = int(token, 16)
            except ValueError:
                raise ValueError(
                    f"'{token}' is not valid hex. Use bytes like: 00 64 FF"
                )
            if not 0 <= value <= 0xFF:
                raise ValueError(
                    f"'{token}' = {value} is out of byte range 0x00–0xFF."
                )
            result.append(value)
        return bytes(result)

    # ── Continuous send ───────────────────────────────────────────

    def _toggle_continuous(self) -> None:
        """Start or stop the continuous send timer."""
        if self._cont_timer.isActive():
            self._cont_timer.stop()
            self._cont_btn.setText("⇄  Continuous")
            self._cont_btn.setStyleSheet(_CONT_BTN_SS_OFF)
            self._show_result("Continuous send stopped", ok=True)
            logger.info("[CAN TOOLS] Continuous send stopped")
        else:
            interval_ms = self._read_interval_ms()
            if interval_ms is None:
                return   # validation error shown by _read_interval_ms
            self._cont_timer.start(interval_ms)
            self._cont_btn.setText("■  Stop")
            self._cont_btn.setStyleSheet(_CONT_BTN_SS_ON)
            self._show_result(f"Sending every {interval_ms} ms…", ok=True)
            logger.info(f"[CAN TOOLS] Continuous send started: {interval_ms} ms")

    def _read_interval_ms(self) -> int | None:
        """
        Read and validate the interval input field.

        Returns:
            Interval in ms (10–60000) if valid.
            None if invalid — shows an error message to the user.
        """
        text = self._interval_edit.text().strip()
        try:
            ms = int(text)
        except ValueError:
            self._show_result("Interval must be a number (10–60000 ms)", ok=False)
            logger.warning(f"[CAN TOOLS] Invalid interval input: '{text}'")
            return None
        if not 10 <= ms <= 60_000:
            self._show_result("Interval must be 10–60000 ms", ok=False)
            logger.warning(f"[CAN TOOLS] Interval out of range: {ms} ms")
            return None
        return ms

    def _on_interval_changed(self, text: str) -> None:
        """Update the running timer immediately when the user edits the interval."""
        if not self._cont_timer.isActive():
            return
        interval_ms = self._read_interval_ms()
        if interval_ms is None:
            return   # keep current timer, error shown by _read_interval_ms
        self._cont_timer.setInterval(interval_ms)
        self._show_result(f"Sending every {interval_ms} ms…", ok=True)
        logger.info(f"[CAN TOOLS] Continuous interval changed to {interval_ms} ms")

    def _on_continuous_tick(self) -> None:
        """Fire one send cycle from the continuous timer."""
        self._on_send(from_timer=True)

    # ── Connection state ──────────────────────────────────────────

    def set_connection(self, node_id: str, connected: bool) -> None:
        """
        Called by MainWindow when a CAN channel connects or disconnects.
        Updates the connection dot if the affected channel is currently selected.
        """
        self._channel_states[node_id] = connected
        if (self._selected_channel is not None
                and self._selected_channel.node_id == node_id):
            self._set_conn_dot(connected)
            logger.debug(
                f"[CAN TOOLS] Channel {node_id} "
                f"{'connected' if connected else 'disconnected'} — dot updated"
            )

    def _set_conn_dot(self, connected: bool) -> None:
        """Set the connection dot: green = connected, red = disconnected."""
        color = t.GREEN if connected else t.RED
        self._conn_dot_lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; background: transparent;"
        )

    # ── Pill menu factory + three selectors ───────────────────────

    @staticmethod
    def _make_pill_menu(parent: QWidget) -> "QMenu":
        """
        Create a styled QMenu that drops below a MonChBtn pill.
        Identical style to CanMonitorWidget._show_channel_menu — reuses the
        same dark-bg + yellow-border + yellow-hover pattern from the CAN page.
        """
        from PySide6.QtWidgets import QMenu
        menu = QMenu(parent)
        menu.setStyleSheet("""
            QMenu {
                background-color: #111111;
                border: 1px solid #FFD100;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                color: #F5F5F5;
                padding: 6px 20px 6px 12px;
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
        return menu

    def _show_channel_pill_menu(self) -> None:
        """Open the channel selector menu below the channel pill button."""
        menu = self._make_pill_menu(self._ch_btn)
        for ch in self._can_channels:
            action = menu.addAction(f"{ch.name}  —  {ch.bitrate_label}")
            action.setData(ch)
            action.setCheckable(True)
            action.setChecked(ch is self._selected_channel)

        pos = self._ch_btn.mapToGlobal(self._ch_btn.rect().bottomLeft())
        chosen = menu.exec(pos)
        if chosen is None:
            return
        self._selected_channel = chosen.data()
        self._ch_btn.setText(
            f"{self._selected_channel.name}  —  {self._selected_channel.bitrate_label}  ▼"
        )
        connected = self._channel_states.get(self._selected_channel.node_id, False)
        self._set_conn_dot(connected)
        logger.debug(f"[CAN TOOLS] Channel selected: {self._selected_channel.node_id}")

    def _show_dlc_pill_menu(self) -> None:
        """
        Open the DLC selector menu below the DLC pill button.

        Two groups with a separator:
          Classical CAN / J1939  — 0 to 8 bytes (all valid, linear)
          CAN FD only            — 12, 16, 20, 24, 32, 48, 64 bytes
                                   (non-linear, ISO 11898-1:2015)
        """
        from PySide6.QtWidgets import QMenu

        menu = self._make_pill_menu(self._dlc_btn)

        # Group 1: Classical CAN / J1939 (0–8)
        hdr1 = menu.addAction("── Classical CAN / J1939 ──")
        hdr1.setEnabled(False)
        for dlc_val in (0, 1, 2, 3, 4, 5, 6, 7, 8):
            action = menu.addAction(f"  {dlc_val}")
            action.setData(dlc_val)
            action.setCheckable(True)
            action.setChecked(dlc_val == self._selected_dlc_val)

        menu.addSeparator()

        # Group 2: CAN FD only (12, 16, 20, 24, 32, 48, 64)
        hdr2 = menu.addAction("── CAN FD only ──")
        hdr2.setEnabled(False)
        for dlc_val in (12, 16, 20, 24, 32, 48, 64):
            action = menu.addAction(f"  {dlc_val}")
            action.setData(dlc_val)
            action.setCheckable(True)
            action.setChecked(dlc_val == self._selected_dlc_val)

        pos = self._dlc_btn.mapToGlobal(self._dlc_btn.rect().bottomLeft())
        chosen = menu.exec(pos)
        if chosen is None or chosen.data() is None:
            return

        new_dlc = chosen.data()
        old_dlc = self._selected_dlc_val
        self._selected_dlc_val = new_dlc
        self._dlc_btn.setText(f"{new_dlc}  ▼")

        # Sync the data field to the new DLC:
        #   - If new DLC < current token count → trim excess bytes
        #   - If new DLC > current token count → pad with zeros
        self._sync_data_to_dlc(old_dlc, new_dlc)

        logger.debug(f"[CAN TOOLS] DLC selected: {new_dlc}")

    def _on_browse(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        from simulator.can.can_file_reader import supported_file_filter

        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Open CAN File",
            "",
            supported_file_filter(),
        )
        if not path_str:
            return   # user cancelled
        self._load_file(Path(path_str))

    def _on_clear(self) -> None:
        self._file_label.setText("No file loaded")
        self._file_status.setText("")
        self._file_status.setStyleSheet(
            f"font-size: 10px; background: transparent; color: {t.TEXT_DIM};"
        )
        self._browser_table.setRowCount(0)
        self._signal_table.setRowCount(0)
        self._loaded_defs = []
        logger.debug("[CAN TOOLS] File cleared")

    def _load_file(self, path: Path) -> None:
        """Parse file and populate the browser table. Runs on the main thread."""
        self._file_label.setText(path.name)
        self._file_status.setText("Loading…")
        self._file_status.setStyleSheet(
            f"font-size: 10px; background: transparent; color: {t.YELLOW};"
        )
        self._browser_table.setRowCount(0)
        self._signal_table.setRowCount(0)
        self._loaded_defs = []

        try:
            from simulator.can.can_file_reader import auto_read_can_file
            msg_defs, log_frames = auto_read_can_file(path)
        except Exception as ex:
            self._show_file_error(str(ex))
            logger.warning(f"[CAN TOOLS] File load failed: {ex}")
            return

        if msg_defs:
            self._populate_db_table(msg_defs)
        elif log_frames:
            self._populate_log_table(log_frames)

    def _show_file_error(self, msg: str) -> None:
        self._file_status.setText(msg)
        self._file_status.setStyleSheet(
            f"font-size: 10px; background: transparent; color: {t.RED};"
        )

    # ── Browser table population ──────────────────────────────────

    def _browser_cell(self, text: str, color: str | None = None) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        if color:
            item.setForeground(QColor(color))
        return item

    def _populate_db_table(self, defs: list) -> None:
        """Show message definitions (from a DB file)."""
        self._loaded_defs = defs
        self._browser_table.setHorizontalHeaderLabels(
            ["ARB ID", "MESSAGE NAME", "DLC", "TYPE"]
        )
        self._browser_table.setRowCount(0)

        for msg in defs:
            row = self._browser_table.rowCount()
            self._browser_table.insertRow(row)
            self._browser_table.setItem(row, 0, self._browser_cell(msg.arb_id_str, t.YELLOW))
            self._browser_table.setItem(row, 1, self._browser_cell(msg.name))
            self._browser_table.setItem(row, 2, self._browser_cell(str(msg.dlc)))
            self._browser_table.setItem(row, 3, self._browser_cell(
                msg.frame_type,
                "#FCD34D" if msg.is_extended else t.TEXT_BRIGHT,
            ))
            self._browser_table.setRowHeight(row, 22)

        n_sig = sum(len(m.signals) for m in defs)
        self._file_status.setText(
            f"{len(defs)} message{'s' if len(defs) != 1 else ''}  ·  "
            f"{n_sig} signal{'s' if n_sig != 1 else ''}"
        )
        self._file_status.setStyleSheet(
            f"font-size: 10px; background: transparent; color: {t.GREEN};"
        )
        logger.info(f"[CAN TOOLS] DB table populated: {len(defs)} messages")

    def _populate_log_table(self, frames: list) -> None:
        """Show recorded frames (from a log file)."""
        self._loaded_defs = []   # log files have no signal definitions
        self._browser_table.setHorizontalHeaderLabels(
            ["ARB ID", "DATA", "DLC", "TYPE"]
        )
        self._browser_table.setRowCount(0)

        for frm in frames:
            row = self._browser_table.rowCount()
            self._browser_table.insertRow(row)
            self._browser_table.setItem(row, 0, self._browser_cell(frm.arb_id_str, t.YELLOW))
            self._browser_table.setItem(row, 1, self._browser_cell(frm.data_str))
            self._browser_table.setItem(row, 2, self._browser_cell(str(frm.dlc)))
            type_color = "#FCD34D" if frm.is_extended else t.TEXT_BRIGHT
            self._browser_table.setItem(row, 3, self._browser_cell(frm.frame_type, type_color))
            self._browser_table.setRowHeight(row, 22)

        truncated = f"  (first {len(frames):,})" if len(frames) >= 10_000 else ""
        self._file_status.setText(
            f"{len(frames):,} frame{'s' if len(frames) != 1 else ''}{truncated}"
        )
        self._file_status.setStyleSheet(
            f"font-size: 10px; background: transparent; color: {t.GREEN};"
        )
        logger.info(f"[CAN TOOLS] Log table populated: {len(frames):,} frames")

    # ── Browser row selection → auto-fill send panel ──────────────

    def _read_browser_row(self, row_index: int) -> dict:
        """
        Read all fields from one browser table row into a plain dict.

        Returns:
            {arb_id_text, data_text, dlc, is_extended}
        Caller handles None / empty gracefully.
        """
        arb_id_item = self._browser_table.item(row_index, 0)
        data_item   = self._browser_table.item(row_index, 1)
        dlc_item    = self._browser_table.item(row_index, 2)
        type_item   = self._browser_table.item(row_index, 3)

        arb_id_text = arb_id_item.text() if arb_id_item else ""
        data_text   = data_item.text()   if data_item   else ""

        try:
            dlc = int(dlc_item.text()) if dlc_item else 8
        except ValueError:
            dlc = 8

        is_extended = (type_item.text() == "EXT") if type_item else False

        return {
            "arb_id_text": arb_id_text,
            "data_text":   data_text,
            "dlc":         dlc,
            "is_extended": is_extended,
        }

    def _on_browser_selection(self) -> None:
        """Auto-fill the send panel when the user clicks a browser row."""
        if not self._browser_table.selectedItems():
            return

        sel_row = self._browser_table.currentRow()
        if sel_row < 0:
            return

        row = self._read_browser_row(sel_row)
        if not row["arb_id_text"]:
            return

        # Arb ID
        self._arb_id_edit.setText(row["arb_id_text"])

        if self._loaded_defs:
            # ── DB file row ───────────────────────────────────────
            # Column 1 is the message NAME, not data bytes.
            # Fill the data field with DLC zeros from the message definition.
            # Derive is_extended directly from the arb ID — more reliable than
            # the TYPE column string, which can differ between cantools versions.
            try:
                arb_id_int = int(row["arb_id_text"], 16)
            except ValueError:
                arb_id_int = 0

            msg_def = next(
                (m for m in self._loaded_defs if m.arb_id == arb_id_int),
                None,
            )

            dlc = msg_def.dlc if msg_def else row["dlc"]
            self._data_edit.setText(" ".join("00" for _ in range(max(0, dlc))))

            # is_extended: trust the message definition object, not the table string
            is_extended = msg_def.is_extended if msg_def else (arb_id_int > 0x7FF)

            # Populate signal sub-table
            self._populate_signal_table(msg_def)

        else:
            # ── Log file row ──────────────────────────────────────
            # Column 1 is the actual recorded data bytes.
            if row["data_text"] and row["data_text"].strip() not in ("", "—"):
                self._data_edit.setText(row["data_text"].strip())
            else:
                self._data_edit.setText(
                    " ".join("00" for _ in range(max(0, row["dlc"])))
                )
            is_extended = row["is_extended"]
            self._signal_table.setRowCount(0)

        # Frame type radio button:
        #   arb_id > 0x7FF → J1939 (29-bit, radio id=2)
        #   arb_id ≤ 0x7FF → Standard (11-bit, radio id=0)
        #   Extended (radio id=1) is for manual selection only — not auto-set.
        try:
            arb_id_for_radio = int(row["arb_id_text"], 16)
        except ValueError:
            arb_id_for_radio = 0
        radio_id   = 2 if arb_id_for_radio > 0x7FF else 0
        radio_name = {0: "Standard", 2: "J1939"}.get(radio_id, "Standard")
        frame_btn  = self._type_grp.button(radio_id)
        if frame_btn:
            frame_btn.setChecked(True)

        logger.debug(
            f"[CAN TOOLS] Row selected: arb_id={row['arb_id_text']} "
            f"frame_type={radio_name} extended={is_extended if self._loaded_defs else row['is_extended']}"
        )

    def _populate_signal_table(self, msg_def) -> None:
        """Fill the signal sub-table for a selected message definition."""
        self._signal_table.setRowCount(0)
        if msg_def is None or not msg_def.signals:
            return

        for sig in msg_def.signals:
            row = self._signal_table.rowCount()
            self._signal_table.insertRow(row)

            # Bit range string e.g. "0+8"
            bit_str = f"{sig.start_bit}+{sig.length}"
            factor_str = f"{sig.factor:g}" if sig.factor != 1.0 else "1"
            offset_str = f"{sig.offset:g}" if sig.offset != 0.0 else "0"

            self._signal_table.setItem(row, 0, self._browser_cell(sig.name))
            self._signal_table.setItem(row, 1, self._browser_cell(bit_str, t.TEXT_DIM))
            self._signal_table.setItem(row, 2, self._browser_cell(factor_str))
            self._signal_table.setItem(row, 3, self._browser_cell(offset_str))
            self._signal_table.setItem(row, 4, self._browser_cell(sig.unit))
            self._signal_table.setRowHeight(row, 20)

    # ── Send ──────────────────────────────────────────────────────

    def _validate_send_fields(self) -> tuple | None:
        """
        Validate ARB ID and data bytes from the send panel.

        Returns:
            (arb_id: int, data_bytes: bytes, is_extended: bool) on success.
            None if any field is invalid — shows error via _show_result.
        """
        # Arb ID
        arb_id_text = self._arb_id_edit.text().strip()
        if not arb_id_text:
            self._show_result("Arb ID is empty", ok=False)
            return None
        try:
            arb_id = int(arb_id_text, 16)
        except ValueError:
            self._show_result(f"Invalid arb ID: '{arb_id_text}'", ok=False)
            return None

        # Data bytes
        data_text = self._data_edit.text().strip()
        try:
            data_bytes = self._parse_data_bytes(data_text) if data_text else b""
        except ValueError as ex:
            self._show_result(f"Data error: {ex}", ok=False)
            return None

        if len(data_bytes) > 64:
            self._show_result("Data exceeds 64-byte CAN-FD maximum", ok=False)
            return None

        # Frame type (Extended or J1939 → 29-bit ID)
        is_extended = self._type_grp.checkedId() in (1, 2)

        return arb_id, data_bytes, is_extended

    def _transmit_can_frame(
        self,
        ch_data,
        arb_id: int,
        data_bytes: bytes,
        is_extended: bool,
    ) -> tuple[bool, str]:
        """
        Open a one-shot CAN bus, send the frame, close the bus.

        Returns:
            (success: bool, message: str)
        """
        try:
            import can as _can_mod
        except ImportError:
            return False, "python-can not installed"

        can_msg = _can_mod.Message(
            arbitration_id = arb_id,
            is_extended_id = is_extended,
            data           = data_bytes,
            is_fd          = False,
        )
        try:
            bus = _can_mod.Bus(
                interface = self._profile.can_backend.value,
                channel   = ch_data.node_id,
                bitrate   = ch_data.bitrate if ch_data.bitrate > 0 else 250_000,
            )
            try:
                bus.send(can_msg, timeout=1.0)
            finally:
                bus.shutdown()

            id_str = f"0x{arb_id:X}"
            msg    = f" Sent {id_str} on {ch_data.name}"
            logger.info(
                f"[CAN TOOLS] Sent: id={id_str} "
                f"data={data_bytes.hex(' ')} "
                f"ch={ch_data.name}"
            )
            return True, msg

        except Exception as ex:
            logger.warning(f"[CAN TOOLS] Send failed: {ex}")
            return False, f"✕ {ex}"

    def _on_send(self, from_timer: bool = False) -> None:
        """
        Validate fields and send one CAN frame.

        from_timer: True when called by the continuous timer.
            On success — updates status label without auto-clear.
            On failure — stops the continuous timer then shows the error.
        """
        if self._selected_channel is None:
            self._show_result("No CAN channel selected", ok=False)
            return

        fields = self._validate_send_fields()
        if fields is None:
            return   # _validate_send_fields already showed the error

        arb_id, data_bytes, is_extended = fields
        ok, msg = self._transmit_can_frame(
            self._selected_channel, arb_id, data_bytes, is_extended
        )

        if from_timer and not ok:
            # Stop continuous mode on any transmission error
            self._toggle_continuous()

        if from_timer and ok:
            # During continuous mode update without auto-clear
            self._send_result.setText(msg)
            self._send_result.setStyleSheet(
                f"color: {t.GREEN}; font-size: 10px; background: transparent;"
            )
        else:
            self._show_result(msg, ok=ok)

    def _show_result(self, text: str, ok: bool) -> None:
        color = t.GREEN if ok else t.RED
        self._send_result.setText(text)
        self._send_result.setStyleSheet(
            f"color: {color}; font-size: 10px; background: transparent;"
        )
        QTimer.singleShot(4000, lambda: self._send_result.setText(""))



# NodePill imported from simulator.gui.components
# — see components.py for the full implementation


