"""
simulator/gui/pages
===================
QStackedWidget page classes. Import directly from each module as needed.

Available modules:
    home_page        — HomePage, _ProductPage, _PingWorker, _FetchWorker, _DeviceRow
    can_page         — CanChannelCard, CanMonitorWidget, CanPage
    can_tools_page   — CanToolsPage
    sensors_page     — _SensorCard, SensorsPage
    calibration_page — CalibrationPage
    playback_page    — PlaybackPage
    rpc_page         — RpcPage
    settings_page    — _SettingsSubPage, _RaspiSettingsPage, HyvaProductsPage,
                       _CreditsDialog, AboutPage, _GeneralSettingsPage,
                       _WindowsSettingsPage, _LinuxSettingsPage, SettingsLandingPage
"""
# No eager imports here — each page file imports independently to avoid
# circular dependencies through main_window.py ↔ pages/__init__.py.
