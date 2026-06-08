from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.components import NodePill, RedSepV
from simulator.gui.constants import SIDEBAR_WIDTH
from simulator.platform.can_detector import CanChannel
from simulator.gui._version import APP_VERSION
from simulator.gui.widgets.top_header import FlowLayout


class FooterBar(QWidget):
    """
    E — Full-width footer.

    Left  : [● v2.0.5] pill — fixed sidebar width.
    Right : pills bottom-aligned when window is maximised.
            On resize/narrow → FlowLayout wraps to extra rows (footer grows).

    All pills: PILL_H tall, width auto-fits label text.
    """
    PILL_H    = 28   # uniform pill height
    FOOTER_H  = 52   # comfortable single-row height (maximised)

    def __init__(
        self,
        platform_label: str,
        can_channels:   list[CanChannel],
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("FooterBar")
        self.setMinimumHeight(self.FOOTER_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._pills: dict[str, NodePill] = {}

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Left: version pill ────────────────────────────────────
        left = QWidget()
        left.setObjectName("FooterLeft")
        left.setFixedWidth(SIDEBAR_WIDTH)

        left_vbox = QVBoxLayout(left)
        left_vbox.setContentsMargins(8, 6, 8, 6)
        left_vbox.setSpacing(0)
        left_vbox.addStretch()          # push pill to bottom of left column

        ver_pill = QWidget()
        ver_pill.setObjectName("VersionPill")
        ver_pill.setAttribute(Qt.WA_StyledBackground, True)
        ver_pill.setFixedHeight(self.PILL_H)
        ver_pill.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ver_pill.setStyleSheet("""
            QWidget#VersionPill {
                background-color: #1C1C1C;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
            }
        """)
        vp_row = QHBoxLayout(ver_pill)
        vp_row.setContentsMargins(8, 0, 10, 0)
        vp_row.setSpacing(5)
        vp_row.setAlignment(Qt.AlignCenter)

        ver_dot = QLabel("●")
        ver_dot.setStyleSheet("color:#FFD100; font-size:6px; background:transparent;")
        vp_row.addWidget(ver_dot, 0, Qt.AlignVCenter)

        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setObjectName("VersionLabel")
        ver_lbl.setAlignment(Qt.AlignCenter)
        vp_row.addWidget(ver_lbl, 0, Qt.AlignVCenter)

        left_vbox.addWidget(ver_pill)
        outer.addWidget(left)
        outer.addWidget(RedSepV())

        # ── Right: stretch above + flow strip at bottom ───────────
        right = QWidget()
        right.setObjectName("FooterRight")
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        right.setAttribute(Qt.WA_StyledBackground, True)
        right.setStyleSheet("QWidget#FooterRight { background: transparent; }")

        right_vbox = QVBoxLayout(right)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)
        right_vbox.addStretch()         # push pill row to bottom

        # The flow container — FlowLayout wraps pills here
        flow_container = QWidget()
        flow_container.setObjectName("PillFlow")
        flow_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        flow_container.setAttribute(Qt.WA_StyledBackground, True)
        flow_container.setStyleSheet("QWidget#PillFlow { background: transparent; }")

        flow = FlowLayout(flow_container, h_spacing=4, v_spacing=4)
        flow.setContentsMargins(12, 0, 12, 8)   # 8px bottom padding

        # ── Separator ─────────────────────────────────────────────
        def _sep() -> QLabel:
            s = QLabel("|")
            s.setFixedSize(16, self.PILL_H)
            s.setAlignment(Qt.AlignCenter)
            s.setStyleSheet(
                "color:#686868; font-size:14px; font-weight:100; background:transparent;"
            )
            return s

        # ── OS platform pill ──────────────────────────────────────
        os_pill = QWidget()
        os_pill.setObjectName("OsPill")
        os_pill.setAttribute(Qt.WA_StyledBackground, True)
        os_pill.setFixedHeight(self.PILL_H)
        os_pill.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        os_pill.setStyleSheet("""
            QWidget#OsPill {
                background-color: #1C1C1C;
                border: 1px solid #2A2A2A;
                border-radius: 6px;
            }
        """)
        osp_row = QHBoxLayout(os_pill)
        osp_row.setContentsMargins(9, 0, 11, 0)
        osp_row.setSpacing(5)

        os_dot = QLabel("●")
        os_dot.setAlignment(Qt.AlignVCenter)
        os_dot.setStyleSheet("color:#FFD100; font-size:7px; background:transparent;")
        osp_row.addWidget(os_dot, 0, Qt.AlignVCenter)

        os_lbl = QLabel(platform_label)
        os_lbl.setObjectName("FooterPlatform")
        os_lbl.setAlignment(Qt.AlignVCenter)
        os_lbl.setStyleSheet(
            "color:#F5F5F5; font-size:9px; letter-spacing:0.5px; background:transparent;"
        )
        osp_row.addWidget(os_lbl, 0, Qt.AlignVCenter)

        flow.addWidget(os_pill)

        # ── CAN channels ──────────────────────────────────────────
        flow.addWidget(_sep())
        if can_channels:
            for i, ch in enumerate(can_channels):
                pill = NodePill(ch.node_id, ch.name, sub=ch.bitrate_label)
                pill.setFixedHeight(self.PILL_H)
                flow.addWidget(pill)
                self._pills[ch.node_id] = pill
                if i < len(can_channels) - 1:
                    flow.addWidget(_sep())
        else:
            p = NodePill("can_none", "NO CAN")
            p.setFixedHeight(self.PILL_H)
            flow.addWidget(p)

        # ── Fixed nodes in importance order ───────────────────────
        for node_id, label in [
            ("lucid_aovo",   "LUCID AOVO"),
            ("lucid_aivo",   "LUCID AIVO"),
            ("gw",           "GW"),
            ("hmi",          "HMI"),
            ("truck_ctrl",   "TRUCK CONTROLLER"),
            ("trailer_ctrl", "TRAILER CONTROLLER"),
            ("joystick",     "JOYSTICK"),
            ("rpc",          "RPC"),
        ]:
            flow.addWidget(_sep())
            pill = NodePill(node_id, label)
            pill.setFixedHeight(self.PILL_H)
            flow.addWidget(pill)
            self._pills[node_id] = pill

        right_vbox.addWidget(flow_container)
        outer.addWidget(right)

    # ── Public API ────────────────────────────────────────────────

    def set_connection(self, node_id: str, connected: bool) -> None:
        if node_id in self._pills:
            self._pills[node_id].set_connected(connected)

    def set_node_state(self, node_id: str, state: str) -> None:
        if node_id in self._pills:
            self._pills[node_id].set_node_state(state)

    def update_baudrate(self, node_id: str, bitrate_label: str) -> None:
        if node_id in self._pills:
            self._pills[node_id].update_sub(bitrate_label)
        else:
            logger.warning(f"[FOOTER] No pill found for {node_id!r} — cannot update baudrate")
