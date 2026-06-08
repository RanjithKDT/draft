from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout

from simulator.gui.components import PageTitleBar


class CalibrationPage(QWidget):
    """
    Page — Calibrations.

    Placeholder for future sensor and hardware calibration workflows.
    Content will be added once calibration procedures are defined.
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(16)

        root.addWidget(PageTitleBar("CALIBRATIONS"))
        root.addStretch()


# ══════════════════════════════════════════════════════════════════
# PLAYBACK PAGE  (stack index 3)
# ══════════════════════════════════════════════════════════════════

