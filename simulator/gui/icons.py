"""
simulator/gui/icons.py
======================
Named constants for every icon and symbol used in the Hyva Simulator.

WHY THIS FILE EXISTS
--------------------
Without this file, teammates must:
  - Remember exact Unicode characters (easy to get wrong: "■" vs "⬛" look similar)
  - Remember Font Awesome icon names ("fa6s.wrench" — easy to typo)
  - Copy-paste symbols from the internet, which can introduce invisible characters

With this file, teammates just write:
    IconWidget(fa=Fa.CAN_TOOLS)
    ActionButton("SEND", icon=Symbol.SEND)

HOW TO FIND NEW ICONS
---------------------
Font Awesome icons (require qtawesome — pip install qtawesome):
  1. Go to https://fontawesome.com/icons
  2. Click "Free" filter, then "Solid" filter
  3. Click any icon — its name appears at the top (e.g. "house", "bolt")
  4. Use it:  IconWidget(fa="house")   or   IconWidget(fa=Fa.HOME)
  NOTE: You do NOT need to change this file. Just pass the name string directly.
        Only add a constant here when the icon is used in many places.

Unicode symbols (no extra package needed):
  1. Go to https://symbl.cc  or  https://unicode.org/charts
  2. Find your symbol, note its code point (e.g. U+2605)
  3. Use it:  IconWidget(symbol="★")  or  IconWidget(symbol="\u2605")
  NOTE: Stick to the Basic Multilingual Plane (U+0000 – U+FFFF) for
        guaranteed rendering on Windows, Linux, and Raspberry Pi.
        Characters above U+FFFF (emoji etc.) may not render on all systems.

HOW THE ICON FALLBACK CHAIN WORKS
----------------------------------
IconWidget tries sources in this order:
  1. Font Awesome (via qtawesome) — sharpest, scales to any size
  2. Unicode symbol               — always works, any size, no extra library
  3. Plain text                   — last resort

If qtawesome is not installed, FA icons fall back to Unicode automatically.
"""

from __future__ import annotations

from loguru import logger


# ══════════════════════════════════════════════════════════════════
# Font Awesome 6 Solid — icon name constants
#
# These are just the icon names WITHOUT the "fa6s." prefix.
# IconWidget adds the prefix automatically.
# Full list: https://fontawesome.com/icons?f=classic&s=solid&q=
# ══════════════════════════════════════════════════════════════════

class Fa:
    """
    Font Awesome 6 Solid icon name constants.

    Usage:
        from simulator.gui.icons import Fa
        icon = IconWidget(fa=Fa.HOME)
        btn  = ActionButton("Home", fa_icon=Fa.HOME)

    You can also pass any FA name directly without using this class:
        icon = IconWidget(fa="house")
        icon = IconWidget(fa="thumbs-up")
    """

    # ── Navigation / Pages ────────────────────────────────────────
    HOME         = "house"
    CAN          = "plug"
    CAN_TOOLS    = "wrench"
    SENSORS      = "sliders"
    PLAYBACK     = "play"
    CALIBRATIONS = "ruler-combined"
    RPC          = "arrows-left-right"
    SETTINGS     = "gear"
    ABOUT        = "circle-info"

    # ── Actions ───────────────────────────────────────────────────
    SEND         = "paper-plane"
    BROWSE       = "folder-open"
    REFRESH      = "rotate"
    RESET        = "arrow-rotate-left"
    CLOSE        = "xmark"
    PLAY         = "play"
    STOP         = "stop"
    PAUSE        = "pause"
    RESUME       = "play"
    CLEAR        = "eraser"
    APPLY        = "check"
    COPY         = "copy"
    DOWNLOAD     = "download"
    UPLOAD       = "upload"
    SEARCH       = "magnifying-glass"
    FILTER       = "filter"
    EXPAND       = "expand"
    COLLAPSE     = "compress"

    # ── Status / Indicators ───────────────────────────────────────
    CONNECTED    = "circle-check"
    DISCONNECTED = "circle-xmark"
    WARNING      = "triangle-exclamation"
    ERROR        = "circle-exclamation"
    INFO         = "circle-info"
    SUCCESS      = "circle-check"
    LOADING      = "circle-notch"       # use with spinning animation
    DOT          = "circle"
    DOT_HALF     = "circle-half-stroke"
    DOT_DOT      = "circle-dot"

    # ── Hardware / Devices ────────────────────────────────────────
    SERVER       = "server"
    NETWORK      = "network-wired"
    MICROCHIP    = "microchip"
    TERMINAL     = "terminal"
    DESKTOP      = "desktop"
    DISPLAY      = "display"
    LAPTOP       = "laptop-code"
    GAMEPAD      = "gamepad"
    USB          = "usb"                # may need fa6b (brands)
    GAUGE        = "gauge-high"

    # ── Data / Files ──────────────────────────────────────────────
    FILE_CSV     = "file-csv"
    FILE         = "file"
    FOLDER       = "folder-open"
    TABLE        = "table-columns"
    CHART        = "chart-line"
    DATABASE     = "database"

    # ── Time ──────────────────────────────────────────────────────
    CALENDAR     = "calendar-days"
    CLOCK        = "clock"
    TIMER        = "stopwatch"

    # ── Misc ──────────────────────────────────────────────────────
    GLOBE        = "globe"
    BOLT         = "bolt"
    DIAMOND      = "diamond"
    COMPASS      = "compass"
    SCALE        = "scale-balanced"
    WAVE         = "wave-square"
    ARROW_UP     = "arrow-up-long"
    ARROW_RIGHT  = "arrow-right"
    STAR         = "star"
    LOCK         = "lock"
    UNLOCK       = "lock-open"
    EYE          = "eye"
    EYE_OFF      = "eye-slash"
    PLUG         = "plug"
    POWER        = "power-off"


# ══════════════════════════════════════════════════════════════════
# Unicode Symbols — named constants
#
# All symbols are from the Basic Multilingual Plane (U+0000–U+FFFF).
# This range renders correctly on Windows, Linux, and Raspberry Pi
# using the bundled Inter / Liberation fonts.
#
# DO NOT use emoji (U+1F000+) as icon replacements — they render
# differently per OS and at wrong sizes in Qt labels.
# ══════════════════════════════════════════════════════════════════

class Symbol:
    """
    Unicode symbol constants — safe on all platforms.

    Usage:
        from simulator.gui.icons import Symbol
        icon  = IconWidget(symbol=Symbol.CHECK)
        label = StatusLabel("Done", ok=True)   # uses Symbol.CHECK automatically

    You can also pass any character directly:
        icon = IconWidget(symbol="★")
        icon = IconWidget(symbol="\u2605")    # same thing, by code point

    To check if a symbol renders on your system, run:
        python3 -c "print('\u2605')"
    """

    # ── Navigation / Direction ────────────────────────────────────
    BACK          = "\u2190"    # ← left arrow
    FORWARD       = "\u2192"    # → right arrow
    FORWARD_LONG  = "\u27F6"    # ⟶ long right arrow
    UP            = "\u2191"    # ↑ up arrow
    DOWN          = "\u2193"    # ↓ down arrow
    REFRESH       = "\u27F3"    # ⟳ circular arrow
    RESET         = "\u21BA"    # ↺ counterclockwise arrow
    SWAP          = "\u21C4"    # ⇄ left-right arrows (Continuous send)

    # ── Actions ───────────────────────────────────────────────────
    PLAY          = "\u25B6"    # ▶ play triangle
    PLAY_SMALL    = "\u25B8"    # ▸ small play triangle
    STOP          = "\u25A0"    # ■ stop square
    STOP_LARGE    = "\u2B1B"    # ⬛ large stop square
    PAUSE         = "\u23F8"    # ⏸ pause bars
    CLEAR         = "\u232B"    # ⌫ backspace/clear
    CLOSE         = "\u2715"    # ✕ cross/close
    ELLIPSIS      = "\u2026"    # … three dots (Loading…)
    SEND          = "\u27A4"    # ➤ filled right arrow

    # ── Status ────────────────────────────────────────────────────
    CHECK         = "\u2713"    # ✓ tick / success
    CHECK_HEAVY   = "\u2714"    # ✔ heavy tick
    CROSS         = "\u2715"    # ✕ cross / error
    WARNING       = "\u26A0"    # ⚠ warning triangle
    INFO          = "\u24D8"    # ⓘ info circle
    DOT_FULL      = "\u25CF"    # ● filled circle (status dot)
    DOT_EMPTY     = "\u25CB"    # ○ hollow circle (stopped)
    DOT_HALF      = "\u25D1"    # ◑ half circle (simulated)
    DOT_SMALL     = "\u25C6"    # ◆ small diamond dot
    DOT_TINY      = "\u25B8"    # ▸ tiny dot

    # ── Page / Navigation icons ───────────────────────────────────
    HOME          = "\u2302"    # ⌂ house
    CAN           = "\u2299"    # ⊙ circled dot
    SENSORS       = "\u25C8"    # ◈ outlined diamond
    CALIBRATIONS  = "\u2726"    # ✦ four-pointed star
    RPC           = "\u21C4"    # ⇄ swap arrows
    SETTINGS      = "\u2699"    # ⚙ gear
    ABOUT         = "\u24D8"    # ⓘ circled i
    SERVER        = "\u2B21"    # ⬡ hexagon
    NETWORK       = "\u2261"    # ≡ triple bar
    GLOBE         = "\u2295"    # ⊕ circled plus

    # ── Calendar / Time ───────────────────────────────────────────
    CALENDAR      = "\u25A6"    # ▦ gridded square
    CLOCK         = "\u25F7"    # ◷ clock face

    # ── Decorative ───────────────────────────────────────────────
    DIAMOND       = "\u25C6"    # ◆ filled diamond (title pill dot)
    DIAMOND_SMALL = "\u2B29"    # ⬩ small diamond
    STAR          = "\u2605"    # ★ filled star
    STAR_EMPTY    = "\u2606"    # ☆ empty star
    BULLET        = "\u2022"    # • standard bullet

    @staticmethod
    def by_code(code_point: int) -> str:
        """
        Return a symbol by its Unicode code point.

        Example:
            Symbol.by_code(0x2605)  →  "★"
            Symbol.by_code(0x2190)  →  "←"
        """
        return chr(code_point)


# ══════════════════════════════════════════════════════════════════
# Page icon mapping
#
# Maps page names to (FA name, Unicode fallback).
# Used by Sidebar and PageTitleBar so they stay in sync automatically.
# ══════════════════════════════════════════════════════════════════

PAGE_ICONS: dict[str, tuple[str, str]] = {
    # ── Main navigation pages ─────────────────────────────────────
    "HOME":                     (Fa.HOME,         Symbol.HOME),
    "CAN":                      (Fa.CAN,          Symbol.CAN),
    "CAN TOOLS":                (Fa.CAN_TOOLS,    Symbol.SETTINGS),
    "SENSORS":                  (Fa.SENSORS,      Symbol.SENSORS),
    "PLAYBACK":                 (Fa.PLAYBACK,     Symbol.PLAY),
    "CALIBRATIONS":             (Fa.CALIBRATIONS, Symbol.CALIBRATIONS),
    "RPC":                      (Fa.RPC,          Symbol.RPC),
    "SETTINGS":                 (Fa.SETTINGS,     Symbol.SETTINGS),
    "ABOUT":                    (Fa.ABOUT,        Symbol.ABOUT),
    # ── Settings sub-pages ────────────────────────────────────────
    "GENERAL SETTINGS":         (Fa.SETTINGS,     Symbol.SETTINGS),
    "WINDOWS SETTINGS":         (Fa.DESKTOP,      Symbol.SERVER),
    "LINUX SETTINGS":           (Fa.TERMINAL,     Symbol.NETWORK),
    "RASPBERRY PI SETTINGS":    (Fa.MICROCHIP,    Symbol.SERVER),
    # ── Info sub-pages ────────────────────────────────────────────
    "HYVA PRODUCTS":            (Fa.COMPASS,      Symbol.DIAMOND),
}


# ══════════════════════════════════════════════════════════════════
# IconWidget — renders an icon with automatic fallback
# ══════════════════════════════════════════════════════════════════

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class IconWidget(QLabel):
    """
    A label that shows an icon. Tries sources in this order:
      1. Font Awesome via qtawesome (vector, scales perfectly)
      2. Unicode symbol (works without qtawesome)
      3. Plain text (absolute last resort)

    CROSS-PLATFORM: Uses bundled fonts so icons look the same on
    Windows, Linux, and Raspberry Pi.

    Examples:
        # FA icon with Unicode fallback
        icon = IconWidget(fa=Fa.HOME, fallback=Symbol.HOME, size=14)

        # FA by name directly (no constant needed)
        icon = IconWidget(fa="thumbs-up", size=16)

        # Unicode only
        icon = IconWidget(symbol=Symbol.CHECK, colour="#22C55E", size=12)

        # Any Unicode character
        icon = IconWidget(symbol="\u2605", colour="#FFD100", size=10)

        # Plain text fallback only
        icon = IconWidget(text="ON", colour="#22C55E", size=11)

        # Change colour later (e.g. when node connects)
        icon.set_colour("#22C55E")
    """

    def __init__(
        self,
        fa:       str | None = None,    # FA icon name, e.g. "house" or Fa.HOME
        fallback: str | None = None,    # Unicode fallback if qtawesome missing
        symbol:   str | None = None,    # Unicode symbol directly (no FA)
        text:     str | None = None,    # plain text as last resort
        colour:   str = "#F5F5F5",      # icon colour (hex string)
        size:     int = 12,             # font size in px
        parent:   "QLabel | None" = None,
    ) -> None:
        super().__init__(parent)
        self._fa       = fa
        self._fallback = fallback
        self._symbol   = symbol
        self._text     = text
        self._colour   = colour
        self._size     = size

        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._render()

    def _render(self) -> None:
        """Try FA → Unicode → text in order."""
        if self._fa is not None:
            if self._try_qtawesome(self._fa):
                return

        # FA failed or not requested — use Unicode
        target = self._fallback or self._symbol
        if target:
            self._set_text(target)
            return

        # Last resort — plain text
        if self._text:
            self._set_text(self._text)
            return

        logger.debug(f"[ICON] No icon source provided — widget will be empty")

    def _try_qtawesome(self, fa_name: str) -> bool:
        """
        Try to render using qtawesome.
        Returns True on success, False if qtawesome is not installed.
        """
        # Normalise: accept "house" or "fa6s.house" — both work
        full_name = fa_name if fa_name.startswith("fa") else f"fa6s.{fa_name}"
        try:
            import qtawesome as qta
            icon = qta.icon(full_name, color=self._colour)
            pixmap = icon.pixmap(self._size, self._size)
            self.setPixmap(pixmap)
            self.setFixedSize(self._size + 2, self._size + 2)
            return True
        except ImportError:
            logger.debug("[ICON] qtawesome not installed — using Unicode fallback")
            return False
        except Exception as exc:
            logger.debug(f"[ICON] qtawesome failed for '{full_name}': {exc}")
            return False

    def _set_text(self, symbol: str) -> None:
        """Render a Unicode symbol or plain text."""
        self.setText(symbol)
        self.setStyleSheet(
            f"font-size: {self._size}px; "
            f"color: {self._colour}; "
            f"background: transparent;"
        )

    def set_colour(self, colour: str) -> None:
        """
        Change the icon colour without recreating the widget.

        Example:
            dot = IconWidget(fa=Fa.DOT, colour="#CC1020")
            dot.set_colour("#22C55E")   # turns green when connected
        """
        self._colour = colour
        self._render()

    def set_size(self, size: int) -> None:
        """Change the icon size and re-render."""
        self._size = size
        self._render()
