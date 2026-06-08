"""
simulator/gui/constants.py

Single source of truth for GUI-wide constants.

Import from here — never define these inline in page or widget files.
All duplicates across pages/ and widgets/ have been removed in favour
of this module.
"""

from pathlib import Path

# Project root — three levels up from this file:
#   simulator/gui/constants.py → simulator/gui/ → simulator/ → project root
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

# Sidebar pixel width.  Both Sidebar and FooterBar use this to keep
# the left column aligned.
SIDEBAR_WIDTH: int = 200

# CAN baud-rate choices shown in drop-downs.
# Add new entries here; all pages pick them up automatically.
BAUDRATE_OPTIONS: list[tuple[str, int]] = [
    ("125 kbps",  125_000),
    ("250 kbps",  250_000),
    ("500 kbps",  500_000),
    ("1 Mbps",  1_000_000),
]
