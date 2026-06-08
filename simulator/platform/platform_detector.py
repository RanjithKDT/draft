"""
platform_detector.py

Detects which OS the simulator is running on and returns a PlatformProfile.
This is the only file that does OS detection — everything else just reads the profile.

Call detect() once at startup. Pass the result to hal_factory.
"""

import os
import re
import sys
import platform
from dataclasses import dataclass
from enum import Enum, auto
from loguru import logger


class OperatingSystem(Enum):
    WINDOWS      = auto()
    LINUX        = auto()
    RASPBERRY_PI = auto()


class CanBackend(Enum):
    PCAN      = "pcan"       # Windows + PCAN-USB adapter
    SOCKETCAN = "socketcan"  # Linux / Raspberry Pi
    VIRTUAL   = "virtual"    # No hardware (fallback)


class HalType(Enum):
    NONE         = auto()   # No GPIO (Windows, Linux desktop)
    RASPBERRY_PI = auto()   # GPIO available on a Raspberry Pi


@dataclass
class PlatformProfile:
    """Holds everything the simulator needs to know about the current machine."""
    operating_system:     OperatingSystem
    can_backend:          CanBackend
    hal_type:             HalType
    can_channel:          str        # e.g. "PCAN_USBBUS1" or "can0"
    gpio_chip:            str | None # e.g. "gpiochip0", or None if no GPIO
    hardware_description: str        # Full description for logs
    display_label:        str        # Short label for the GUI footer e.g. "WINDOWS 11"


# Files that only exist on Linux / Raspberry Pi
_RASPI_MODEL_FILE = "/sys/firmware/devicetree/base/model"
_GPIO_INFO_FILE   = "/sys/kernel/debug/gpio"


def _read_raspi_model() -> str | None:
    """Read the Raspberry Pi model name. Returns None if not on a Pi."""
    try:
        with open(_RASPI_MODEL_FILE) as f:
            return f.read().replace("\x00", "").strip()
    except FileNotFoundError:
        return None
    except Exception as ex:
        logger.warning(f"Could not read Pi model file: {ex}")
        return None


def _read_gpio_chip() -> str | None:
    """
    Find the GPIO chip name for the Pi's pinctrl controller.

    Strategy:
      1. Parse /sys/kernel/debug/gpio (requires root on some kernels).
      2. Fall back to checking /dev/gpiochip0 … /dev/gpiochip3 directly —
         readable by any user who is in the 'gpio' group, which is the
         default on Raspberry Pi OS.  gpiochip0 is always the main chip on Pi 4/5.
    """
    # --- attempt 1: kernel debug fs (root or relaxed kernel) ---
    try:
        with open(_GPIO_INFO_FILE) as f:
            for line in f:
                if "pinctrl" in line:
                    chip = line.split(":")[0].strip()
                    logger.debug(f"GPIO chip from debug fs: {chip}")
                    return chip
    except FileNotFoundError:
        pass
    except PermissionError:
        logger.debug("No permission to read GPIO debug fs — trying /dev/gpiochipN fallback")
    except Exception as ex:
        logger.warning(f"Could not read GPIO info: {ex}")

    # --- attempt 2: probe /dev/gpiochip* directly (works without root) ---
    for n in range(4):
        chip_path = f"/dev/gpiochip{n}"
        if os.path.exists(chip_path):
            logger.debug(f"GPIO chip found via /dev: gpiochip{n}")
            return f"gpiochip{n}"

    logger.warning(
        "GPIO chip not found — add user to 'gpio' group or run with sudo to enable GPIO"
    )
    return None


def _build_display_label(os: OperatingSystem, raspi_model: str | None = None) -> str:
    """
    Build a short display string for the GUI footer.
    Examples: "WINDOWS 11", "UBUNTU 22.04", "RASPBERRY PI 4 MODEL B"
    """
    if os == OperatingSystem.WINDOWS:
        return f"WINDOWS {platform.release()}"

    if os == OperatingSystem.RASPBERRY_PI and raspi_model:
        # Remove the revision suffix e.g. "Rev 1.2" to keep it short
        short = re.sub(r"\s+Rev\s+[\d.]+$", "", raspi_model, flags=re.IGNORECASE)
        return short.upper()

    # Linux — read the distro name and version from /etc/os-release
    try:
        name = ""
        version = ""
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("NAME="):
                    name = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("VERSION_ID="):
                    version = line.split("=", 1)[1].strip().strip('"')
        if name:
            return f"{name} {version}".strip().upper()
    except Exception as ex:
        logger.debug(f"[PLATFORM] Could not read /etc/os-release: {ex}")

    # Fallback — use the kernel version
    return f"LINUX {platform.release().split('-')[0].upper()}"


def detect() -> PlatformProfile:
    """
    Detect the current platform and return a PlatformProfile.

    Order of checks:
      1. Windows  → sys.platform == "win32"
      2. Linux    → check if it is a Raspberry Pi via device tree
      3. Other    → fallback to virtual CAN
    """
    logger.info("Detecting platform...")

    if sys.platform == "win32":
        profile = PlatformProfile(
            operating_system     = OperatingSystem.WINDOWS,
            can_backend          = CanBackend.PCAN,
            hal_type             = HalType.NONE,
            can_channel          = "PCAN_USBBUS1",
            gpio_chip            = None,
            hardware_description = f"Windows {platform.release()} — PCAN-USB, no GPIO",
            display_label        = _build_display_label(OperatingSystem.WINDOWS),
        )

    elif sys.platform.startswith("linux"):
        raspi_model = _read_raspi_model()
        gpio_chip   = _read_gpio_chip()

        if raspi_model and "Raspberry Pi" in raspi_model:
            profile = PlatformProfile(
                operating_system     = OperatingSystem.RASPBERRY_PI,
                can_backend          = CanBackend.SOCKETCAN,
                hal_type             = HalType.RASPBERRY_PI if gpio_chip else HalType.NONE,
                can_channel          = "can0",
                gpio_chip            = gpio_chip,
                hardware_description = (
                    f"{raspi_model} — SocketCAN"
                    + (" + GPIO" if gpio_chip else ", GPIO unavailable")
                ),
                display_label        = _build_display_label(
                    OperatingSystem.RASPBERRY_PI, raspi_model
                ),
            )
        else:
            profile = PlatformProfile(
                operating_system     = OperatingSystem.LINUX,
                can_backend          = CanBackend.SOCKETCAN,
                hal_type             = HalType.NONE,
                can_channel          = "can0",
                gpio_chip            = None,
                hardware_description = f"Linux {platform.release()} — SocketCAN, no GPIO",
                display_label        = _build_display_label(OperatingSystem.LINUX),
            )

    elif sys.platform == "darwin":
        # macOS — developer / CI machine; no PCAN driver, no GPIO
        logger.warning("macOS detected — no PCAN driver or GPIO; using virtual CAN (dev/CI only)")
        profile = PlatformProfile(
            operating_system     = OperatingSystem.LINUX,   # treated as Linux-like
            can_backend          = CanBackend.VIRTUAL,
            hal_type             = HalType.NONE,
            can_channel          = "virtual_0",
            gpio_chip            = None,
            hardware_description = f"macOS {platform.mac_ver()[0]} — virtual CAN (no hardware)",
            display_label        = f"MACOS {platform.mac_ver()[0]}",
        )

    else:
        logger.warning(f"Unsupported OS: {sys.platform} — falling back to virtual CAN")
        profile = PlatformProfile(
            operating_system     = OperatingSystem.LINUX,
            can_backend          = CanBackend.VIRTUAL,
            hal_type             = HalType.NONE,
            can_channel          = "virtual_0",
            gpio_chip            = None,
            hardware_description = f"Unsupported OS ({sys.platform}) — virtual CAN",
            display_label        = sys.platform.upper(),
        )

    logger.info(f"Platform  : {profile.hardware_description}")
    logger.info(f"HAL       : {profile.hal_type.name}")

    return profile
