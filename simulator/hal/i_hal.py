"""
i_hal.py

Interface for the Hardware Abstraction Layer (HAL).

Every concrete HAL must implement the three lifecycle methods below.
No other responsibilities belong here — hardware-specific behaviour lives
entirely in the concrete implementation (NoHal, RaspberryPiHal, …).

Ignition relay / K15 control is handled exclusively by IgnitionController
(simulator/ign/ignition_controller.py) — the HAL does NOT expose pin-level
write methods.  This separation keeps the HAL focused on lifecycle only.

Introduced in v0.2.0 — HAL system:
  IHal (this file)       — interface definition
  NoHal                  — stub for Windows / Linux desktop (no GPIO)
  RaspberryPiHal         — GPIO chip lifecycle on Raspberry Pi (gpiod)
"""

from interface import Interface


class IHal(Interface):
    """
    Hardware Abstraction Layer interface.

    Implement start(), stop(), and join() in every concrete HAL class.
    The simulator calls them in this order:

        hal.start()   ← simulator starts up
        ...running...
        hal.stop()    ← user closes window / Ctrl-C
        hal.join()    ← wait for background threads (if any) to finish
    """

    def start(self) -> None:
        """Called once at startup. Initialise hardware resources here."""
        pass

    def stop(self) -> None:
        """Called on shutdown. Release hardware resources here."""
        pass

    def join(self) -> None:
        """Block until any background hardware threads have finished."""
        pass
