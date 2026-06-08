"""
simulator/gui/theme.py
======================
Single source of truth for every visual value in the Hyva Simulator.

HOW TO USE
----------
Import specific values you need:

    from simulator.gui import theme

    btn.setStyleSheet(f"background: {theme.YELLOW}; color: {theme.TEXT_ON_YELLOW};")
    label.setStyleSheet(f"font-size: {theme.SIZE_MD}px; color: {theme.TEXT_DIM};")

HOW TO CHANGE A COLOUR
-----------------------
Change one value here — every widget that references it updates automatically.

Example: change all primary action button colour from yellow to orange:
    YELLOW = "#F97316"     ← just change this line

HOW THIS FILE IS ORGANISED
---------------------------
1. Brand colours    — the actual Hyva hex values
2. Backgrounds      — page, card, input surface colours
3. Borders          — from invisible to strong
4. Text             — from bright to invisible
5. Interactive      — hover and pressed variants
6. Semantic         — what each colour MEANS (connect meaning to colour)
7. Typography       — fonts and font sizes
8. Shape            — border radii
9. Sizing           — fixed heights for buttons and inputs
10. Spacing         — margin and padding steps

CROSS-PLATFORM NOTES
---------------------
All values are pure strings and numbers — no PySide6 imports here.
This file has zero dependencies and zero side effects.
It is safe to import from any module at any time.
"""

from __future__ import annotations


# ══════════════════════════════════════════════════════════════════
# 1 — BRAND COLOURS  (Hyva identity palette)
# ══════════════════════════════════════════════════════════════════

YELLOW = "#FFD100"    # Hyva primary yellow  — buttons, accents, active state
RED    = "#CC1020"    # Hyva primary red     — danger, stop, error, nav separators
GREEN  = "#22C55E"    # Connected / active / success
BLACK  = "#111111"    # True dark background

# Product colours — each Hyva product has its own accent
YELLOW_GUIDE       = "#FFD100"    # GUIDE
CYAN_CONTROL       = "#38BDF8"    # CONTROL
GREEN_TIP_BY_WIRE  = "#4ADE80"    # TIP BY WIRE
ORANGE_EPTO        = "#F97316"    # EPTO
ORANGE_RASPI       = "#F97316"    # Raspberry Pi settings page

# CAN frame type colours (used in the monitor table)
BLUE_UTC           = "#38BDF8"    # UTC time badge / CAN page right panel
AMBER_EXT          = "#FCD34D"    # Extended (29-bit) frame type label
VIOLET_J1939       = "#A78BFA"    # J1939 frame type label
CYAN_CANFD         = "#4DB8D4"    # CAN-FD frame / playback header


# ══════════════════════════════════════════════════════════════════
# 2 — BACKGROUNDS
# ══════════════════════════════════════════════════════════════════

BG_PAGE        = "#111111"    # main window, page area
BG_SURFACE     = "#1A1A1A"    # header, sidebar, footer
BG_CARD        = "#1E1E1E"    # card surface (standard)
BG_CARD_DEEP   = "#161616"    # slightly darker card (monitor, CAN tools)
BG_CARD_HOVER  = "#242424"    # card on mouse hover
BG_CARD_ACTIVE = "#222222"    # card in active/pressed state
BG_INPUT       = "#0D0D0D"    # text input background
BG_TABLE       = "#0D0D0D"    # table / data grid background
BG_TABLE_ALT   = "#111111"    # alternating table row
BG_SENSOR_CARD = "#181818"    # sensor card (slightly different from standard)

# IGN button backgrounds (radial gradient stop colours)
BG_IGN_OFF_CENTRE = "#3A0A0A"
BG_IGN_OFF_MID    = "#220808"
BG_IGN_OFF_EDGE   = "#0A0303"
BG_IGN_ON_CENTRE  = "#1A4A28"
BG_IGN_ON_MID     = "#0D2A18"
BG_IGN_ON_EDGE    = "#080F0B"
BG_IGN_PEND_CENTRE = "#22C55E"    # pendant blink bright
BG_IGN_PEND_DIM    = "#0A1A10"    # pendant blink dark

# NodePill backgrounds (footer connection pills)
BG_PILL_NEUTRAL    = "#191919"
BG_PILL_PRESENT    = "#111C15"    # green-tinted (node connected)
BG_PILL_SIMULATED  = "#0F1915"    # slightly darker green-tinted

# Hover tint backgrounds for coloured elements
BG_HOVER_YELLOW = "#1A1200"    # dark yellow tint — hover on yellow-bordered items
BG_HOVER_RED    = "#1A0000"    # dark red tint   — hover on red-bordered / back buttons
BG_HOVER_GREEN  = "#0F3A22"    # dark green tint — hover on green elements


# ══════════════════════════════════════════════════════════════════
# 3 — BORDERS
# ══════════════════════════════════════════════════════════════════

BORDER_INVISIBLE = "transparent"
BORDER_FAINT     = "#2A2A2A"    # subtlest — card edges at rest
BORDER_SOFT      = "#2E2E2E"    # inputs, neutral pills
BORDER_MID       = "#333333"    # standard pill border, header dividers
BORDER_STRONG    = "#3A3A3A"    # visible separator lines
BORDER_CARD      = "#2C2C2C"    # card border (slightly different from faint)
BORDER_INPUT_FOCUS = YELLOW     # input fields glow yellow on focus


# ══════════════════════════════════════════════════════════════════
# 4 — TEXT
# ══════════════════════════════════════════════════════════════════

TEXT_BRIGHT   = "#F5F5F5"    # primary body text
TEXT_WHITE    = "#FFFFFF"    # white — on coloured backgrounds
TEXT_MID      = "#E0E0E0"    # slightly dimmer — values, data
TEXT_LABEL    = "#CCCCCC"    # neutral labels
TEXT_SUBTLE   = "#AAAAAA"    # secondary labels
TEXT_DIM      = "#666666"    # dim — inactive labels
TEXT_MUTED    = "#555555"    # very dim — field labels, hints
TEXT_FAINT    = "#444444"    # almost invisible — placeholder-level
TEXT_INVISIBLE = "#333333"   # near-invisible — address labels, sub-text

TEXT_ON_YELLOW = "#111111"   # readable on yellow background
TEXT_ON_GREEN  = "#0A0A0A"   # readable on green background
TEXT_ON_RED    = "#FFFFFF"   # readable on red background

TEXT_GREEN     = "#22C55E"   # success / connected
TEXT_RED       = "#CC1020"   # error / disconnected
TEXT_YELLOW    = "#FFD100"   # accent / active
TEXT_AMBER     = "#A38600"   # dim yellow — checking state


# ══════════════════════════════════════════════════════════════════
# 5 — INTERACTIVE STATES  (hover and pressed variants)
#
# Matte finish rule: hover DARKENS (absorbs light).
# Never use a brighter colour on hover than the base colour.
# ══════════════════════════════════════════════════════════════════

YELLOW_HOVER   = "#E8BA00"    # yellow button hover (matte darkens)
YELLOW_PRESSED = "#C9A000"    # yellow button pressed
YELLOW_DIM     = "#A38600"    # dim yellow — inactive / checking state
YELLOW_DISABLED_BG   = "#2A2200"
YELLOW_DISABLED_TEXT = "#665500"

RED_HOVER   = "#AA0E1A"    # red button hover
RED_PRESSED = "#880C16"    # red button pressed
RED_DIM     = "#661010"    # dim red — IGN OFF border

GREEN_HOVER   = "#1AA050"    # green button hover
GREEN_PRESSED = "#158040"    # green button pressed
GREEN_DIM     = "#1A3A2A"    # disabled green background
GREEN_DIM_TEXT = "#2A6A4A"   # disabled green text

CYAN_HOVER   = "#0F3A22"    # cyan (playback) button hover background
CYAN_BORDER  = "#4DB8D4"    # cyan border for playback section

# Neutral dark button states
NEUTRAL_HOVER   = "#242424"    # dark neutral hover (barely lighter)
NEUTRAL_PRESSED = "#191919"    # dark neutral pressed


# ══════════════════════════════════════════════════════════════════
# 6 — SEMANTIC COLOURS  (what each colour MEANS in the UI)
#
# Use these names when context matters.
# Example: use DANGER not RED when you mean "this action is destructive".
# ══════════════════════════════════════════════════════════════════

# Actions
COLOUR_PRIMARY  = YELLOW      # primary action (SEND, FETCH, APPLY)
COLOUR_DANGER   = RED         # destructive / stop action
COLOUR_SUCCESS  = GREEN       # start / confirm / connected
COLOUR_NEUTRAL  = BG_CARD     # secondary / neutral action

# Connection status
COLOUR_CONNECTED    = GREEN
COLOUR_DISCONNECTED = RED
COLOUR_CHECKING     = YELLOW_DIM    # amber — not yet polled
COLOUR_SIMULATED    = GREEN         # node is faked by simulator

# Node pill label colours (used in NodePill state methods)
TEXT_NODE_PRESENT   = "#2A4A2A"    # muted green — "PRESENT" sub-label text
BORDER_NODE_PRESENT = "#1E4527"    # subtle green pill border when present
BORDER_NODE_SIMUL   = "#1A4025"    # slightly darker green — simulated state border

# Navigation
COLOUR_NAV_ACTIVE = YELLOW    # selected sidebar item
COLOUR_NAV_HOVER  = RED       # hovered sidebar item border
COLOUR_SEPARATOR  = RED       # Hyva red separator lines (header, sidebar)

# Frame types in CAN monitor
COLOUR_FRAME_STD   = TEXT_BRIGHT    # Standard 11-bit
COLOUR_FRAME_EXT   = AMBER_EXT      # Extended 29-bit
COLOUR_FRAME_J1939 = VIOLET_J1939   # J1939
COLOUR_FRAME_FD    = CYAN_CANFD     # CAN-FD


# ══════════════════════════════════════════════════════════════════
# 7 — TYPOGRAPHY
#
# Import font stacks from fonts.py — do not duplicate them here.
# Only sizes and letter-spacing values live here.
# ══════════════════════════════════════════════════════════════════

# Intentional re-exports — other modules use t.FONT_UI and t.FONT_MONO.
# Styles, sensors_page, and components all read these via `t.FONT_UI/FONT_MONO`.
from simulator.gui.fonts import SANS_STACK as FONT_UI, MONO_STACK as FONT_MONO  # noqa: F401

# Font sizes in px
SIZE_XS = 7     # sub-labels (pill sub-text, version dot)
SIZE_SM = 9     # small labels, badges, field category labels
SIZE_MD = 11    # standard body text
SIZE_LG = 13    # card titles, emphasis
SIZE_XL = 15    # header title ("HYVA SIMULATOR")
SIZE_2XL = 18   # large display values (currently unused but reserved)

# Letter spacing in px (used in letter-spacing CSS property)
TRACKING_TIGHT   = "0.5px"
TRACKING_NORMAL  = "1px"
TRACKING_WIDE    = "2px"
TRACKING_WIDEST  = "3px"    # section titles like "DEVICE DETAILS"


# ══════════════════════════════════════════════════════════════════
# 8 — SHAPE  (border-radius values)
#
# Cross-platform note:
#   border-radius on a QWidget only works when WA_StyledBackground is set.
#   All Card/Pill components set this automatically.
# ══════════════════════════════════════════════════════════════════

RADIUS_XS     = 4     # small inputs, tiny buttons
RADIUS_SM     = 5     # standard buttons
RADIUS_MD     = 6     # cards, node pills
RADIUS_LG     = 8     # large cards, page-title pill, header pill
RADIUS_PILL   = 12    # selector pill buttons (MonChBtn shape)
RADIUS_CIRCLE = 999   # fully round — IGN button


# ══════════════════════════════════════════════════════════════════
# 9 — SIZING  (fixed heights for interactive elements)
#
# All values have been tested on Windows 10/11, Ubuntu 22+,
# and Raspberry Pi OS (Bullseye / Bookworm).
# ══════════════════════════════════════════════════════════════════

H_BTN_XS  = 24    # small inline buttons (APPLY in settings rows)
H_BTN_SM  = 26    # slim buttons (FETCH DEVICE DETAILS)
H_BTN_MD  = 28    # standard pill selectors (MonChBtn)
H_BTN_LG  = 34    # primary action buttons (SEND FRAME, ■ Stop)
H_INPUT   = 28    # text input fields
H_NAV     = 54    # sidebar navigation items
H_FOOTER  = 52    # footer bar
H_HEADER  = 60    # top header
H_SEP     = 2     # separator lines (2px for visibility on dark backgrounds)
H_PAGE_TITLE_PILL = 36    # PageTitleBar pill


# ══════════════════════════════════════════════════════════════════
# 10 — SPACING  (margins and padding steps)
#
# Use these for setContentsMargins() and setSpacing() values.
# ══════════════════════════════════════════════════════════════════

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24
