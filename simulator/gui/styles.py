"""
simulator/gui/styles.py
=======================
Builds the complete Qt stylesheet for the Hyva Simulator.

HOW IT WORKS
------------
One function — build_stylesheet() — returns a single QSS string.
This is applied once at startup with app.setStyleSheet(build_stylesheet()).

After that, any widget with the right objectName gets styled automatically.
Teammates never write CSS — they just set the correct objectName:

    btn = QPushButton("SEND FRAME")
    btn.setObjectName("action-btn")    ← that is all
    # The global stylesheet handles the rest.

OBJECTNAME → STYLE MAPPING
---------------------------
Every objectName recognised by this stylesheet is listed below.
Use these exact strings in setObjectName() calls.

BUTTONS:
    "action-btn"      Yellow filled   — primary actions  (SEND, FETCH, APPLY)
    "danger-btn"      Red filled      — stop / cancel    (■ Stop, STOP)
    "success-btn"     Green filled    — start / confirm  (▶ START, ▶ PLAY)
    "ghost-btn"       Transparent     — back / nav       (← CAN, ← Back)
    "icon-btn"        Icon only       — small square     (✕, ↺)
    "pill-btn"        Dark rounded    — selectors        (channel, DLC, baudrate)
    "toggle-off"      Dark neutral    — toggle ready     (⇄ Continuous)
    "toggle-on"       Red filled      — toggle active    (■ Stop)
    "link-btn"        Inline link     — subtle text link

INPUTS:
    "field"           Dark text input — any text/hex entry

LABELS:
    "section-label"   Dim uppercase   — "CHANNEL", "DLC", "INTERVAL"
    "value-label"     Mono bright     — live readings, hex addresses
    "status-ok"       Green text      — success message
    "status-err"      Red text        — error message
    "card-title"      Accent title    — inside card headers
    "badge"           Small label     — count badges

CARDS:
    "card"            Standard card
    "sub-card"        Nested card

DISPLAY:
    "data-table"      Dark read-only table

SEPARATORS:
    "h-sep"           Thin grey line
    "red-sep-h"       Hyva red horizontal
    "red-sep-v"       Hyva red vertical

PAGE CHROME (existing names — kept for backward compatibility):
    "TopHeader", "Sidebar", "FooterBar", "FooterLeft", "FooterRight"
    "TitlePill", "HeaderTitle", "ClockPill", "ClockDate", "ClockTime"
    "UtcPill", "UtcBadge", "PageTitlePill", "PanelTitle"
    "NodePill", "VersionPill", "OsPill", "VersionLabel", "FooterPlatform"
    "PillSub", "RedSepH", "RedSepV"
    "MonChBtn", "MonStartBtn", "MonStopBtn", "MonClearBtn"
    "BaudBtn", "FetchBtn", "CanCardApply", "SendField", "FrameTypeRb"
    "MonTable", "ClearLogBtn"

CROSS-PLATFORM NOTES
--------------------
- No CSS triangle tricks (broken on Windows/Fusion). Use SVG files.
- No QFrame(HLine) separators (render white on Windows). Use QWidget.
- All font-family values use the fallback stack from theme.FONT_UI.
- All colour values come from theme.py — change there, updates here.
"""

from __future__ import annotations

from simulator.gui import theme as t


def build_stylesheet(arrow_svg_path: str = "") -> str:
    """
    Build and return the complete QSS stylesheet string.

    Call once at startup:
        from simulator.gui.styles import build_stylesheet
        app.setStyleSheet(build_stylesheet(arrow_svg_path=_ARROW_SVG))

    Args:
        arrow_svg_path: Path to the yellow dropdown arrow SVG file.
                        Created at startup in main_window.py.
                        Use forward slashes on all platforms (Qt requirement).

    Returns:
        A single QSS string covering every named widget in the simulator.
    """
    return f"""

/* ── Base ──────────────────────────────────────────────────────── */

QMainWindow {{
    background-color: {t.BG_PAGE};
}}

QWidget {{
    background-color: {t.BG_PAGE};
    color: {t.TEXT_BRIGHT};
    font-family: {t.FONT_UI};
    font-size: {t.SIZE_MD}px;
}}

QLabel {{
    background-color: transparent;
}}

QScrollArea,
QScrollArea > QWidget > QWidget {{
    background: transparent;
    border: none;
}}


/* ── Page chrome ────────────────────────────────────────────────── */

QWidget#TopHeader {{
    background-color: {t.BG_SURFACE};
}}

QWidget#Sidebar {{
    background-color: {t.BG_SURFACE};
}}

QWidget#FooterBar {{
    background-color: {t.BG_SURFACE};
    border-top: 1px solid {t.BORDER_STRONG};
}}

QWidget#FooterLeft,
QWidget#FooterRight {{
    background-color: {t.BG_SURFACE};
}}

QWidget#RedSepH {{
    background-color: {t.RED};
    border: none;
}}

QWidget#RedSepV {{
    background-color: {t.RED};
    border: none;
}}

QFrame#HeaderDivider {{
    color: {t.BORDER_STRONG};
}}


/* ── Header pills ────────────────────────────────────────────────── */

QWidget#TitlePill {{
    background-color: {t.BG_CARD};
    border: 1px solid {t.BORDER_MID};
    border-left: 3px solid {t.YELLOW};
    border-radius: {t.RADIUS_LG}px;
}}

QWidget#ClockPill,
QWidget#UtcPill {{
    background-color: {t.BG_CARD};
    border: 1px solid {t.BORDER_MID};
    border-radius: {t.RADIUS_LG}px;
}}

QLabel#HeaderTitle {{
    color: {t.YELLOW};
    font-size: {t.SIZE_XL}px;
    font-weight: normal;
    letter-spacing: {t.TRACKING_WIDE};
    background: transparent;
}}

QLabel#ClockDate {{
    color: {t.YELLOW};
    font-size: {t.SIZE_MD}px;
    letter-spacing: {t.TRACKING_TIGHT};
    background: transparent;
    font-family: {t.FONT_MONO};
}}

QLabel#ClockTime {{
    color: {t.YELLOW};
    font-size: {t.SIZE_LG}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_NORMAL};
    background: transparent;
    font-family: {t.FONT_MONO};
}}

QLabel#UtcBadge {{
    color: {t.BLUE_UTC};
    font-size: {t.SIZE_SM}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_WIDE};
    background: transparent;
}}


/* ── Page title bar ──────────────────────────────────────────────── */

QWidget#PageTitlePill {{
    background-color: {t.BG_CARD};
    border: 1px solid {t.BORDER_MID};
    border-left: 3px solid {t.YELLOW};
    border-radius: {t.RADIUS_LG}px;
}}

QLabel#PanelTitle {{
    color: {t.YELLOW};
    font-size: {t.SIZE_LG}px;
    letter-spacing: {t.TRACKING_WIDEST};
    background: transparent;
}}


/* ── Footer pills ────────────────────────────────────────────────── */

QWidget#VersionPill {{
    background-color: {t.BG_PILL_NEUTRAL};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: {t.RADIUS_MD}px;
}}

QLabel#VersionLabel {{
    color: {t.TEXT_LABEL};
    font-size: {t.SIZE_MD}px;
    letter-spacing: {t.TRACKING_NORMAL};
    background: transparent;
}}

QWidget#OsPill {{
    background-color: {t.BG_PILL_NEUTRAL};
    border: 1px solid {t.BORDER_FAINT};
    border-radius: {t.RADIUS_MD}px;
}}

QLabel#FooterPlatform {{
    color: {t.TEXT_BRIGHT};
    font-size: {t.SIZE_SM}px;
    letter-spacing: {t.TRACKING_TIGHT};
    background: transparent;
}}

QLabel#PillSub {{
    color: {t.TEXT_DIM};
    font-size: {t.SIZE_XS}px;
    background: transparent;
}}


/* ── NEW: Generic named button styles ────────────────────────────── */
/* Use these by setting objectName on any QPushButton.               */

QPushButton[objectName="action-btn"] {{
    background-color: {t.YELLOW};
    color: {t.TEXT_ON_YELLOW};
    border: none;
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_MD}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_WIDE};
    padding: 0 16px;
}}
QPushButton[objectName="action-btn"]:hover   {{ background-color: {t.YELLOW_HOVER}; }}
QPushButton[objectName="action-btn"]:pressed {{ background-color: {t.YELLOW_PRESSED}; }}
QPushButton[objectName="action-btn"]:disabled {{
    background-color: {t.YELLOW_DISABLED_BG};
    color: {t.YELLOW_DISABLED_TEXT};
}}

QPushButton[objectName="danger-btn"] {{
    background-color: {t.RED};
    color: {t.TEXT_ON_RED};
    border: none;
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_MD}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_NORMAL};
    padding: 0 14px;
}}
QPushButton[objectName="danger-btn"]:hover   {{ background-color: {t.RED_HOVER}; }}
QPushButton[objectName="danger-btn"]:pressed {{ background-color: {t.RED_PRESSED}; }}

QPushButton[objectName="success-btn"] {{
    background-color: {t.GREEN};
    color: {t.TEXT_ON_GREEN};
    border: none;
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_MD}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_NORMAL};
    padding: 0 14px;
}}
QPushButton[objectName="success-btn"]:hover   {{ background-color: {t.GREEN_HOVER}; }}
QPushButton[objectName="success-btn"]:pressed {{ background-color: {t.GREEN_PRESSED}; }}
QPushButton[objectName="success-btn"]:disabled {{
    background-color: {t.GREEN_DIM};
    color: {t.GREEN_DIM_TEXT};
}}

QPushButton[objectName="ghost-btn"] {{
    background-color: transparent;
    color: {t.TEXT_DIM};
    border: 1px solid {t.BORDER_SOFT};
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_SM}px;
    padding: 0 12px;
}}
QPushButton[objectName="ghost-btn"]:hover {{
    color: {t.RED};
    border-color: {t.RED};
    background-color: {t.BG_HOVER_RED};
}}

QPushButton[objectName="pill-btn"] {{
    background-color: {t.BG_PILL_NEUTRAL};
    color: {t.TEXT_LABEL};
    border: 1px solid {t.BORDER_SOFT};
    border-radius: {t.RADIUS_PILL}px;
    font-size: {t.SIZE_MD}px;
    padding: 4px 12px 4px 10px;
}}
QPushButton[objectName="pill-btn"]:hover {{
    background-color: {t.BG_HOVER_YELLOW};
    border-color: {t.YELLOW};
    color: {t.YELLOW};
}}
QPushButton[objectName="pill-btn"]:pressed {{ background-color: #141000; }}

QPushButton[objectName="toggle-off"] {{
    background-color: {t.BG_PILL_NEUTRAL};
    color: {t.TEXT_LABEL};
    border: 1px solid {t.BORDER_SOFT};
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_SM}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_NORMAL};
    padding: 0 14px;
}}
QPushButton[objectName="toggle-off"]:hover {{
    background-color: {t.NEUTRAL_HOVER};
    border-color: {t.BORDER_STRONG};
    color: {t.TEXT_BRIGHT};
}}
QPushButton[objectName="toggle-off"]:pressed {{ background-color: {t.NEUTRAL_PRESSED}; }}

QPushButton[objectName="toggle-on"] {{
    background-color: {t.RED};
    color: {t.TEXT_ON_RED};
    border: none;
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_SM}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_NORMAL};
    padding: 0 14px;
}}
QPushButton[objectName="toggle-on"]:hover   {{ background-color: {t.RED_HOVER}; }}
QPushButton[objectName="toggle-on"]:pressed {{ background-color: {t.RED_PRESSED}; }}

QPushButton[objectName="icon-btn"] {{
    background-color: transparent;
    color: {t.TEXT_DIM};
    border: none;
    border-radius: {t.RADIUS_XS}px;
    font-size: {t.SIZE_MD}px;
    padding: 2px 6px;
}}
QPushButton[objectName="icon-btn"]:hover {{
    color: {t.RED};
    background-color: {t.BG_HOVER_RED};
}}

QPushButton[objectName="link-btn"] {{
    background-color: transparent;
    color: {t.YELLOW};
    border: none;
    font-size: {t.SIZE_MD}px;
    text-decoration: underline;
    padding: 0;
}}
QPushButton[objectName="link-btn"]:hover {{ color: {t.YELLOW_HOVER}; }}


/* ── NEW: Generic named input styles ─────────────────────────────── */

QLineEdit[objectName="field"] {{
    background-color: {t.BG_INPUT};
    color: {t.TEXT_MID};
    border: 1px solid {t.BORDER_SOFT};
    border-radius: {t.RADIUS_XS}px;
    padding: 2px 8px;
    font-size: {t.SIZE_MD}px;
    font-family: {t.FONT_MONO};
}}
QLineEdit[objectName="field"]:focus {{
    border-color: {t.YELLOW};
}}


/* ── NEW: Generic named label styles ─────────────────────────────── */

QLabel[objectName="section-label"] {{
    color: {t.TEXT_MUTED};
    font-size: {t.SIZE_SM}px;
    letter-spacing: {t.TRACKING_NORMAL};
    background: transparent;
}}

QLabel[objectName="value-label"] {{
    color: {t.TEXT_MID};
    font-size: {t.SIZE_MD}px;
    font-family: {t.FONT_MONO};
    background: transparent;
}}

QLabel[objectName="status-ok"] {{
    color: {t.TEXT_GREEN};
    font-size: {t.SIZE_SM}px;
    background: transparent;
}}

QLabel[objectName="status-err"] {{
    color: {t.TEXT_RED};
    font-size: {t.SIZE_SM}px;
    background: transparent;
}}

QLabel[objectName="card-title"] {{
    color: {t.YELLOW};
    font-size: {t.SIZE_MD}px;
    letter-spacing: {t.TRACKING_WIDE};
    font-weight: bold;
    background: transparent;
}}

QLabel[objectName="badge"] {{
    color: {t.TEXT_DIM};
    font-size: {t.SIZE_SM}px;
    letter-spacing: {t.TRACKING_NORMAL};
    background: transparent;
}}


/* ── Separators ──────────────────────────────────────────────────────────── */
/* All separator widgets use QWidget (not QFrame) so they render correctly  */
/* on Windows/Fusion style. QFrame(HLine/VLine) renders as white on Fusion. */
/* WA_StyledBackground is set in the component class — required on Windows.  */

QWidget[objectName="h-sep"] {{
    background-color: {t.BORDER_STRONG};
    border: none;
}}

/* Red horizontal separator — below the top header (3 px) and inside pages. */
QWidget[objectName="red-sep-h"] {{
    background-color: {t.RED};
    border: none;
}}

/* Red vertical separator — between sidebar and content area.
   min-width ensures it never collapses to 0 on high-DPI or Fusion style.
   It stretches to full content height automatically because it is placed in
   the same QHBoxLayout as the sidebar (Expanding) and QStackedWidget
   (Expanding) — both force the layout row to be as tall as the window. */
QWidget[objectName="red-sep-v"] {{
    background-color: {t.RED};
    border: none;
    min-width: 2px;
}}


/* ── CAN Monitor ─────────────────────────────────────────────────── */

QTableWidget#MonTable {{
    background-color: {t.BG_TABLE};
    alternate-background-color: {t.BG_TABLE_ALT};
    color: #D0D0D0;
    gridline-color: {t.BG_CARD};
    font-size: {t.SIZE_MD}px;
    border: 1px solid #222222;
    border-radius: {t.RADIUS_XS}px;
    selection-background-color: {t.BG_CARD_HOVER};
}}

QHeaderView::section {{
    background-color: {t.BG_SURFACE};
    color: {t.TEXT_DIM};
    font-size: {t.SIZE_SM}px;
    letter-spacing: {t.TRACKING_NORMAL};
    border: none;
    border-bottom: 1px solid {t.BORDER_FAINT};
    padding: 4px 6px;
}}

QPushButton#MonChBtn {{
    background-color: {t.BG_PILL_NEUTRAL};
    color: {t.TEXT_LABEL};
    border: 1px solid {t.BORDER_SOFT};
    border-radius: {t.RADIUS_PILL}px;
    padding: 4px 12px 4px 10px;
    font-size: {t.SIZE_MD}px;
}}
QPushButton#MonChBtn:hover {{
    background-color: {t.BG_HOVER_YELLOW};
    border-color: {t.YELLOW};
    color: {t.YELLOW};
}}
QPushButton#MonChBtn:pressed {{ background-color: #141000; }}

QPushButton#MonStartBtn {{
    background-color: {t.GREEN};
    color: {t.TEXT_ON_GREEN};
    border: none;
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_SM}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_NORMAL};
    padding: 0 12px;
}}
QPushButton#MonStartBtn:hover   {{ background-color: {t.GREEN_HOVER}; }}
QPushButton#MonStartBtn:pressed {{ background-color: {t.GREEN_PRESSED}; }}
QPushButton#MonStartBtn:disabled {{
    background-color: {t.GREEN_DIM};
    color: {t.GREEN_DIM_TEXT};
}}

QPushButton#MonStopBtn {{
    background-color: {t.BG_PILL_NEUTRAL};
    color: {t.RED};
    border: 1px solid {t.RED};
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_SM}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_NORMAL};
    padding: 0 12px;
}}
QPushButton#MonStopBtn:hover {{
    background-color: #1E0808;
    border-color: #E01020;
}}
QPushButton#MonStopBtn:pressed {{ background-color: #160606; }}
QPushButton#MonStopBtn:disabled {{
    border-color: {t.BORDER_SOFT};
    color: {t.TEXT_INVISIBLE};
}}

QPushButton#MonClearBtn {{
    background-color: {t.BG_PILL_NEUTRAL};
    color: {t.TEXT_DIM};
    border: 1px solid {t.BORDER_SOFT};
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_SM}px;
    letter-spacing: {t.TRACKING_NORMAL};
    padding: 0 12px;
}}
QPushButton#MonClearBtn:hover {{
    background-color: {t.NEUTRAL_HOVER};
    color: {t.TEXT_SUBTLE};
    border-color: {t.BORDER_STRONG};
}}

QPushButton#ClearLogBtn {{
    background-color: {t.BG_SURFACE};
    color: {t.TEXT_DIM};
    border: 1px solid {t.BORDER_FAINT};
    border-radius: {t.RADIUS_XS}px;
    font-size: {t.SIZE_SM}px;
    padding: 0 10px;
}}
QPushButton#ClearLogBtn:hover {{
    background-color: #3A1A1A;
    color: {t.RED};
    border-color: {t.RED};
}}
QPushButton#ClearLogBtn:pressed {{ background-color: #4A2020; }}


/* ── CAN Channel / Baud ──────────────────────────────────────────── */

QPushButton#BaudBtn {{
    background-color: {t.BG_PILL_NEUTRAL};
    color: {t.TEXT_LABEL};
    border: 1px solid {t.BORDER_SOFT};
    border-radius: {t.RADIUS_PILL}px;
    padding: 4px 12px 4px 10px;
    font-size: {t.SIZE_MD}px;
}}
QPushButton#BaudBtn:hover {{
    background-color: {t.BG_HOVER_YELLOW};
    border-color: {t.YELLOW};
    color: {t.YELLOW};
}}
QPushButton#BaudBtn:pressed {{ background-color: #141000; }}

QPushButton#CanCardApply {{
    background-color: {t.YELLOW};
    color: {t.TEXT_ON_YELLOW};
    border: none;
    border-radius: {t.RADIUS_XS}px;
    padding: 6px 0px;
    font-size: {t.SIZE_SM}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_WIDE};
}}
QPushButton#CanCardApply:hover   {{ background-color: {t.YELLOW_HOVER}; }}
QPushButton#CanCardApply:pressed {{ background-color: {t.YELLOW_PRESSED}; }}

QComboBox#MonCombo,
QComboBox#CanCardCombo {{
    background-color: {t.BG_SURFACE};
    color: {t.TEXT_BRIGHT};
    border: 1px solid {t.BORDER_MID};
    border-radius: {t.RADIUS_SM}px;
    padding: 3px 28px 3px 8px;
    font-size: {t.SIZE_MD}px;
}}
QComboBox#MonCombo:hover,
QComboBox#CanCardCombo:hover {{ border-color: {t.YELLOW}; }}

QComboBox#MonCombo::drop-down,
QComboBox#CanCardCombo::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    background-color: {t.BG_SURFACE};
    border-left: 1px solid {t.BORDER_MID};
    border-top-right-radius: {t.RADIUS_SM}px;
    border-bottom-right-radius: {t.RADIUS_SM}px;
}}
QComboBox#MonCombo::down-arrow,
QComboBox#CanCardCombo::down-arrow {{
    image: url({arrow_svg_path});
    width: 10px;
    height: 7px;
}}
QComboBox#MonCombo:hover::drop-down,
QComboBox#CanCardCombo:hover::drop-down {{
    background-color: {t.BG_HOVER_YELLOW};
    border-left-color: {t.YELLOW};
}}
QComboBox#MonCombo:on,
QComboBox#CanCardCombo:on {{ border-color: {t.YELLOW}; }}
QComboBox#MonCombo:on::down-arrow,
QComboBox#CanCardCombo:on::down-arrow {{ image: none; width: 0; height: 0; }}

QComboBox#MonCombo QAbstractItemView,
QComboBox#CanCardCombo QAbstractItemView {{
    background-color: {t.BG_PAGE};
    color: {t.TEXT_BRIGHT};
    border: 1px solid {t.YELLOW};
    selection-background-color: {t.BG_HOVER_YELLOW};
    selection-color: {t.YELLOW};
    outline: 0px;
}}
QComboBox#MonCombo QAbstractItemView::item,
QComboBox#CanCardCombo QAbstractItemView::item {{
    padding: 6px 8px;
    min-height: 22px;
    background-color: transparent;
    color: {t.TEXT_BRIGHT};
}}
QComboBox#MonCombo QAbstractItemView::item:hover,
QComboBox#CanCardCombo QAbstractItemView::item:hover {{
    background-color: {t.BG_HOVER_YELLOW};
    color: {t.YELLOW};
}}


/* ── Frame type radio buttons ────────────────────────────────────── */

QRadioButton#FrameTypeRb {{
    color: {t.TEXT_DIM};
    font-size: {t.SIZE_MD}px;
    background: transparent;
    spacing: 6px;
}}
QRadioButton#FrameTypeRb::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 2px solid #444444;
    background: transparent;
}}
QRadioButton#FrameTypeRb::indicator:checked {{
    border: 2px solid {t.YELLOW};
    background: {t.YELLOW};
}}
QRadioButton#FrameTypeRb:checked {{ color: {t.YELLOW}; }}


/* ── Send / Build & Send ─────────────────────────────────────────── */

QLineEdit#SendField {{
    background-color: {t.BG_INPUT};
    color: {t.TEXT_MID};
    border: 1px solid {t.BORDER_SOFT};
    border-radius: {t.RADIUS_XS}px;
    padding: 2px 8px;
    font-size: {t.SIZE_MD}px;
    font-family: {t.FONT_MONO};
}}
QLineEdit#SendField:focus {{ border-color: {t.YELLOW}; }}

QPushButton#FetchBtn {{
    background-color: {t.YELLOW};
    color: {t.TEXT_ON_YELLOW};
    border: none;
    border-radius: {t.RADIUS_SM}px;
    font-size: {t.SIZE_MD}px;
    font-weight: bold;
    letter-spacing: {t.TRACKING_WIDE};
}}
QPushButton#FetchBtn:hover   {{ background-color: {t.YELLOW_HOVER}; }}
QPushButton#FetchBtn:pressed {{ background-color: {t.YELLOW_PRESSED}; }}
QPushButton#FetchBtn:disabled {{
    background-color: {t.YELLOW_DISABLED_BG};
    color: {t.YELLOW_DISABLED_TEXT};
}}

QLabel#CanNoneMsg {{
    color: {t.TEXT_DIM};
    font-size: {t.SIZE_LG}px;
    background: transparent;
}}

QWidget#CanCard {{
    background-color: {t.BG_CARD};
    border: 1px solid {t.BORDER_STRONG};
    border-radius: {t.RADIUS_MD}px;
}}

QLabel#CanCardTitle {{
    color: {t.TEXT_WHITE};
    font-size: {t.SIZE_LG}px;
    letter-spacing: {t.TRACKING_NORMAL};
    background: transparent;
}}

QLabel#CanCardStatus {{
    color: {t.TEXT_DIM};
    font-size: {t.SIZE_MD}px;
    background: transparent;
}}

QLabel#CanCardFieldLabel {{
    color: {t.TEXT_DIM};
    font-size: {t.SIZE_SM}px;
    letter-spacing: {t.TRACKING_NORMAL};
    background: transparent;
}}

""".strip()
