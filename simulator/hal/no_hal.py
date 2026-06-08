"""
no_hal.py

Stub HAL — used on Windows and Linux desktop where there is no GPIO hardware.

Accepts all lifecycle calls and does nothing, allowing the simulator to run
in full software-only mode.  Ignition control is handled exclusively by
IgnitionController (simulator/ign/ignition_controller.py).
"""

from interface import implements
from loguru import logger

from simulator.hal.i_hal import IHal


class NoHal(implements(IHal)):
    """
    Software-only HAL stub.

    All three IHal methods are implemented as no-ops.
    start() logs a single INFO line so the operator knows which HAL is active.
    """

    def start(self) -> None:
        logger.info("HAL: NoHal — software-only mode (no GPIO)")

    def stop(self) -> None:
        logger.debug("HAL: NoHal stopped")

    def join(self) -> None:
        logger.debug("HAL: NoHal join (no background threads)")
