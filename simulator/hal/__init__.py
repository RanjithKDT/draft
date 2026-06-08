"""
simulator/hal/__init__.py

HAL package — Hardware Abstraction Layer.

Public API (introduced in v0.2.0, current as of v2.0.5):
  IHal          — interface every HAL must implement
  NoHal         — stub for Windows / Linux desktop (no GPIO)
  RaspberryPiHal — GPIO chip lifecycle on Raspberry Pi (gpiod required)

Use hal_factory.create_hal(profile) to get the right HAL automatically.
"""

from simulator.hal.i_hal import IHal
from simulator.hal.no_hal import NoHal

__all__ = ["IHal", "NoHal"]