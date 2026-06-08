"""
main.py

Entry point for Hyva Simulator v2.0.5.

Usage:
    python main.py                          Auto-detect platform, open GUI
    python main.py --no-gui                 Run headless (no window)
    python main.py --can-channel can1       Override CAN channel
"""

import argparse
import sys
from loguru import logger

from simulator.platform.platform_detector import detect
from simulator.platform.hal_factory import create_hal
from simulator.simulator import Simulator


def setup_logger() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "{message}"
        ),
        colorize=True,
        level="DEBUG",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hyva Simulator")
    parser.add_argument("--no-gui",      action="store_true", help="Run headless")
    parser.add_argument("--can-channel", type=str, default=None,
                        help="Override CAN channel (e.g. can1, PCAN_USBBUS2)")
    return parser.parse_args()


def main() -> None:
    setup_logger()
    args = parse_args()

    from simulator.gui._version import APP_VERSION as _VER

    logger.info("=" * 60)
    logger.info(f"  Hyva Simulator  v{_VER}")
    logger.info(f"  Python          {sys.version.split()[0]}")
    logger.info(f"  Mode            {'Headless (no GUI)' if args.no_gui else 'GUI'}")
    logger.info("=" * 60)

    profile = detect()

    logger.info(f"Platform  : {profile.hardware_description}")
    logger.info(f"OS label  : {profile.display_label}")
    logger.info(f"CAN back  : {profile.can_backend.value}  channel={profile.can_channel}")
    logger.info(f"HAL type  : {profile.hal_type.name}")

    if args.can_channel:
        profile.can_channel = args.can_channel
        logger.info(f"CAN channel overridden → '{args.can_channel}'")

    hal = create_hal(profile)

    Simulator(
        profile = profile,
        hal     = hal,
        no_gui  = args.no_gui,
    ).start()


if __name__ == "__main__":
    main()
