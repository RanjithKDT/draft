from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.icons import IconWidget, Symbol, PAGE_ICONS
from simulator.gui.constants import SIDEBAR_WIDTH


class PlugCard(QWidget):
    """
    Sidebar navigation card — rounded pill style.

    Inactive : transparent, dim icon + text
    Hover    : dark card surfaces, yellow border glow, rounded corners
    Active   : yellow left border, rounded corners, yellow icon + text
    """

    clicked = Signal()

    def __init__(self, label: str, badge: str = "", parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._active = False
        self._label  = label
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(54)
        self.setAttribute(Qt.WA_StyledBackground, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 12, 0)
        row.setSpacing(0)

        # Icon — look up from PAGE_ICONS, IconWidget handles FA→Unicode fallback
        page_icon  = PAGE_ICONS.get(label)
        fa_name    = ("fa6s." + page_icon[0]) if page_icon else "fa6s.circle"
        fallback   = page_icon[1] if page_icon else Symbol.DOT_SMALL
        self._icon = IconWidget(fa=fa_name, fallback=fallback,
                                colour=t.TEXT_DIM, size=14)
        self._icon.setFixedWidth(26)
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        row.addWidget(self._icon)

        row.addSpacing(10)

        # Text column: label + optional badge
        col = QVBoxLayout()
        col.setSpacing(1)
        col.setContentsMargins(0, 0, 0, 0)

        self._name = QLabel(label)
        self._name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        col.addWidget(self._name)

        if badge:
            self._badge = QLabel(badge)
            self._badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            col.addWidget(self._badge)
        else:
            self._badge = None

        row.addLayout(col)
        row.addStretch()

        self._paint("inactive")

    def set_active(self, active: bool) -> None:
        self._active = active
        self._paint("active" if active else "inactive")

    def _paint(self, state: str) -> None:
        if state == "active":
            self.setStyleSheet(f"""
                PlugCard {{
                    background-color: {t.BG_CARD_ACTIVE};
                    border: 1px solid {t.BORDER_STRONG};
                    border-left: 3px solid {t.YELLOW};
                    border-radius: 8px;
                }}
            """)
            self._icon.set_colour(t.YELLOW)
            self._name.setStyleSheet(
                f"color: {t.YELLOW}; font-size: 11px; "
                f"letter-spacing: 2px; font-weight: 500; background: transparent;"
            )
        elif state == "hover":
            self.setStyleSheet(f"""
                PlugCard {{
                    background-color: {t.BG_CARD_HOVER};
                    border: 1px solid {t.RED};
                    border-radius: 8px;
                }}
            """)
            self._icon.set_colour(t.YELLOW)
            self._name.setStyleSheet(
                f"color: {t.TEXT_BRIGHT}; font-size: 11px; "
                f"letter-spacing: 2px; background: transparent;"
            )
        else:  # inactive
            self.setStyleSheet("""
                PlugCard {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 8px;
                }
            """)
            self._icon.set_colour(t.TEXT_DIM)
            self._name.setStyleSheet(
                f"color: {t.TEXT_DIM}; font-size: 11px; "
                f"letter-spacing: 2px; background: transparent;"
            )

        if self._badge:
            self._badge.setStyleSheet(
                f"color: {t.TEXT_DIM}; font-size: 9px; "
                f"letter-spacing: 1px; background: transparent;"
            )

    def update_badge(self, text: str) -> None:
        """Update the badge text live (e.g. '2 ch connected' → '1 ch connected')."""
        if self._badge:
            self._badge.setText(text)
        elif text:
            # Badge didn't exist at construction — create it now
            col = self.findChild(QVBoxLayout)
            self._badge = QLabel(text)
            self._badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self._badge.setStyleSheet(
                f"color: {t.TEXT_DIM}; font-size: 9px; "
                f"letter-spacing: 1px; background: transparent;"
            )
            if col:
                col.addWidget(self._badge)

    def mousePressEvent(self, event: object) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def enterEvent(self, event: object) -> None:
        if not self._active:
            self._paint("hover")

    def leaveEvent(self, event: object) -> None:
        if not self._active:
            self._paint("inactive")


class Sidebar(QWidget):
    """
    C — Plug card nav panel.
    Emits page_requested(index) when a card is clicked.
    Add new cards as each feature is built.

    Page index map:
      0 — HOME
      1 — CAN
    """

    page_requested = Signal(int)

    def __init__(self, can_channel_count: int = 0, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)

        col = QVBoxLayout(self)
        col.setContentsMargins(10, 20, 10, 0)
        col.setSpacing(6)

        self._cards: list[PlugCard] = []
        self._stack_indices: list[int] = []   # parallel list: stack idx per card

        self._add_card("HOME",         index=0)

        self._can_card_index = 1
        self._add_card("CAN",          index=1)

        self._add_card("SENSORS",      index=2)
        self._add_card("PLAYBACK",     index=3)
        self._add_card("CALIBRATIONS", index=15)
        self._add_card("RPC",          index=4)

        self._add_card("SETTINGS",     index=5)
        self._add_card("ABOUT",        index=6)

        col.addStretch()

        # HOME active by default
        self._cards[0].set_active(True)

    def _add_card(self, label: str, index: int, badge: str = "") -> None:
        card = PlugCard(label, badge=badge)
        card.clicked.connect(lambda idx=index: self._on_clicked(idx))
        self.layout().addWidget(card)
        self._cards.append(card)
        self._stack_indices.append(index)

    def update_can_badge(self, connected_count: int, total_count: int) -> None:
        """Update the CAN badge live as adapters connect/disconnect."""
        if connected_count == 0:
            text = "not connected"
        elif connected_count == total_count:
            text = f"{connected_count} ch connected"
        else:
            text = f"{connected_count}/{total_count} ch connected"
        self._cards[self._can_card_index].update_badge(text)

    def _on_clicked(self, index: int) -> None:
        page_names = {
            0: "HOME", 1: "CAN", 2: "SENSORS", 3: "PLAYBACK",
            4: "RPC",  5: "SETTINGS", 6: "ABOUT", 15: "CALIBRATIONS",
        }
        logger.debug(f"[NAV] Sidebar click → {page_names.get(index, index)}")
        # Match by stack index (not card list position) so any insertion order works
        for card, si in zip(self._cards, self._stack_indices):
            card.set_active(si == index)
        self.page_requested.emit(index)


# ══════════════════════════════════════════════════════════════════
# D — CONTENT PAGES
# ══════════════════════════════════════════════════════════════════


