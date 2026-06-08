================================================================================
pyLucidIo Version 2.5 (bundled)
================================================================================

OVERVIEW
========
Python 3.x API for LucidControl USB IO Modules.

(C) 2008 - 2025 deciphe it GmbH

CHANGES FROM v2.2 → v2.5
=========================
- Architecture refactored: shared base classes introduced
    LucidControlAO  → base for LucidControlAO4, LucidControlAO8
    LucidControlAI  → base for LucidControlAI4, LucidControlAI8
- New modules added: LucidControlAI8, LucidControlAO8, LucidControlDI16,
    LucidControlDO16, LucidControlDI4DO4
- API rename in Values.py: _setData()/_getData() → setData()/getData()
- Python 3 only (Python 2 support removed)
- MIT License

MODULES IN THIS BUNDLE
======================
Core:
  Cmd.py, Com.py, IoReturn.py, LucidControl.py, LucidControlId.py, Values.py

Analog Output (AOVO):
  LucidControlAO.py   - base class
  LucidControlAO4.py  - 4-channel analog output (0-10V) ← used by simulator IGN
  LucidControlAO8.py  - 8-channel analog output

Analog Input (AIVO):
  LucidControlAI.py   - base class
  LucidControlAI4.py  - 4-channel analog input (24V)
  LucidControlAI8.py  - 8-channel analog input

Digital:
  LucidControlDI.py, LucidControlDI4.py, LucidControlDI8.py
  LucidControlDI16.py, LucidControlDI4DO4.py
  LucidControlDO.py, LucidControlDO4.py, LucidControlDO8.py, LucidControlDO16.py

RTD (Temperature):
  LucidControlRT.py, LucidControlRT4.py, LucidControlRT8.py

PRODUCT PAGES
=============
AI4 (AIVO - Analogue Input, 24V, 4-channel):
  https://www.lucid-control.com/product/lucidcontrol-ai4-4-channel-analog-input-usb-module/

AO4 (AOVO - Analogue Output, 0-10V, 4-channel):
  https://www.lucid-control.com/product/lucidcontrol-ao4-4-channel-analog-output-usb-module/

Downloads page:
  https://www.lucid-control.com/downloads/

SUPPORT
=======
support@lucid-control.com
https://www.lucid-control.com
