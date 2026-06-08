from __future__ import annotations

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QAbstractItemView, QSlider, QFileDialog,
)
from PySide6.QtCore import Qt
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.icons import IconWidget
from simulator.gui.components import (
    PageTitleBar, RedSepH,
    ActionButton, DangerButton, SuccessButton,
    SectionLabel, ValueLabel, Card,
)


class PlaybackPage(QWidget):
    """
    Page 3 — CSV scenario playback.

    Layout:
      ┌─────────────────────────────────────────────────────────┐
      │  FILE ──────────────────────────────────────── [Browse] │
      │  [Load]  ▸ 3 sensors · 1200 rows · 120.0 s              │
      ├─────────────────────────────────────────────────────────┤
      │  Column mapping  ● lateral  ● longitudinal  ● pressure  │
      ├─────────────────────────────────────────────────────────┤
      │  ◀◀  ▶ PLAY  ⏸ PAUSE  ■ STOP   Speed: [1× ▼]           │
      │  ──────────────────●─────────────────────────────────── │
      │  00:12.4 / 02:00.0          Row 744 / 1200              │
      └─────────────────────────────────────────────────────────┘

    Wired to OBU bridge via set_obu_bridge():
      player.sensor_values → bridge per-sensor set_sensor_target calls
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        from simulator.playback.csv_player import CsvPlayer, SPEED_OPTIONS, _SENSOR_META

        self._player: CsvPlayer    = CsvPlayer()
        self._info                 = None
        self._bridge               = None
        self._total_rows: int      = 0
        self._duration_s: float    = 0.0
        self._is_playing: bool     = False

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)
        root.addWidget(PageTitleBar("PLAYBACK"))

        CARD_SS = """
            QWidget#PlaybackCard {
                background-color: #1A1A1A;
                border: 1px solid #2A2A2A;
                border-top: 2px solid #3A3A3A;
                border-radius: 8px;
            }
        """

        # ── Card 1: file picker ───────────────────────────────────
        file_card = QWidget()
        file_card.setObjectName("PlaybackCard")
        file_card.setAttribute(Qt.WA_StyledBackground, True)
        file_card.setStyleSheet(CARD_SS)
        fc_lay = QVBoxLayout(file_card)
        fc_lay.setContentsMargins(16, 12, 16, 14)
        fc_lay.setSpacing(8)

        # Header
        fhdr = QHBoxLayout()
        fhdr.setSpacing(8)
        fhdr.addWidget(IconWidget(fa="fa6s.file-csv", fallback="▤", colour="#FFD100", size=13))
        fhdr_lbl = QLabel("SCENARIO FILE")
        fhdr_lbl.setStyleSheet(
            "color:#FFD100; font-size:11px; letter-spacing:2px; font-weight:bold;"
        )
        fhdr.addWidget(fhdr_lbl)
        fhdr.addStretch()
        fc_lay.addLayout(fhdr)

        # Path row
        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self._path_inp = QLineEdit()
        self._path_inp.setPlaceholderText("Path to .csv file…")
        self._path_inp.setStyleSheet("""
            QLineEdit {
                background:#111111; color:#AAAAAA;
                border:1px solid #2A2A2A; border-radius:3px;
                padding:4px 8px; font-size:12px;
                font-family:'Liberation Mono','DejaVu Sans Mono',Consolas,monospace;
            }
            QLineEdit:focus { border:1px solid #555555; color:#E0E0E0; }
        """)
        path_row.addWidget(self._path_inp, 1)

        BROWSE_SS = """
            QPushButton {
                background:#1E1E1E; color:#888888;
                border:1px solid #333333; border-radius:3px;
                font-size:11px; letter-spacing:1px; padding:4px 12px;
            }
            QPushButton:hover  { background:#252525; color:#E0E0E0; border-color:#555555; }
            QPushButton:pressed{ background:#1A1A1A; }
        """
        btn_browse = QPushButton("BROWSE")
        btn_browse.setStyleSheet(BROWSE_SS)
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self._on_browse)
        path_row.addWidget(btn_browse)
        fc_lay.addLayout(path_row)

        # Load row
        load_row = QHBoxLayout()
        load_row.setSpacing(10)

        LOAD_SS = """
            QPushButton {
                background:#0A2A18; color:#22C55E;
                border:1px solid #1A5030; border-radius:3px;
                font-size:11px; letter-spacing:1px; padding:4px 16px; font-weight:bold;
            }
            QPushButton:hover  { background:#0F3A22; border-color:#22C55E; }
            QPushButton:pressed{ background:#071A10; }
            QPushButton:disabled{ background:#111111; color:#333333; border-color:#222222; }
        """
        self._btn_load = QPushButton("LOAD")
        self._btn_load.setStyleSheet(LOAD_SS)
        self._btn_load.setCursor(Qt.PointingHandCursor)
        self._btn_load.clicked.connect(self._on_load)
        load_row.addWidget(self._btn_load)

        self._file_status = QLabel("No file loaded")
        self._file_status.setStyleSheet("color:#555555; font-size:11px;")
        load_row.addWidget(self._file_status)
        load_row.addStretch()
        fc_lay.addLayout(load_row)
        root.addWidget(file_card)

        # ── Card 2: column mapping ────────────────────────────────
        self._map_card = QWidget()
        self._map_card.setObjectName("PlaybackCard")
        self._map_card.setAttribute(Qt.WA_StyledBackground, True)
        self._map_card.setStyleSheet(CARD_SS)
        self._map_card.setVisible(False)
        mc_lay = QVBoxLayout(self._map_card)
        mc_lay.setContentsMargins(16, 12, 16, 14)
        mc_lay.setSpacing(8)

        mhdr = QHBoxLayout()
        mhdr.setSpacing(8)
        mhdr.addWidget(IconWidget(fa="fa6s.table-columns", fallback="≡", colour="#4DB8D4", size=12))
        mhdr_lbl = QLabel("COLUMN MAP")
        mhdr_lbl.setStyleSheet(
            "color:#4DB8D4; font-size:11px; letter-spacing:2px; font-weight:bold;"
        )
        mhdr.addWidget(mhdr_lbl)
        mhdr.addStretch()
        mc_lay.addLayout(mhdr)

        self._col_map_row = QHBoxLayout()
        self._col_map_row.setSpacing(12)
        mc_lay.addLayout(self._col_map_row)
        root.addWidget(self._map_card)

        # ── Card 3: transport + scrubber ──────────────────────────
        self._transport_card = QWidget()
        self._transport_card.setObjectName("PlaybackCard")
        self._transport_card.setAttribute(Qt.WA_StyledBackground, True)
        self._transport_card.setStyleSheet(CARD_SS)
        self._transport_card.setVisible(False)
        tc_lay = QVBoxLayout(self._transport_card)
        tc_lay.setContentsMargins(16, 12, 16, 14)
        tc_lay.setSpacing(10)

        # Transport buttons row
        tb_row = QHBoxLayout()
        tb_row.setSpacing(6)

        BTN_SS = """
            QPushButton {
                background:#1E1E1E; color:#888888;
                border:1px solid #2A2A2A; border-radius:3px;
                font-size:13px; padding:4px 12px;
            }
            QPushButton:hover   { background:#162030; color:#4DB8D4; border-color:#1A5060; }
            QPushButton:pressed { background:#0F1A28; color:#7AD4EC; }
            QPushButton:disabled{ background:#111111; color:#333333; border-color:#1A1A1A; }
        """
        PLAY_SS = """
            QPushButton {
                background:#0A2A18; color:#22C55E;
                border:1px solid #1A5030; border-radius:3px;
                font-size:13px; padding:4px 16px; font-weight:bold;
            }
            QPushButton:hover   { background:#0F3A22; border-color:#22C55E; }
            QPushButton:pressed { background:#071A10; }
            QPushButton:disabled{ background:#111111; color:#333333; border-color:#222222; }
        """
        STOP_SS = """
            QPushButton {
                background:#2A0A0A; color:#CC1020;
                border:1px solid #661010; border-radius:3px;
                font-size:13px; padding:4px 14px; font-weight:bold;
            }
            QPushButton:hover   { background:#3A0F0F; border-color:#CC1020; }
            QPushButton:pressed { background:#1A0808; }
            QPushButton:disabled{ background:#111111; color:#333333; border-color:#1A1A1A; }
        """

        self._btn_play  = QPushButton("▶  PLAY")
        self._btn_pause = QPushButton("⏸  PAUSE")
        self._btn_stop  = QPushButton("■  STOP")
        self._btn_play.setStyleSheet(PLAY_SS)
        self._btn_pause.setStyleSheet(BTN_SS)
        self._btn_stop.setStyleSheet(STOP_SS)
        for b in (self._btn_play, self._btn_pause, self._btn_stop):
            b.setCursor(Qt.PointingHandCursor)
            b.setEnabled(False)

        self._btn_play.clicked.connect(self._on_play)
        self._btn_pause.clicked.connect(self._on_pause)
        self._btn_stop.clicked.connect(self._on_stop)

        tb_row.addWidget(self._btn_play)
        tb_row.addWidget(self._btn_pause)
        tb_row.addWidget(self._btn_stop)
        tb_row.addStretch()

        # Speed selector
        spd_lbl = QLabel("SPEED")
        spd_lbl.setStyleSheet("color:#555555; font-size:10px; letter-spacing:1px;")
        tb_row.addWidget(spd_lbl)

        self._speed_combo = QComboBox()
        self._speed_combo.setStyleSheet("""
            QComboBox {
                background:#1A1A1A; color:#AAAAAA;
                border:1px solid #2A2A2A; border-radius:3px;
                padding:3px 8px; font-size:12px;
            }
            QComboBox:hover { border-color:#555555; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background:#1A1A1A; color:#AAAAAA;
                selection-background-color:#0F3A22;
                selection-color:#22C55E;
            }
        """)
        for spd in SPEED_OPTIONS:
            label = f"{spd:g}×"
            self._speed_combo.addItem(label, spd)
        self._speed_combo.setCurrentIndex(SPEED_OPTIONS.index(1.0))
        self._speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        tb_row.addWidget(self._speed_combo)
        tc_lay.addLayout(tb_row)

        # Scrubber
        self._scrubber = QSlider(Qt.Horizontal)
        self._scrubber.setRange(0, 1000)
        self._scrubber.setValue(0)
        self._scrubber.setEnabled(False)
        self._scrubber.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px; background: #0D0D0D;
                border: 1px solid #252525; border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #22C55E; border-radius: 2px;
            }
            QSlider::add-page:horizontal {
                background: #111111; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #E8E8E8; border: 1px solid #888888;
                width: 12px; height: 12px; margin: -5px 0; border-radius: 6px;
            }
            QSlider::handle:horizontal:hover { background: #FFFFFF; }
            QSlider::handle:horizontal:disabled { background: #333333; border-color:#222222; }
        """)
        self._scrubber.sliderMoved.connect(self._on_scrub)
        tc_lay.addWidget(self._scrubber)

        # Time + row progress
        prog_row = QHBoxLayout()
        self._time_lbl = QLabel("00:00.0 / 00:00.0")
        self._time_lbl.setStyleSheet(
            "color:#666666; font-size:11px;"
            " font-family:'Liberation Mono','DejaVu Sans Mono',Consolas,monospace;"
        )
        prog_row.addWidget(self._time_lbl)
        prog_row.addStretch()

        self._row_lbl = QLabel("Row 0 / 0")
        self._row_lbl.setStyleSheet(
            "color:#444444; font-size:11px;"
            " font-family:'Liberation Mono','DejaVu Sans Mono',Consolas,monospace;"
        )
        prog_row.addWidget(self._row_lbl)
        tc_lay.addLayout(prog_row)
        root.addWidget(self._transport_card)

        root.addStretch()

        # ── Player signals ────────────────────────────────────────
        self._player.row_changed.connect(self._on_row_changed)
        self._player.playback_finished.connect(self._on_finished)
        self._player.error_occurred.connect(self._on_player_error)

        self._set_transport_state("unloaded")

    # ── Public API ────────────────────────────────────────────────

    def set_obu_bridge(self, bridge: "ObuBridge | None") -> None:
        """Wire the bridge. Safe to call with bridge=None."""
        self._bridge = bridge
        if bridge is None:
            logger.warning("[PLAYBACK] set_obu_bridge: bridge=None — running disconnected")
            return
        # sensor_values emits dict[int, float]; bridge.set_sensor_target takes (sid, val)
        self._player.sensor_values.connect(self._dispatch_sensor_values)
        logger.info("[PLAYBACK] Bridge wired")

    # ── Private helpers ───────────────────────────────────────────

    def _dispatch_sensor_values(self, values: dict) -> None:
        """
        Fan out {sensor_id: float} from CSV playback to bridge.

        Uses direct=True so values jump immediately — the CSV player's own
        timing loop controls the pacing.  Ramping here would fight the
        playback speed and produce inaccurate results.
        """
        if self._bridge is None:
            return
        for sid, val in values.items():
            try:
                self._bridge.set_sensor_target(sid, val, direct=True)
            except Exception as ex:
                logger.warning(f"[PLAYBACK] bridge.set_sensor_target({sid}, {val}): {ex}")

    def _set_transport_state(self, state: str) -> None:
        """
        State machine for transport button enable/disable.
          unloaded   → all disabled
          ready      → play enabled, pause/stop disabled
          playing    → pause + stop enabled, play disabled
          paused     → play (resume) + stop enabled, pause disabled
          finished   → play (restart) enabled, pause/stop disabled
        """
        loaded   = state != "unloaded"
        playing  = state == "playing"
        paused   = state == "paused"
        finished = state == "finished"

        self._btn_play.setEnabled(loaded and not playing)
        self._btn_play.setText("▶  RESUME" if paused else "▶  PLAY")
        self._btn_pause.setEnabled(playing)
        self._btn_stop.setEnabled(playing or paused)
        self._scrubber.setEnabled(loaded)
        self._is_playing = playing

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        m = int(seconds) // 60
        s = seconds - m * 60
        return f"{m:02d}:{s:04.1f}"

    # ── Slots: user actions ───────────────────────────────────────

    def _on_browse(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV scenario", "", "CSV files (*.csv);;All files (*)"
        )
        if path:
            self._path_inp.setText(path)

    def _on_load(self) -> None:
        path_str = self._path_inp.text().strip()
        if not path_str:
            self._file_status.setText("⚠ Enter a file path first")
            self._file_status.setStyleSheet("color:#CC1020; font-size:11px;")
            return

        from pathlib import Path as _Path
        from simulator.playback.csv_player import _SENSOR_META

        # Stop any running playback before loading new file
        if self._player.isRunning():
            self._player.stop()
            self._player.wait(2000)

        try:
            info = self._player.load(_Path(path_str))
        except ValueError as ex:
            self._file_status.setText(f"⚠ {ex}")
            self._file_status.setStyleSheet("color:#CC1020; font-size:11px;")
            self._map_card.setVisible(False)
            self._transport_card.setVisible(False)
            self._set_transport_state("unloaded")
            logger.warning(f"[PLAYBACK] Load failed: {ex}")
            return

        self._info = info
        self._total_rows = info.total_rows
        self._duration_s = info.duration_s

        # File status summary
        dur = f" · {self._fmt_time(info.duration_s)}" if info.duration_s > 0 else ""
        self._file_status.setText(
            f"✓  {len(info.sensor_ids)} sensor{'s' if len(info.sensor_ids) != 1 else ''}"
            f" · {info.total_rows:,} rows{dur}"
        )
        self._file_status.setStyleSheet("color:#22C55E; font-size:11px;")

        # Column map display
        # Clear previous widgets
        while self._col_map_row.count():
            item = self._col_map_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for sid in info.sensor_ids:
            meta = _SENSOR_META.get(sid)
            if meta is None:
                continue
            label, unit, *_ = meta
            col_name = info.column_map.all_headers[info.column_map.sensor_cols[sid]]
            pill = QLabel(f"● {label}")
            pill.setStyleSheet(
                "color:#22C55E; background:#0A1A10; border:1px solid #1A4A28;"
                " border-radius:4px; font-size:10px; padding:2px 8px;"
            )
            pill.setToolTip(f"CSV column: {col_name!r}")
            self._col_map_row.addWidget(pill)

        if info.column_map.unmapped:
            ign = QLabel(f"↷ {len(info.column_map.unmapped)} col(s) ignored")
            ign.setStyleSheet("color:#444444; font-size:10px;")
            ign.setToolTip("Ignored: " + ", ".join(info.column_map.unmapped))
            self._col_map_row.addWidget(ign)

        self._col_map_row.addStretch()

        # Scrubber + time reset
        self._scrubber.setRange(0, max(1, info.total_rows - 1))
        self._scrubber.setValue(0)
        self._time_lbl.setText(f"00:00.0 / {self._fmt_time(info.duration_s)}")
        self._row_lbl.setText(f"Row 0 / {info.total_rows:,}")

        self._map_card.setVisible(True)
        self._transport_card.setVisible(True)
        self._set_transport_state("ready")
        logger.info(f"[PLAYBACK] Loaded: {info.path.name}")

    def _on_play(self) -> None:
        if self._info is None:
            return
        self._player.play()
        self._set_transport_state("playing")
        logger.info("[PLAYBACK] ▶ Play")

    def _on_pause(self) -> None:
        self._player.pause()
        self._set_transport_state("paused")

    def _on_stop(self) -> None:
        self._player.stop()
        self._set_transport_state("ready")
        self._scrubber.setValue(0)
        self._time_lbl.setText(f"00:00.0 / {self._fmt_time(self._duration_s)}")
        self._row_lbl.setText(f"Row 0 / {self._total_rows:,}")

    def _on_speed_changed(self, idx: int) -> None:
        speed = self._speed_combo.itemData(idx)
        if speed:
            self._player.set_speed(float(speed))

    def _on_scrub(self, value: int) -> None:
        """User dragged the scrubber — seek the player."""
        self._player.seek(value)

    # ── Slots: player signals ─────────────────────────────────────

    def _on_row_changed(self, current: int, total: int) -> None:
        if total == 0:
            return
        # Scrubber
        self._scrubber.blockSignals(True)
        self._scrubber.setValue(current)
        self._scrubber.blockSignals(False)

        # Time label — derive elapsed from row fraction if we have a duration
        if self._duration_s > 0:
            elapsed = (current / total) * self._duration_s
            self._time_lbl.setText(
                f"{self._fmt_time(elapsed)} / {self._fmt_time(self._duration_s)}"
            )
        else:
            self._time_lbl.setText(f"row {current:,}")

        self._row_lbl.setText(f"Row {current:,} / {total:,}")

    def _on_finished(self) -> None:
        self._set_transport_state("finished")
        logger.info("[PLAYBACK] ● Playback finished")

    def _on_player_error(self, msg: str) -> None:
        self._file_status.setText(f"⚠ {msg}")
        self._file_status.setStyleSheet("color:#CC1020; font-size:11px;")
        self._set_transport_state("unloaded")
        logger.error(f"[PLAYBACK] Player error: {msg}")

