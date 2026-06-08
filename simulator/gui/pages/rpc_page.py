from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
)
from PySide6.QtCore import Qt, QTimer
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.components import PageTitleBar


class RpcPage(QWidget):
    """
    RPC Server status page — shows server address, live connection count,
    and a ring-buffer call log that refreshes every 500 ms.
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._server = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)
        root.addWidget(PageTitleBar("RPC"))

        # ── Status card ──────────────────────────────────────────
        status_card = QWidget()
        status_card.setObjectName("StatusCard")
        status_card.setStyleSheet(f"""
            QWidget#StatusCard {{
                background-color: {t.BG_CARD};
                border: 1px solid {t.BORDER_FAINT};
                border-radius: 6px;
            }}
        """)
        sc_lay = QGridLayout(status_card)
        sc_lay.setContentsMargins(16, 12, 16, 12)
        sc_lay.setHorizontalSpacing(24)
        sc_lay.setVerticalSpacing(6)

        lbl_style  = f"color:{t.TEXT_DIM};  font-size:10px;"
        val_style  = f"color:{t.TEXT_BRIGHT}; font-size:13px; font-weight:600;"
        addr_style = f"color:{t.YELLOW};    font-size:13px; font-family:monospace;"

        for col, (lbl_text, val_attr) in enumerate([
            ("ADDRESS",     "_lbl_addr"),
            ("STATUS",      "_lbl_status"),
            ("CLIENTS",     "_lbl_clients"),
        ]):
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet(lbl_style)
            val = QLabel("—")
            val.setStyleSheet(addr_style if col == 0 else val_style)
            sc_lay.addWidget(lbl, 0, col)
            sc_lay.addWidget(val, 1, col)
            setattr(self, val_attr, val)

        root.addWidget(status_card)

        # ── Call log header row: label + Clear button ────────────
        log_hdr_row = QHBoxLayout()
        log_hdr_row.setContentsMargins(0, 4, 0, 0)
        log_hdr_row.setSpacing(8)

        log_header = QLabel("CALL LOG  (last 100 calls)")
        log_header.setStyleSheet(
            f"color:{t.TEXT_DIM}; font-size:10px;"
        )
        log_hdr_row.addWidget(log_header)
        log_hdr_row.addStretch()

        self._btn_clear_log = QPushButton("⌫  CLEAR")
        self._btn_clear_log.setObjectName("ClearLogBtn")
        self._btn_clear_log.setCursor(Qt.PointingHandCursor)
        self._btn_clear_log.setFixedHeight(22)
        self._btn_clear_log.setStyleSheet(f"""
            QPushButton#ClearLogBtn {{
                background-color: {t.BG_SURFACE};
                color: {t.TEXT_DIM};
                border: 1px solid {t.BORDER_FAINT};
                border-radius: 4px;
                font-size: 9px;
                padding: 0 10px;
            }}
            QPushButton#ClearLogBtn:hover {{
                background-color: #3A1A1A;
                color: {t.RED};
                border-color: {t.RED};
            }}
            QPushButton#ClearLogBtn:pressed {{
                background-color: #4A2020;
            }}
        """)
        self._btn_clear_log.clicked.connect(self._clear_log)
        log_hdr_row.addWidget(self._btn_clear_log)

        log_hdr_w = QWidget()
        log_hdr_w.setLayout(log_hdr_row)
        root.addWidget(log_hdr_w)

        self._log_table = QTableWidget(0, 4)
        self._log_table.setHorizontalHeaderLabels(["TIME", "FUNCTION", "ARGS", "RESULT"])
        self._log_table.horizontalHeader().setStretchLastSection(True)
        self._log_table.horizontalHeader().setStyleSheet(
            f"color:{t.TEXT_DIM}; font-size:10px;"
        )
        self._log_table.verticalHeader().setVisible(False)
        self._log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._log_table.setAlternatingRowColors(True)
        self._log_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {t.BG_CARD};
                color: {t.TEXT_BRIGHT};
                gridline-color: {t.BORDER_FAINT};
                font-size: 11px;
                border: 1px solid {t.BORDER_FAINT};
                border-radius: 4px;
            }}
            QTableWidget::item:alternate {{
                background-color: {t.BG_SURFACE};
            }}
        """)
        self._log_table.setColumnWidth(0, 72)
        self._log_table.setColumnWidth(1, 180)
        self._log_table.setColumnWidth(2, 180)
        root.addWidget(self._log_table)

        # ── Install/missing rpyc hint ─────────────────────────────
        self._hint = QLabel(
            "ℹ  rpyc not installed — run:  pip install rpyc>=6.0.0"
        )
        self._hint.setStyleSheet(
            f"color:{t.TEXT_DIM}; font-size:10px; font-style:italic;"
        )
        self._hint.setVisible(False)
        root.addWidget(self._hint)

        # ── Refresh timer ─────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._refresh)

        # Local clear flag — when user clears we freeze display until
        # new entries arrive, preventing immediate re-population.
        self._cleared_at_count: int = -1

    # ── Public API ────────────────────────────────────────────────

    def set_rpc_server(self, server: "RpcServer | None") -> None:
        """
        Called from MainWindow._init_subsystems() once the RpcServer is started.
        Pass None if rpyc is unavailable.
        """
        self._server = server
        if server is None:
            self._lbl_addr.setText("unavailable")
            self._lbl_status.setText("rpyc not installed")
            self._lbl_status.setStyleSheet(f"color:{t.RED}; font-size:13px;")
            self._hint.setVisible(True)
            self._btn_clear_log.setEnabled(False)
            logger.warning("[RPC] Page: server not available")
        else:
            self._lbl_addr.setText(server.address)
            self._timer.start()
            self._refresh()
            logger.info(f"[RPC] Page: monitoring {server.address}")

    # ── Private ───────────────────────────────────────────────────

    def _clear_log(self) -> None:
        """Clear the visual table and record how many server entries exist now.
        New entries arriving after this point will be shown normally."""
        self._log_table.setRowCount(0)
        if self._server is not None:
            # Record current ring-buffer size so _refresh knows where
            # "cleared" ends and new entries begin.
            self._cleared_at_count = len(self._server.get_call_log())
        logger.debug("[RPC] Call log cleared by user")

    def _refresh(self) -> None:
        """Update status labels and call-log table from the server's ring buffer."""
        if self._server is None:
            return

        # ── Status row ────────────────────────────────────────────
        if self._server.is_running:
            self._lbl_status.setText("● LISTENING")
            self._lbl_status.setStyleSheet(
                f"color:{t.GREEN}; font-size:13px; font-weight:600;"
            )
        else:
            self._lbl_status.setText("○ stopped")
            self._lbl_status.setStyleSheet(
                f"color:{t.RED}; font-size:13px;"
            )
        self._lbl_clients.setText(str(self._server.get_conn_count()))

        # ── Call log ──────────────────────────────────────────────
        entries = self._server.get_call_log()

        # After a user clear: only show entries that arrived afterwards.
        # _cleared_at_count is the ring-buffer length at the moment of clear.
        # New entries are prepended (newest first), so show only the first
        # (len - cleared_at_count) entries if that is positive.
        if self._cleared_at_count >= 0:
            new_count = len(entries) - self._cleared_at_count
            if new_count <= 0:
                # Nothing new yet — table stays empty.
                return
            entries = entries[:new_count]

        # Skip repopulate if nothing has changed.
        if self._log_table.rowCount() == len(entries):
            return

        self._log_table.setRowCount(0)
        for entry in entries:
            row = self._log_table.rowCount()
            self._log_table.insertRow(row)
            for col, key in enumerate(("time", "func", "args", "result")):
                item = QTableWidgetItem(str(entry.get(key, "")))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self._log_table.setItem(row, col, item)
            self._log_table.setRowHeight(row, 22)


