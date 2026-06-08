"""
fonts.py

Loads bundled fonts into Qt at application startup.
Called once from MainWindow.__init__ before any widget is created.

FONT PRIORITY (highest to lowest):
  1. Inter (Variable)     — assets/fonts/InterVariable.ttf    — best screen crispness
  2. Inter (Static TTFs)  — assets/fonts/Inter-Regular.ttf etc — fallback for older Qt
  3. Liberation Sans      — assets/fonts/LiberationSans-*.ttf  — always bundled, always works
  4. System font          — Qt default                         — last resort

All fonts are SIL Open Font Licence — free to bundle and distribute.

Inter:
  Designed for screen readability at small sizes. Used by Figma, GitHub, Linear.
  Works identically on Windows, Linux, and Raspberry Pi because it is bundled.

Liberation Sans:
  Metric-compatible with Arial. Ships on every Raspberry Pi OS / Debian by default.
  Also bundled here so it works on completely bare systems too.
"""

from __future__ import annotations

from pathlib import Path
from loguru import logger

from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication


_FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"

# Load order matters — Inter first (best), Liberation as guaranteed fallback
_FONT_FILES = [
    # Inter — variable font (single file, covers all weights)
    "InterVariable.ttf",
    # Inter — static TTFs (fallback if variable font has issues on older Qt)
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
    # Liberation — always-present fallback
    "LiberationSans-Regular.ttf",
    "LiberationSans-Bold.ttf",
    "LiberationMono-Regular.ttf",
    "LiberationMono-Bold.ttf",
]

# Font name Qt resolves after loading InterVariable.ttf
SANS  = "Inter"
MONO  = "Liberation Mono"

# Full fallback stacks used in stylesheets.
# Qt picks the first font in the list that it has loaded.
SANS_STACK = "'Inter', 'Liberation Sans', 'DejaVu Sans', Arial, sans-serif"
MONO_STACK = "'Liberation Mono', 'DejaVu Sans Mono', Consolas, monospace"


def load_fonts() -> None:
    """Register bundled TTF files with Qt. Call once before any QWidget is created."""
    loaded = 0
    for name in _FONT_FILES:
        path = _FONTS_DIR / name
        if not path.exists():
            logger.debug(f"[FONT] Optional font not found (skipping): {name}")
            continue
        fid = QFontDatabase.addApplicationFont(str(path))
        if fid < 0:
            logger.warning(f"[FONT] Qt rejected font: {name}")
        else:
            loaded += 1
            logger.debug(f"[FONT] Loaded: {name}")

    inter_loaded = (_FONTS_DIR / "InterVariable.ttf").exists() or (_FONTS_DIR / "Inter-Regular.ttf").exists()
    if inter_loaded:
        logger.info(f"[FONT] Inter loaded — UI will use Inter (crisp screen font)")
    else:
        logger.info(f"[FONT] Inter not found — using Liberation Sans (also bundled, works fine)")

    # Set app-wide default font — all widgets inherit this
    app = QApplication.instance()
    if app:
        primary = SANS if inter_loaded else "Liberation Sans"
        default_font = QFont(primary, 10)
        default_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        app.setFont(default_font)
        logger.debug(f"[FONT] App default font set to: {primary} 10pt")
