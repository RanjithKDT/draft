"""
hal_factory.py

Returns the correct HAL instance for the current platform.

Selection logic (unchanged since v0.2.0):
  HalType.RASPBERRY_PI  →  RaspberryPiHal  (requires gpiod on the Pi)
  HalType.NONE          →  NoHal           (Windows, Linux desktop, macOS)

RaspberryPiHal is imported lazily here so gpiod is never required on
Windows or Linux desktop — missing gpiod does not crash the import.

If gpiod is not installed or the GPIO chip cannot be opened, the factory
falls back to NoHal and logs a clear warning so the operator knows why
hardware control is disabled.
"""

from loguru import logger

from simulator.hal.i_hal import IHal
from simulator.hal.no_hal import NoHal
from simulator.platform.platform_detector import HalType, PlatformProfile


def create_hal(profile: PlatformProfile) -> IHal:
    """
    Return the correct HAL for the detected platform.

    Args:
        profile: PlatformProfile produced by platform_detector.detect().

    Returns:
        An IHal instance — either RaspberryPiHal or NoHal.
    """
    if profile.hal_type == HalType.RASPBERRY_PI:
        return _create_raspi_hal(profile)

    logger.info("HAL: NoHal (no GPIO hardware on this platform)")
    return NoHal()


# ── Private factory helpers ───────────────────────────────────────


def _create_raspi_hal(profile: PlatformProfile) -> IHal:
    """
    Try to create RaspberryPiHal.
    Falls back to NoHal if gpiod is missing or GPIO chip is inaccessible.
    """
    gpio_chip = profile.gpio_chip or "gpiochip0"
    try:
        # Lazy import — gpiod must NOT be imported at module level so Windows
        # and Linux desktop imports never fail.
        from simulator.hal.raspi_hal import RaspberryPiHal

        logger.info(f"HAL: RaspberryPiHal (GPIO chip: {gpio_chip})")
        return RaspberryPiHal(gpio_chip=gpio_chip)

    except ImportError:
        logger.warning(
            "HAL: gpiod not installed — falling back to NoHal. "
            "Install with: pip install gpiod"
        )
    except Exception as ex:
        logger.warning(
            f"HAL: RaspberryPiHal init failed ({ex}) — falling back to NoHal"
        )

    logger.info("HAL: NoHal (fallback — GPIO unavailable)")
    return NoHal()
