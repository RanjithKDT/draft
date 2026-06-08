from __future__ import annotations

from pathlib import Path
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from loguru import logger

from simulator.gui import theme as t


class GoodbyeScreen(QWidget):
    """
    Full-screen animated goodbye splash shown while the simulator shuts down.

    Animation sequence (driven by a single QTimer tick at 16 ms ≈ 60 fps):
      Phase 1 (0 – 0.3 s)  : Hyva logo fades in and scales up (zoom-in)
      Phase 2 (0.3 – 0.8 s): Logo holds; "See you again · Tot ziens" fades in
      Phase 3 (0.8 – 1.2 s): Everything fades out together

    Total display time: ~1.2 seconds.

    Cross-platform: pure Qt primitives only — no external animation libs.
    """

    # Duration constants (seconds)
    _PHASE_LOGO_IN_END = 0.3
    _PHASE_TEXT_END    = 0.8
    _PHASE_FADE_END    = 1.2

    def __init__(self, logo_path: Path, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._logo_path = logo_path
        self._elapsed   = 0.0        # seconds since animation start
        self._tick_ms   = 16         # ~60 fps
        self._logo_px   = QPixmap()  # loaded in showEvent

        # Full-screen dark overlay — always on top of the main window
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet("background-color: #0D0D0D;")

        self._timer = QTimer(self)
        self._timer.setInterval(self._tick_ms)
        self._timer.timeout.connect(self._tick)

        logger.debug("[GOODBYE] Screen created")

    def showEvent(self, event: object) -> None:
        """Load logo and start animation when widget is shown."""
        if self._logo_path.exists():
            self._logo_px = QPixmap(str(self._logo_path))
            logger.debug(f"[GOODBYE] Logo loaded: {self._logo_path.name}")
        else:
            logger.warning(f"[GOODBYE] Logo not found: {self._logo_path}")

        self._timer.start()
        super().showEvent(event)

    def closeEvent(self, event: object) -> None:
        self._timer.stop()
        super().closeEvent(event)  # type: ignore[arg-type]

    def _tick(self) -> None:
        """Advance animation by one frame."""
        self._elapsed += self._tick_ms / 1000.0
        self.update()   # trigger paintEvent

        if self._elapsed >= self._PHASE_FADE_END:
            self._timer.stop()
            logger.debug("[GOODBYE] Animation complete")

    def paintEvent(self, event: object) -> None:
        from PySide6.QtGui import QPainter, QFont, QColor
        from PySide6.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        cx   = w / 2
        elapsed = self._elapsed   # renamed: avoids shadowing module alias 't = theme'

        # ── Overall opacity ─────────────────────────────────────────
        if elapsed < self._PHASE_LOGO_IN_END:
            overall_alpha = elapsed / self._PHASE_LOGO_IN_END
        elif elapsed > self._PHASE_TEXT_END:
            overall_alpha = 1.0 - (elapsed - self._PHASE_TEXT_END) / (
                self._PHASE_FADE_END - self._PHASE_TEXT_END
            )
        else:
            overall_alpha = 1.0

        overall_alpha = max(0.0, min(1.0, overall_alpha))
        painter.setOpacity(overall_alpha)

        # ── Logo (zoom-in then hold) ─────────────────────────────────
        if not self._logo_px.isNull():
            logo_h = int(h * 0.20)
            logo_w = int(self._logo_px.width() * logo_h / self._logo_px.height())

            scale  = (0.6 + 0.4 * (elapsed / self._PHASE_LOGO_IN_END)
                      if elapsed < self._PHASE_LOGO_IN_END else 1.0)

            draw_w = int(logo_w * scale)
            draw_h = int(logo_h * scale)
            logo_x = int(cx - draw_w / 2)
            logo_y = int(h * 0.30 - draw_h / 2)

            scaled_px = self._logo_px.scaled(
                draw_w, draw_h,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            painter.drawPixmap(logo_x, logo_y, scaled_px)

        # ── Text fades in after logo is fully visible ─────────────────
        text_alpha = 0.0
        if elapsed >= self._PHASE_LOGO_IN_END:
            text_alpha = min(
                1.0,
                (elapsed - self._PHASE_LOGO_IN_END) / (
                    self._PHASE_TEXT_END - self._PHASE_LOGO_IN_END
                ),
            )

        if text_alpha > 0:
            painter.setOpacity(overall_alpha * text_alpha)

            # English
            en_font = QFont("Inter", 24, QFont.Bold)
            en_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
            painter.setFont(en_font)
            painter.setPen(QColor("#F0F0F0"))
            text_y = int(h * 0.60)
            painter.drawText(
                QRectF(0, text_y - 36, w, 44),
                Qt.AlignHCenter | Qt.AlignVCenter,
                "See you again",
            )

            # Dutch
            nl_font = QFont("Inter", 13)
            nl_font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
            painter.setFont(nl_font)
            painter.setPen(QColor(t.YELLOW))   # t = theme alias (not local float)
            painter.drawText(
                QRectF(0, text_y + 16, w, 28),
                Qt.AlignHCenter | Qt.AlignVCenter,
                "Tot ziens",
            )

        painter.end()

