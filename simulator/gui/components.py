"""
simulator/gui/components.py
===========================
All reusable UI components for the Hyva Simulator.

WHY THIS FILE EXISTS
--------------------
Teammates use these components to build pages WITHOUT writing any CSS,
without typing Unicode symbols, and without re-implementing the same
visual patterns over and over.

HOW TO USE
----------
    from simulator.gui.components import (
        Card, ActionButton, DangerButton, PillSelector,
        TextField, SectionLabel, StatusLabel, HSep,
    )

    # Build a section — zero CSS
    card, layout = Card.create("BUILD & SEND")
    layout.addWidget(SectionLabel("CHANNEL"))
    ch = PillSelector("PCAN_USBBUS1 — 250 kbps")
    layout.addWidget(ch)
    layout.addWidget(HSep())
    btn = ActionButton("SEND FRAME")
    layout.addWidget(btn)
    status = StatusLabel()
    layout.addWidget(status)

    # Wire logic — pure Python
    ch.selected.connect(self._on_channel)
    btn.clicked.connect(self._on_send)

    def _on_send(self):
        try:
            # ... do the work ...
            status.set_ok("Sent on PCAN_USBBUS1")
        except Exception as e:
            status.set_error(str(e))

FULL QT API IS AVAILABLE
------------------------
Every component inherits from its Qt base class.
All Qt methods work exactly as documented:

    btn = ActionButton("SEND FRAME")
    btn.setEnabled(False)       # ← standard Qt — works
    btn.setToolTip("Send now")  # ← standard Qt — works
    btn.setFixedWidth(200)      # ← standard Qt — works
    btn.clicked.connect(fn)     # ← standard Qt signal — works

CROSS-PLATFORM NOTES
--------------------
- Uses bundled fonts (Inter / Liberation) — identical on Win/Linux/Pi.
- Uses IconWidget which falls back from FA → Unicode automatically.
- HSep uses QWidget (not QFrame) — QFrame renders white on Windows.
- All colours from theme.py — one change updates everything.
"""

from __future__ import annotations

from PySide6.QtCore    import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QMenu, QSizePolicy,
)
from PySide6.QtGui import QIntValidator, QDoubleValidator
from loguru import logger

from simulator.gui import theme as t
from simulator.gui.icons import IconWidget, Fa, Symbol, PAGE_ICONS


# ══════════════════════════════════════════════════════════════════
# BUTTONS
# ══════════════════════════════════════════════════════════════════

class ActionButton(QPushButton):
    """
    Yellow filled button — use for primary actions.

    Examples:
        send  = ActionButton("SEND FRAME")
        fetch = ActionButton("FETCH DEVICE DETAILS")
        apply = ActionButton("APPLY", height=24)    # smaller

    Full Qt API works:
        send.setEnabled(False)
        send.setToolTip("Click to send")
        send.clicked.connect(my_function)
    """

    def __init__(self, text: str, height: int = t.H_BTN_LG, parent: "QWidget | None" = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("action-btn")
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)


class DangerButton(QPushButton):
    """
    Red filled button — use for stop, cancel, or destructive actions.

    Examples:
        stop  = DangerButton("■  Stop")
        abort = DangerButton("ABORT")
    """

    def __init__(self, text: str, height: int = t.H_BTN_LG, parent: "QWidget | None" = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("danger-btn")
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)


class SuccessButton(QPushButton):
    """
    Green filled button — use for start or confirm actions.

    Examples:
        start = SuccessButton("▶  START")
        play  = SuccessButton("▶  PLAY")
    """

    def __init__(self, text: str, height: int = t.H_BTN_LG, parent: "QWidget | None" = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("success-btn")
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)


class GhostButton(QPushButton):
    """
    Transparent button with border — use for navigation (Back, Close).
    Turns red on hover to signal "leaving this context".

    Examples:
        back = GhostButton(f"{Symbol.BACK}  CAN")
        back.clicked.connect(self._go_can)
    """

    def __init__(
        self,
        text:   str,
        height: int = t.H_BTN_MD,
        radius: int = t.RADIUS_PILL,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("ghost-btn")
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)
        # Allow custom radius (e.g. pill vs standard)
        if radius != t.RADIUS_SM:
            self.setStyleSheet(
                self.styleSheet()
                + f"QPushButton {{ border-radius: {radius}px; }}"
            )


class PillButton(QPushButton):
    """
    Dark rounded pill — use for selectors that open a dropdown menu.

    Examples:
        ch  = PillButton("PCAN_USBBUS1 — 250 kbps")
        dlc = PillButton("8  ▼", width=72)

    The ▼ arrow is optional — add it manually in the text if you want it.
    """

    def __init__(
        self,
        text:   str,
        width:  int | None = None,
        height: int = t.H_BTN_MD,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("pill-btn")
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)
        if width is not None:
            self.setFixedWidth(width)


class ToggleButton(QPushButton):
    """
    Two-state toggle button.
    OFF state: dark neutral.
    ON state: red (signals an active process that can be stopped).

    The button manages its own visual state — you only wire the state_changed signal.

    Examples:
        cont = ToggleButton(off_text="⇄  Continuous", on_text="■  Stop")
        cont.state_changed.connect(self._on_continuous_toggle)

        # Check current state
        if cont.is_on():
            print("continuous is running")

        # Force a state (e.g. when an error occurs)
        cont.set_state(False)
    """

    # Emitted when the button is clicked. True = now ON, False = now OFF.
    # Named 'state_changed' to avoid shadowing QAbstractButton.toggled(bool).
    state_changed = Signal(bool)

    def __init__(
        self,
        off_text: str = f"{Symbol.SWAP}  Continuous",
        on_text:  str = f"{Symbol.STOP}  Stop",
        height:   int = t.H_BTN_LG,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(off_text, parent)
        self._off_text = off_text
        self._on_text  = on_text
        self._on       = False
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)
        self._paint()
        self.clicked.connect(self._on_click)

    def _on_click(self) -> None:
        self.set_state(not self._on)
        self.state_changed.emit(self._on)

    def _paint(self) -> None:
        if self._on:
            self.setText(self._on_text)
            self.setObjectName("toggle-on")
        else:
            self.setText(self._off_text)
            self.setObjectName("toggle-off")
        # Force Qt to re-apply the stylesheet after objectName change
        self.style().unpolish(self)
        self.style().polish(self)

    def set_state(self, on: bool) -> None:
        """
        Programmatically set the button state without emitting toggled.

        Use this when external logic (e.g. a send error) needs to turn
        the button off without triggering the toggle callback again.
        """
        self._on = on
        self._paint()

    def is_on(self) -> bool:
        """Return True when the button is in the ON (active) state."""
        return self._on


class IconButton(QPushButton):
    """
    Small square icon-only button — use for toolbar actions.

    Examples:
        close  = IconButton(Symbol.CLOSE)
        reset  = IconButton(Symbol.RESET)
        rescan = IconButton(f"{Symbol.REFRESH}  Rescan")
    """

    def __init__(self, text: str, size: int = t.H_BTN_MD, parent: "QWidget | None" = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("icon-btn")
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)


# ══════════════════════════════════════════════════════════════════
# SELECTORS
# ══════════════════════════════════════════════════════════════════

class PillSelector(QWidget):
    """
    A PillButton that opens a styled QMenu when clicked.
    Emits selected(data) when the user picks an item.

    This is the correct pattern for channel, DLC, baudrate, and interval
    selectors — use instead of QComboBox for consistent Hyva styling.

    Examples:
        ch = PillSelector("Select channel")
        ch.add_option("PCAN_USBBUS1 — 250 kbps", data=channel_obj)
        ch.add_option("PCAN_USBBUS2 — 250 kbps", data=channel_obj2)
        ch.selected.connect(self._on_channel_selected)

        # Check current selection
        current = ch.current_data()

        # Update label programmatically
        ch.set_label("PCAN_USBBUS1 — 250 kbps")

    Signal:
        selected(object) — emitted with the data object passed to add_option()
    """

    # Emits the data object attached to the selected menu item
    selected = Signal(object)

    def __init__(
        self,
        label:  str,
        width:  int | None = None,
        height: int = t.H_BTN_MD,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        self._current_data = None
        self._options: list[tuple[str, object]] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._btn = PillButton(label, width=width, height=height)
        self._btn.clicked.connect(self._show_menu)
        layout.addWidget(self._btn)

    def add_option(self, label: str, data: object = None) -> None:
        """
        Add one item to the dropdown menu.

        Args:
            label: Text shown in the menu.
            data:  Any Python object — emitted with selected() signal.
                   Can be a string, a CanChannel object, an int — anything.

        Example:
            selector.add_option("PCAN_USBBUS1 — 250 kbps", data=channel)
            selector.add_option("8", data=8)
        """
        self._options.append((label, data))

    def add_separator(self) -> None:
        """Add a visual separator line between groups of options."""
        self._options.append(("__sep__", None))

    def add_group_header(self, text: str) -> None:
        """
        Add a non-selectable section header inside the menu.

        Example:
            dlc_sel.add_group_header("── Classical CAN / J1939 ──")
            for v in range(9):
                dlc_sel.add_option(str(v), data=v)
        """
        self._options.append(("__hdr__" + text, None))

    def set_label(self, text: str) -> None:
        """Update the pill button label (e.g. after a selection is made)."""
        self._btn.setText(text)

    def current_data(self) -> object:
        """Return the data object of the currently selected item."""
        return self._current_data

    def _show_menu(self) -> None:
        """Build and show the styled dropdown menu below the pill."""
        menu = QMenu(self._btn)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t.BG_PAGE};
                border: 1px solid {t.YELLOW};
                border-radius: {t.RADIUS_MD}px;
                padding: 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: {t.TEXT_BRIGHT};
                padding: 6px 20px 6px 12px;
                font-size: {t.SIZE_MD}px;
            }}
            QMenu::item:selected {{
                background-color: {t.BG_HOVER_YELLOW};
                color: {t.YELLOW};
            }}
            QMenu::item:checked {{
                color: {t.YELLOW};
                font-weight: bold;
            }}
        """)

        for label, data in self._options:
            if label == "__sep__":
                menu.addSeparator()
            elif label.startswith("__hdr__"):
                action = menu.addAction(label[7:])   # strip __hdr__ prefix
                action.setEnabled(False)
            else:
                action = menu.addAction(label)
                action.setData(data)
                action.setCheckable(True)
                action.setChecked(data == self._current_data)

        pos    = self._btn.mapToGlobal(self._btn.rect().bottomLeft())
        chosen = menu.exec(pos)
        if chosen is None:
            return   # user dismissed the menu without selecting

        self._current_data = chosen.data()
        logger.debug(f"[COMPONENT] PillSelector: selected '{chosen.text()}'")
        self.selected.emit(self._current_data)


class RadioGroup(QWidget):
    """
    A horizontal row of styled radio buttons.
    Use for mutually exclusive choices (e.g. frame type selection).

    Examples:
        frame_type = RadioGroup(["Standard", "Extended (29-bit)", "J1939"])
        frame_type.changed.connect(self._on_type_changed)

        # Read current selection (0-indexed)
        idx = frame_type.checked_index()

        # Set programmatically
        frame_type.set_index(2)    # select "J1939"

    Signal:
        changed(int) — emitted with the index of the selected option.
    """

    changed = Signal(int)

    def __init__(self, options: list[str], parent: "QWidget | None" = None) -> None:
        from PySide6.QtWidgets import QButtonGroup
        super().__init__(parent)
        self._group = QButtonGroup(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(t.SPACE_LG)

        for i, text in enumerate(options):
            rb = _StyledRadio(text, self)
            self._group.addButton(rb, i)
            layout.addWidget(rb)

        if options:
            self._group.button(0).setChecked(True)

        self._group.idClicked.connect(self.changed.emit)

    def checked_index(self) -> int:
        """Return the 0-based index of the selected option."""
        return self._group.checkedId()

    def checked_text(self) -> str:
        """Return the text of the selected option."""
        btn = self._group.checkedButton()
        return btn.text() if btn else ""

    def set_index(self, index: int) -> None:
        """Select an option by its 0-based index."""
        btn = self._group.button(index)
        if btn:
            btn.setChecked(True)


class _StyledRadio(QWidget):
    """
    A single radio button styled for the Hyva dark theme.
    Used internally by RadioGroup — not needed directly.
    """

    def __init__(self, text: str, parent: "QWidget | None" = None) -> None:
        # We wrap QRadioButton in a widget so QSS objectName styling applies
        from PySide6.QtWidgets import QRadioButton
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        rb = QRadioButton(text)
        rb.setObjectName("FrameTypeRb")
        layout.addWidget(rb)
        self._rb = rb

    def setChecked(self, checked: bool) -> None:
        self._rb.setChecked(checked)

    def isChecked(self) -> bool:
        return self._rb.isChecked()

    def text(self) -> str:
        return self._rb.text()


# ══════════════════════════════════════════════════════════════════
# INPUTS
# ══════════════════════════════════════════════════════════════════

class TextField(QLineEdit):
    """
    A dark text input field.

    Examples:
        arb_id  = TextField(placeholder="0x18FF0063")
        comment = TextField(placeholder="Optional note", width=200)

    Full Qt API works:
        value = arb_id.text()
        arb_id.setText("0x100")
        arb_id.textChanged.connect(my_fn)
        arb_id.setEnabled(False)
    """

    def __init__(
        self,
        placeholder: str = "",
        width:  int | None = None,
        height: int = t.H_INPUT,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("field")
        self.setFixedHeight(height)
        self.setPlaceholderText(placeholder)
        if width is not None:
            self.setFixedWidth(width)


class IntField(TextField):
    """
    A text input that only accepts integers within a given range.

    Examples:
        interval = IntField(min_val=10, max_val=60000,
                           placeholder="500", width=72)
        port     = IntField(min_val=1, max_val=65535, placeholder="18200")

    Reads like a normal QLineEdit:
        ms = int(interval.text())
    """

    def __init__(
        self,
        min_val:     int = 0,
        max_val:     int = 99999,
        placeholder: str = "",
        width:  int | None = None,
        height: int = t.H_INPUT,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(placeholder=placeholder, width=width, height=height, parent=parent)
        self.setValidator(QIntValidator(min_val, max_val, self))


class FloatField(TextField):
    """
    A text input that only accepts decimal numbers.

    Examples:
        gain   = FloatField(min_val=0.0, max_val=10.0, placeholder="1.0")
        offset = FloatField(min_val=-100.0, max_val=100.0)
    """

    def __init__(
        self,
        min_val:     float = 0.0,
        max_val:     float = 99999.0,
        decimals:    int = 3,
        placeholder: str = "",
        width:  int | None = None,
        height: int = t.H_INPUT,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(placeholder=placeholder, width=width, height=height, parent=parent)
        validator = QDoubleValidator(min_val, max_val, decimals, self)
        self.setValidator(validator)


class HexField(TextField):
    """
    A text input for space-separated hex bytes.
    Accepts: 0-9, A-F, a-f, and spaces.

    Examples:
        data = HexField(placeholder="00 64 32 00")
        arb  = HexField(placeholder="0x18FF0063", width=200)
    """

    def __init__(
        self,
        placeholder: str = "",
        width:  int | None = None,
        height: int = t.H_INPUT,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(placeholder=placeholder, width=width, height=height, parent=parent)
        from PySide6.QtGui import QRegularExpressionValidator
        from PySide6.QtCore import QRegularExpression
        # Allow: hex chars, spaces, 0x prefix, uppercase enforced by textChanged
        validator = QRegularExpressionValidator(
            QRegularExpression(r"[0-9A-Fa-fx ]*"),
            self,
        )
        self.setValidator(validator)
        # Auto-uppercase as user types
        self.textChanged.connect(self._to_upper)

    def _to_upper(self, text: str) -> None:
        """Convert input to uppercase without moving the cursor."""
        upper = text.upper()
        if upper != text:
            pos = self.cursorPosition()
            self.blockSignals(True)
            self.setText(upper)
            self.setCursorPosition(pos)
            self.blockSignals(False)


# ══════════════════════════════════════════════════════════════════
# LABELS & TEXT
# ══════════════════════════════════════════════════════════════════

class SectionLabel(QLabel):
    """
    Small dim uppercase label above an input or selector.
    Use to label what a field or picker is for.

    Examples:
        layout.addWidget(SectionLabel("CHANNEL"))
        layout.addWidget(channel_picker)

        layout.addWidget(SectionLabel("INTERVAL"))
        layout.addWidget(interval_input)
    """

    def __init__(self, text: str, parent: "QWidget | None" = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("section-label")


class ValueLabel(QLabel):
    """
    Monospace label for displaying live values, addresses, or hex data.

    Examples:
        addr  = ValueLabel("0x18FF0063")
        speed = ValueLabel("1200 rpm")

        # Update live
        addr.setText(f"0x{arb_id:08X}")
    """

    def __init__(self, text: str = "—", parent: "QWidget | None" = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("value-label")
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)


class StatusLabel(QLabel):
    """
    A coloured status / feedback label.
    Automatically prepends a tick (✓) for ok and cross (✕) for error.

    Examples:
        status = StatusLabel()                    # empty at first
        layout.addWidget(status)

        # In your logic:
        status.set_ok("Sent on PCAN_USBBUS1")     # → green "✓ Sent on PCAN_USBBUS1"
        status.set_error("No channel selected")   # → red   "✕ No channel selected"
        status.clear()                             # → empty (hidden)
    """

    def __init__(self, text: str = "", parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(t.H_BTN_XS)
        if text:
            self.set_ok(text)
        else:
            self.clear()

    def set_ok(self, message: str) -> None:
        """Show a green success message with a tick prefix."""
        self.setText(f"{Symbol.CHECK}  {message}")
        self.setObjectName("status-ok")
        self._repolish()

    def set_error(self, message: str) -> None:
        """Show a red error message with a cross prefix."""
        self.setText(f"{Symbol.CROSS}  {message}")
        self.setObjectName("status-err")
        self._repolish()

    def set_plain(self, message: str, colour: str = "") -> None:
        """
        Show a message with no automatic prefix or colour.
        Optionally pass a hex colour string.
        """
        self.setText(message)
        self.setObjectName("")
        if colour:
            self.setStyleSheet(
                f"color: {colour}; font-size: {t.SIZE_SM}px; background: transparent;"
            )
        else:
            self.setStyleSheet(
                f"color: {t.TEXT_DIM}; font-size: {t.SIZE_SM}px; background: transparent;"
            )

    def clear(self) -> None:
        """Remove the message and hide the label."""
        self.setText("")
        self.setObjectName("")
        self.setStyleSheet(
            f"font-size: {t.SIZE_SM}px; background: transparent; color: {t.TEXT_DIM};"
        )

    def _repolish(self) -> None:
        """Force Qt to re-apply the stylesheet after objectName changes."""
        self.style().unpolish(self)
        self.style().polish(self)


class BadgeLabel(QLabel):
    """
    A small coloured pill-shaped label for counts and states.

    Examples:
        badge = BadgeLabel("2 ch connected", colour=theme.TEXT_DIM)
        badge = BadgeLabel("PRESENT",        colour=theme.GREEN)
        badge = BadgeLabel("NO CAN",         colour=theme.RED)
    """

    def __init__(self, text: str = "", colour: str = "", parent: "QWidget | None" = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("badge")
        if colour:
            self.setStyleSheet(
                f"color: {colour}; font-size: {t.SIZE_XS}px; "
                f"letter-spacing: {t.TRACKING_TIGHT}; background: transparent;"
            )


# ══════════════════════════════════════════════════════════════════
# CARDS & PANELS
# ══════════════════════════════════════════════════════════════════

class Card(QWidget):
    """
    Dark panel with a coloured top accent stripe and optional header.

    Use Card.create() — it returns the card widget AND its content layout.
    Add your widgets to the content layout.

    Examples:
        # Basic card with header
        card, layout = Card.create("BUILD & SEND", icon_fa=Fa.SEND)
        layout.addWidget(my_widget)
        parent_layout.addWidget(card)

        # Card with custom accent colour
        card, layout = Card.create("CAN NODES",
                                   icon_fa=Fa.NETWORK,
                                   accent=theme.YELLOW_DIM)

        # Card with no header (content only)
        card, layout = Card.create()

    The card widget itself is a standard QWidget — all Qt methods work:
        card.setVisible(False)
        card.setSizePolicy(...)
    """

    @staticmethod
    def create(
        title:       str = "",
        icon_fa:     str = "",
        icon_symbol: str = "",
        accent:      str = "",
        bg:          str = "",
        parent: "QWidget | None" = None,
    ) -> tuple["Card", QVBoxLayout]:
        """
        Create a card and return (card_widget, content_layout).

        Args:
            title:       Header text (e.g. "BUILD & SEND"). Empty = no header.
            icon_fa:     Font Awesome icon name (e.g. Fa.SEND = "paper-plane").
            icon_symbol: Unicode fallback (e.g. Symbol.SEND).
            accent:      Top stripe colour. Default = theme.YELLOW.
            bg:          Card background. Default = theme.BG_CARD.
            parent:      Qt parent widget.

        Returns:
            (card_widget, content_layout)
            Add your widgets to content_layout.
        """
        accent = accent or t.YELLOW
        bg     = bg     or t.BG_CARD

        card = Card(parent=parent)
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            Card {{
                background-color: {bg};
                border: 1px solid {t.BORDER_FAINT};
                border-top: 2px solid {accent};
                border-radius: {t.RADIUS_LG}px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(t.SPACE_MD, t.SPACE_MD, t.SPACE_MD, t.SPACE_MD)
        outer.setSpacing(t.SPACE_SM)

        if title:
            hdr = QHBoxLayout()
            hdr.setSpacing(t.SPACE_SM)
            hdr.setContentsMargins(0, 0, 0, 0)

            if icon_fa or icon_symbol:
                icon = IconWidget(
                    fa=icon_fa or None,
                    fallback=icon_symbol or None,
                    colour=accent,
                    size=t.SIZE_LG,
                )
                hdr.addWidget(icon)

            lbl = QLabel(title)
            lbl.setObjectName("card-title")
            lbl.setStyleSheet(
                f"color: {accent}; font-size: {t.SIZE_MD}px; "
                f"letter-spacing: {t.TRACKING_WIDE}; font-weight: bold; "
                f"background: transparent;"
            )
            hdr.addWidget(lbl)
            hdr.addStretch()
            outer.addLayout(hdr)

            outer.addWidget(HSep())

        return card, outer


class SubCard(QWidget):
    """
    Lighter nested panel — use inside a Card for sub-sections.

    Examples:
        sub, layout = SubCard.create()
        layout.addWidget(my_widget)
    """

    @staticmethod
    def create(
        bg:     str = "",
        parent: "QWidget | None" = None,
    ) -> tuple["SubCard", QVBoxLayout]:
        """Create a sub-card. Returns (sub_card_widget, content_layout)."""
        bg = bg or t.BG_CARD_DEEP

        card = SubCard(parent=parent)
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            SubCard {{
                background-color: {bg};
                border: 1px solid {t.BORDER_FAINT};
                border-radius: {t.RADIUS_MD}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(t.SPACE_MD, t.SPACE_SM, t.SPACE_MD, t.SPACE_SM)
        layout.setSpacing(t.SPACE_SM)

        return card, layout


class InfoRow(QWidget):
    """
    A label : value pair for displaying key-value information.
    Used in Device Details, node status, etc.

    Examples:
        row = InfoRow("GW VERSION", "1.2.3.4")
        row = InfoRow("SA", "0x63")

        # Update the value
        row.set_value("1.2.3.5")
        row.set_value("—")           # clear
        row.set_value("ERROR", ok=False)    # red value
    """

    def __init__(self, label: str, value: str = "—", parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(t.SPACE_SM)

        self._lbl = QLabel(label)
        self._lbl.setStyleSheet(
            f"color: {t.TEXT_MUTED}; font-size: {t.SIZE_SM}px; "
            f"letter-spacing: {t.TRACKING_NORMAL}; background: transparent;"
        )

        self._val = ValueLabel(value)

        layout.addWidget(self._lbl)
        layout.addStretch()
        layout.addWidget(self._val)

    def set_value(self, text: str, ok: bool = True) -> None:
        """Update the value text. Pass ok=False for red error colour."""
        self._val.setText(text)
        colour = t.TEXT_MID if ok else t.TEXT_RED
        self._val.setStyleSheet(
            f"color: {colour}; font-size: {t.SIZE_MD}px; "
            f"font-family: {t.FONT_MONO}; background: transparent;"
        )


# ══════════════════════════════════════════════════════════════════
# NAVIGATION  (existing components — refactored for this toolkit)
# ══════════════════════════════════════════════════════════════════

class PageTitleBar(QWidget):
    """
    Reusable page header: pill with icon + title text + optional separator.

    Add this at the top of every page.

    The icon is looked up automatically from PAGE_ICONS using the page name.
    You can also pass icon_fa and icon_fallback explicitly for custom pages.

    Parameters
    ----------
    page : str
        Page title displayed in the pill (e.g. ``"HOME"``, ``"CAN TOOLS"``).
    icon_fa : str, optional
        Font Awesome icon name override (e.g. ``Fa.SEND``).
    icon_fallback : str, optional
        Unicode fallback icon override.
    show_separator : bool, default True
        When *True* (the default) a full-width ``HSep`` is appended below the
        pill inside this widget.  Set to *False* when embedding
        ``PageTitleBar`` inside a horizontal row that already has other
        widgets alongside it — in that case add a standalone ``HSep()``
        **outside** the row in the parent layout so the line spans the full
        page width rather than just the width of the title pill column.

    Examples
    --------
    Standalone (separator included automatically — the normal case)::

        root.addWidget(PageTitleBar("HOME"))
        root.addWidget(PageTitleBar("SENSORS"))

    Embedded in a row alongside another widget (suppress internal separator,
    add an explicit full-width one below)::

        header_row = QHBoxLayout()
        header_row.addWidget(PageTitleBar("CAN", show_separator=False), stretch=1)
        header_row.addWidget(tools_btn, stretch=0, alignment=Qt.AlignVCenter)
        root.addLayout(header_row)
        root.addWidget(HSep())   # ← full-width, spans both columns
    """

    def __init__(
        self,
        page:           str,
        icon_fa:        str = "",
        icon_fallback:  str = "",
        show_separator: bool = True,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        logger.debug(
            f"[UI] PageTitleBar: page='{page}' show_separator={show_separator}"
        )

        # Auto-lookup icon from PAGE_ICONS if not supplied explicitly
        if not icon_fa and not icon_fallback:
            fa_sym = PAGE_ICONS.get(page)
            if fa_sym:
                icon_fa, icon_fallback = fa_sym[0], fa_sym[1]
            else:
                icon_fallback = Symbol.DIAMOND
        elif not icon_fallback:
            icon_fallback = Symbol.DIAMOND

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(t.SPACE_XS)

        # ── Title pill ────────────────────────────────────────────
        pill = QWidget()
        pill.setObjectName("PageTitlePill")
        pill.setAttribute(Qt.WA_StyledBackground, True)
        pill.setFixedHeight(t.H_PAGE_TITLE_PILL)
        pill.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        pill_row = QHBoxLayout(pill)
        pill_row.setContentsMargins(t.SPACE_MD, 0, t.SPACE_LG, 0)
        pill_row.setSpacing(t.SPACE_SM)

        icon = IconWidget(
            fa=icon_fa or None,
            fallback=icon_fallback,
            colour=t.YELLOW,
            size=t.SIZE_MD,
        )
        pill_row.addWidget(icon)

        title = QLabel(page)
        title.setObjectName("PanelTitle")
        pill_row.addWidget(title)
        pill_row.addStretch()

        col.addWidget(pill)

        # ── Optional separator ────────────────────────────────────
        # Included by default for standalone usage.
        # Suppressed when the caller places this bar inside an HBoxLayout
        # alongside other widgets, where a separate full-width HSep must be
        # added by the caller in the parent vertical layout.
        if show_separator:
            col.addWidget(HSep())
            logger.debug(f"[UI] PageTitleBar '{page}': internal HSep added")


class BackButton(GhostButton):
    """
    A ← back / navigation button.
    Turns red on hover to signal "leaving this context".

    Examples:
        back = BackButton("CAN")          # renders "← CAN"
        back = BackButton("Back to Home") # renders "← Back to Home"
        back.clicked.connect(self._go_home)
    """

    def __init__(self, destination: str, parent: "QWidget | None" = None) -> None:
        super().__init__(
            text=f"{Symbol.BACK}  {destination}",
            height=t.H_BTN_MD,
            radius=t.RADIUS_PILL,
            parent=parent,
        )


# ══════════════════════════════════════════════════════════════════
# STATUS PILLS  (footer connection indicators)
# ══════════════════════════════════════════════════════════════════

class NodePill(QWidget):
    """
    Footer connection status pill.

    Four visual states:
      checking     — amber dot, "CHECKING" sub-text   (startup, not yet polled)
      disconnected — red dot, optional sub-text
      present      — green dot, "PRESENT" or baudrate sub-text
      simulated    — green half-dot, "SIMULATED" sub-text

    Examples:
        pill = NodePill("pcan_usbbus1", "PCAN_USBBUS1", sub="250 kbps")
        pill.set_connected(True)          # turns green "PRESENT"
        pill.set_connected(False)         # turns red, sub shows "NO CAN"
        pill.set_node_state("simulated")  # green half-dot "SIMULATED"
        pill.set_checking()               # amber "CHECKING"
    """

    def __init__(
        self,
        node_id: str,
        label:   str,
        sub:     str = "",
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        self._node_id   = node_id
        self._saved_sub = sub

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("NodePill")
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(9, 5, 11, 5)
        outer.setSpacing(1)
        outer.setAlignment(Qt.AlignVCenter)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(5)
        top_row.setAlignment(Qt.AlignVCenter)

        self._dot = IconWidget(fa=Fa.DOT, fallback=Symbol.DOT_FULL,
                               colour=t.RED, size=8)
        self._dot.setFixedSize(10, 10)
        top_row.addWidget(self._dot, 0, Qt.AlignVCenter)

        self._label_lbl = QLabel(label)
        self._label_lbl.setStyleSheet(
            f"color: {t.TEXT_BRIGHT}; font-size: {t.SIZE_SM}px; "
            f"letter-spacing: {t.TRACKING_TIGHT}; background: transparent;"
        )
        self._label_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        top_row.addWidget(self._label_lbl, 0, Qt.AlignVCenter)
        outer.addLayout(top_row)

        self._sub_lbl = QLabel(sub)
        self._sub_lbl.setObjectName("PillSub")
        self._sub_lbl.setAlignment(Qt.AlignLeft)
        self._sub_lbl.setStyleSheet(
            f"color: {t.TEXT_MID}; font-size: {t.SIZE_XS}px; "
            f"letter-spacing: {t.TRACKING_TIGHT}; "
            f"background: transparent; margin-left: 12px;"
        )
        self._sub_lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        outer.addWidget(self._sub_lbl)

        # Start in amber "CHECKING" state
        self._set_checking()

    # ── Public API ────────────────────────────────────────────────

    def set_checking(self) -> None:
        """Revert to amber CHECKING state (e.g. on reconnect attempts)."""
        self._set_checking()

    def set_connected(self, connected: bool) -> None:
        """Switch between connected (green) and disconnected (red) states."""
        if connected:
            self._set_present()
            self._sub_lbl.setText(self._saved_sub)
            self._sub_lbl.setStyleSheet(
                f"color: {t.TEXT_MID}; font-size: {t.SIZE_XS}px; "
                f"letter-spacing: {t.TRACKING_TIGHT}; "
                f"background: transparent; margin-left: 12px;"
            )
        else:
            self._set_disconnected()
            if self._saved_sub:
                self._sub_lbl.setText("NO CAN")
                self._sub_lbl.setStyleSheet(
                    f"color: {t.RED}; font-size: {t.SIZE_XS}px; "
                    f"letter-spacing: {t.TRACKING_TIGHT}; "
                    f"background: transparent; margin-left: 12px;"
                )
            else:
                self._sub_lbl.setText("")

    def set_node_state(self, state: str) -> None:
        """
        Set state by name.

        Args:
            state: "present", "simulated", or "disconnected"
        """
        if state == "present":
            self._set_present()
            self._sub_lbl.setText("PRESENT")
            self._sub_lbl.setStyleSheet(
                f"color: {t.TEXT_NODE_PRESENT}; font-size: {t.SIZE_XS}px; "
                f"letter-spacing: {t.TRACKING_TIGHT}; background: transparent;"
            )
        elif state == "simulated":
            self._set_simulated()
            self._sub_lbl.setText("SIMULATED")
            self._sub_lbl.setStyleSheet(
                f"color: {t.GREEN}; font-size: {t.SIZE_XS}px; "
                f"letter-spacing: {t.TRACKING_TIGHT}; background: transparent;"
            )
        else:
            self._set_disconnected()
            self._sub_lbl.setText("")

    def update_sub(self, text: str) -> None:
        """Update the sub-text label (e.g. baudrate) and remember it."""
        self._saved_sub = text
        self._sub_lbl.setText(text)
        self._sub_lbl.setStyleSheet(
            f"color: {t.TEXT_MID}; font-size: {t.SIZE_XS}px; "
            f"letter-spacing: {t.TRACKING_TIGHT}; "
            f"background: transparent; margin-left: 12px;"
        )

    # ── Private visual states ─────────────────────────────────────

    def _set_checking(self) -> None:
        self._dot.set_colour(t.YELLOW_DIM)
        self._label_lbl.setStyleSheet(
            f"color: {t.TEXT_DIM}; font-size: {t.SIZE_SM}px; "
            f"letter-spacing: {t.TRACKING_TIGHT}; background: transparent;"
        )
        self.setStyleSheet(f"""
            NodePill {{
                background-color: {t.BG_PILL_NEUTRAL};
                border: 1px solid {t.BORDER_FAINT};
                border-radius: {t.RADIUS_MD}px;
            }}
        """)
        self._sub_lbl.setText("CHECKING")
        self._sub_lbl.setStyleSheet(
            f"color: {t.YELLOW_DIM}; font-size: {t.SIZE_XS}px; "
            f"letter-spacing: {t.TRACKING_TIGHT}; "
            f"background: transparent; margin-left: 12px;"
        )

    def _set_disconnected(self) -> None:
        self._dot.set_colour(t.RED)
        self._label_lbl.setStyleSheet(
            f"color: {t.TEXT_BRIGHT}; font-size: {t.SIZE_SM}px; "
            f"letter-spacing: {t.TRACKING_TIGHT}; background: transparent;"
        )
        self.setStyleSheet(f"""
            NodePill {{
                background-color: {t.BG_PILL_NEUTRAL};
                border: 1px solid {t.BORDER_FAINT};
                border-radius: {t.RADIUS_MD}px;
            }}
        """)

    def _set_present(self) -> None:
        self._dot.set_colour(t.GREEN)
        self._label_lbl.setStyleSheet(
            f"color: {t.TEXT_BRIGHT}; font-size: {t.SIZE_SM}px; "
            f"letter-spacing: {t.TRACKING_TIGHT}; background: transparent;"
        )
        self.setStyleSheet(f"""
            NodePill {{
                background-color: {t.BG_PILL_PRESENT};
                border: 1px solid {t.BORDER_NODE_PRESENT};
                border-radius: {t.RADIUS_MD}px;
            }}
        """)

    def _set_simulated(self) -> None:
        self._dot.set_colour(t.GREEN)
        self._label_lbl.setStyleSheet(
            f"color: {t.GREEN}; font-size: {t.SIZE_SM}px; "
            f"letter-spacing: {t.TRACKING_TIGHT}; background: transparent;"
        )
        self.setStyleSheet(f"""
            NodePill {{
                background-color: {t.BG_PILL_SIMULATED};
                border: 1px solid {t.BORDER_NODE_SIMUL};
                border-radius: {t.RADIUS_MD}px;
            }}
        """)


# ══════════════════════════════════════════════════════════════════
# DISPLAY
# ══════════════════════════════════════════════════════════════════

class DataTable(QTableWidget):
    """
    Styled dark read-only table with row selection.
    Use for CAN monitor, file browser, log viewer, RPC call log.

    Examples:
        table = DataTable(columns=["ARB ID", "DATA", "DLC", "TYPE"])
        table.add_row(["0x18FF0063", "04 14 64 F0", "8", "EXT"])
        table.row_selected.connect(self._on_row)

        # Clear all rows
        table.clear_rows()

        # Read a row
        row_data = table.get_row(0)    # list of strings

    Signal:
        row_selected(int) — emitted with the row index when user clicks a row.
    """

    row_selected = Signal(int)

    def __init__(self, columns: list[str], parent: "QWidget | None" = None) -> None:
        super().__init__(0, len(columns), parent)
        self.setObjectName("MonTable")
        self.setHorizontalHeaderLabels(columns)

        # Standard table configuration
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)

        # Wire row click to signal
        self.itemSelectionChanged.connect(self._on_selection)

    def add_row(self, values: list[str], colours: list[str] | None = None) -> None:
        """
        Append a row to the table.

        Args:
            values:  List of strings, one per column.
            colours: Optional list of hex colour strings for each cell.
                     Pass None for a cell to use the default colour.

        Example:
            table.add_row(
                ["0x18FF0063", "04 14 64 F0", "8", "EXT"],
                colours=["#FFD100", None, None, "#FCD34D"],
            )
        """
        row = self.rowCount()
        self.insertRow(row)
        for col, text in enumerate(values):
            item = QTableWidgetItem(str(text))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if colours and col < len(colours) and colours[col]:
                from PySide6.QtGui import QColor
                item.setForeground(QColor(colours[col]))
            self.setItem(row, col, item)
        self.setRowHeight(row, 22)

    def clear_rows(self) -> None:
        """Remove all rows from the table."""
        self.setRowCount(0)

    def get_row(self, row_index: int) -> list[str]:
        """Return the string values of all cells in a row."""
        return [
            (self.item(row_index, col).text()
             if self.item(row_index, col) else "")
            for col in range(self.columnCount())
        ]

    def _on_selection(self) -> None:
        row = self.currentRow()
        if row >= 0:
            self.row_selected.emit(row)


# ══════════════════════════════════════════════════════════════════
# LAYOUT HELPERS
# ══════════════════════════════════════════════════════════════════

class HSep(QWidget):
    """
    Thin horizontal separator line between sections.

    Cross-platform note: uses QWidget not QFrame — QFrame(HLine)
    renders white on Windows with some Qt styles.

    Example:
        layout.addWidget(HSep())
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setObjectName("h-sep")
        self.setAttribute(Qt.WA_StyledBackground, True) 
        self.setFixedHeight(t.H_SEP)
        self.setStyleSheet(f"background-color: {t.BORDER_STRONG}; border: none;")


class VSep(QWidget):
    """
    Thin vertical separator line between columns.

    Example:
        row_layout.addWidget(VSep())
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setObjectName("v-sep")
        self.setFixedWidth(t.H_SEP)
        self.setStyleSheet(f"background-color: {t.BORDER_FAINT}; border: none;")


class RedSepH(QWidget):
    """
    Hyva red horizontal separator — used below the top header.

    Args:
        height: Separator height in pixels. Default is 2.
                Pass height=3 for the main header separator.

    Cross-platform: uses QWidget not QFrame — QFrame(HLine)
    renders white on Windows with some Qt styles.
    WA_StyledBackground is required so Qt paints the background
    colour from the stylesheet on Windows/Fusion style.

    Examples:
        layout.addWidget(RedSepH())           # 2px
        layout.addWidget(RedSepH(height=3))   # 3px (main header)
    """

    def __init__(self, height: int = 2, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setObjectName("red-sep-h")
        # WA_StyledBackground: required on Windows/Fusion — without it Qt
        # will NOT paint the background-color from the stylesheet.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(height)
        self.setStyleSheet(f"background-color: {t.RED}; border: none;")


class RedSepV(QWidget):
    """
    Hyva red vertical separator — used between sidebar and content.

    This is the prominent red stripe that visually divides the sidebar
    navigation from the main content area.  It runs the FULL HEIGHT of
    the content area because it is placed in the same QHBoxLayout as the
    sidebar and the QStackedWidget, both of which have Expanding vertical
    size policy.

    Cross-platform note: WA_StyledBackground is required so Qt paints
    the background colour from the stylesheet on Windows/Fusion style.
    Without it, the widget renders as a transparent gap.

    Example:
        mid_row.addWidget(RedSepV())
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setObjectName("red-sep-v")
        # WA_StyledBackground: required on Windows/Fusion — without it Qt
        # will NOT paint the background-color from the stylesheet.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(2)
        self.setStyleSheet(f"background-color: {t.RED}; border: none;")
