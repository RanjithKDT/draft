"""
raspi_hal.py

Hardware Abstraction Layer for Raspberry Pi.

Controls physical GPIO using the gpiod library (Linux kernel GPIO character
device API).  Works on Pi 4, Pi 5, and Revolution Pi (RevPi).

Lifecycle only (start / stop / join):
  The HAL owns the GPIO chip lifecycle.
  Ignition pin control is handled exclusively by IgnitionController via
  _GpioBackend — see simulator/ign/ignition_controller.py.

Lazy import:
  gpiod is only imported when RaspberryPiHal is instantiated so Windows and
  Linux desktop imports never fail even if gpiod is not installed.
"""

from interface import implements
from loguru import logger

from simulator.hal.i_hal import IHal


class RaspberryPiHal(implements(IHal)):
    """
    Raspberry Pi HAL — manages GPIO chip lifecycle only.

    gpio_chip: name of the GPIO character device to open (e.g. 'gpiochip0').
               Resolved by platform_detector and passed in from hal_factory.
               Defaults to 'gpiochip0' which is the main chip on Pi 4 / Pi 5.

    Actual pin writes are done by IgnitionController._GpioBackend.
    This class only verifies that gpiod can open the chip at startup so
    any configuration error is caught immediately with a clear log message.
    """

    def __init__(self, gpio_chip: str = "gpiochip0") -> None:
        self._gpio_chip_name = gpio_chip

    # ── IHal lifecycle ─────────────────────────────────────────────

    def start(self) -> None:
        """
        Verify the GPIO chip is accessible at startup.
        Does not acquire any pins — IgnitionController does that separately.
        """
        logger.info(
            f"RaspberryPiHal: starting — chip={self._gpio_chip_name}"
        )
        self._verify_chip()
        logger.info(
            "RaspberryPiHal: started — pin control via IgnitionController"
        )

    def stop(self) -> None:
        """No resources to release — pins are owned by IgnitionController."""
        logger.debug("RaspberryPiHal: stopped")

    def join(self) -> None:
        """No background threads — nothing to join."""
        pass

    # ── Private helpers ────────────────────────────────────────────

    def _verify_chip(self) -> None:
        """
        Open and immediately close the GPIO chip to confirm it is accessible.
        Logs a warning (does not raise) if the chip cannot be opened — the
        simulator continues in software-only mode in that case.
        """
        try:
            import gpiod
            chip = gpiod.Chip(f"/dev/{self._gpio_chip_name}")
            num_lines = chip.num_lines()
            chip.close()
            logger.info(
                f"RaspberryPiHal: GPIO chip '{self._gpio_chip_name}' "
                f"verified — {num_lines} lines available"
            )
        except ImportError:
            logger.warning(
                "RaspberryPiHal: gpiod not installed — GPIO unavailable. "
                "Install with: pip install gpiod"
            )
        except Exception as ex:
            logger.warning(
                f"RaspberryPiHal: could not open GPIO chip "
                f"'{self._gpio_chip_name}': {ex} — "
                "add user to 'gpio' group or run with sudo"
            )
