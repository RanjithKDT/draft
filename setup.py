"""
setup.py

Hyva Simulator — one-shot environment setup.

What it does:
  1. Detects the OS  (Windows / Linux / Raspberry Pi)
  2. Checks Python version (3.12+ required)
  3. Creates a virtual environment at .venv/ if one does not exist
  4. Upgrades pip inside the venv
  5. Installs all packages from requirements.txt
  6. On Windows: installs pywin32 + wmi (Windows-only extras)
  7. Prints an activation command so the user can enable the venv

Run once before first use:
    Windows   : python setup.py
    Linux/RasPi: python3 setup.py

After setup completes, activate the venv and run the simulator:
    Windows    : .venv\\Scripts\\activate  →  python main.py
    Linux/RasPi: source .venv/bin/activate  →  python main.py
"""

import os
import re
import sys
import shutil
import platform
import subprocess
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────

MIN_PYTHON = (3, 12)   # matches requirements.txt "Python 3.12 required"
VENV_DIR   = Path(__file__).resolve().parent / ".venv"
REQ_FILE   = Path(__file__).resolve().parent / "requirements.txt"

# Windows-only packages (not in requirements.txt because they fail on Linux)
WINDOWS_EXTRAS = ["pywin32", "wmi"]

# ANSI colours (disabled on Windows unless ANSICON / Windows Terminal is present)
_USE_COLOR = sys.platform != "win32" or os.environ.get("WT_SESSION")

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

def ok(msg: str):    print(_c("32", f"    {msg}"))
def info(msg: str):  print(_c("36", f"    {msg}"))
def warn(msg: str):  print(_c("33", f"    {msg}"))
def step(msg: str):  print(_c("1;37", f"\n[ {msg} ]"))
def fail(msg: str):
    print(_c("31", f"\n    {msg}"))
    sys.exit(1)


# ── OS detection ──────────────────────────────────────────────────

def detect_os() -> str:
    """Return 'windows', 'raspberry_pi', or 'linux'."""
    if sys.platform == "win32":
        return "windows"
    model_path = Path("/sys/firmware/devicetree/base/model")
    if model_path.exists():
        try:
            model = model_path.read_text(errors="replace").lower()
            if "raspberry pi" in model:
                return "raspberry_pi"
        except OSError:
            pass
    return "linux"


OS = detect_os()

OS_LABELS = {
    "windows":      "Windows",
    "linux":        "Linux",
    "raspberry_pi": "Raspberry Pi",
}


# ── Python version check ──────────────────────────────────────────

def check_python() -> None:
    step("Checking Python version")
    v = sys.version_info
    info(f"Running Python {v.major}.{v.minor}.{v.micro}")
    if (v.major, v.minor) < MIN_PYTHON:
        fail(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required.\n"
            f"       You have {v.major}.{v.minor}.{v.micro}.\n"
            f"       On Raspberry Pi run:  python3.12 setup.py\n"
            f"       Download from https://www.python.org/downloads/"
        )
    ok(f"Python {v.major}.{v.minor}.{v.micro} — OK")


# ── Venv paths ────────────────────────────────────────────────────

def venv_python() -> Path:
    if OS == "windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_pip() -> Path:
    if OS == "windows":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def activate_cmd() -> str:
    if OS == "windows":
        return str(VENV_DIR / "Scripts" / "activate.bat")
    return "source " + str(VENV_DIR / "bin" / "activate")


# ── Venv creation ─────────────────────────────────────────────────

def create_venv() -> None:
    step("Virtual environment")

    if VENV_DIR.exists() and venv_python().exists():
        ok(f"venv already exists at {VENV_DIR}")
        return

    if VENV_DIR.exists():
        warn(f"Stale venv directory found at {VENV_DIR} — removing")
        shutil.rmtree(VENV_DIR)

    info(f"Creating venv at {VENV_DIR} ...")
    _run([sys.executable, "-m", "venv", str(VENV_DIR)],
         fail_msg="Failed to create virtual environment")
    ok("venv created")


# ── Pip upgrade ───────────────────────────────────────────────────

def upgrade_pip() -> None:
    step("Upgrading pip")
    _run(
        [str(venv_python()), "-m", "pip", "install", "--upgrade", "pip"],
        fail_msg="pip upgrade failed",
    )
    ok("pip up-to-date")


# ── Requirements install ──────────────────────────────────────────

def install_requirements() -> None:
    step("Installing requirements.txt")

    if not REQ_FILE.exists():
        fail(f"requirements.txt not found at {REQ_FILE}")

    # Strip comment lines and blank lines so we can show package count
    lines = [
        l.strip() for l in REQ_FILE.read_text().splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    info(f"Installing {len(lines)} package(s) from {REQ_FILE.name}")

    _run(
        [str(venv_python()), "-m", "pip", "install", "-r", str(REQ_FILE)],
        fail_msg="Package installation failed",
    )
    ok("All packages installed")


# ── Windows extras ────────────────────────────────────────────────

def install_windows_extras() -> None:
    if OS != "windows":
        return
    step("Installing Windows extras (pywin32, wmi)")
    _run(
        [str(venv_python()), "-m", "pip", "install"] + WINDOWS_EXTRAS,
        fail_msg="Windows extras install failed",
    )
    ok("Windows extras installed")


# ── Raspberry Pi system deps check ───────────────────────────────

def check_raspi_deps() -> None:
    if OS != "raspberry_pi":
        return
    step("Checking Raspberry Pi system packages")

    # SocketCAN: ip command must exist
    if shutil.which("ip"):
        ok("iproute2 (ip command) — found")
    else:
        warn("iproute2 not found — install with:  sudo apt install iproute2")

    # GPIO: gpiod is optional — only needed if GPIO features are used
    try:
        result = subprocess.run(
            ["dpkg", "-s", "gpiod"],
            capture_output=True, text=True
        )
        if "Status: install ok" in result.stdout:
            ok("gpiod — found")
        else:
            warn("gpiod not installed — GPIO features disabled.\n"
                 "         Install with:  sudo apt install gpiod python3-gpiod")
    except FileNotFoundError:
        warn("Could not check gpiod (dpkg not available)")


# ── Subprocess helper ─────────────────────────────────────────────

def _run(cmd: list, fail_msg: str):
    """Run a subprocess; stream output; exit on failure."""
    try:
        result = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as ex:
        fail(f"{fail_msg}\n       Exit code: {ex.returncode}")
    except FileNotFoundError as ex:
        fail(f"{fail_msg}\n       Command not found: {ex}")


# ── Summary ───────────────────────────────────────────────────────

def print_summary() -> None:
    print()
    print(_c("1;32", "  ══════════════════════════════════════════"))
    print(_c("1;32", "    Setup complete!"))
    print(_c("1;32", "  ══════════════════════════════════════════"))
    print()
    print(_c("1;37", "  Platform  :"), OS_LABELS[OS])
    print(_c("1;37", "  Venv      :"), str(VENV_DIR))
    print()
    print(_c("1;37", "  Next steps:"))
    print()

    # Pre-assign to avoid backslash-inside-f-string (Python < 3.12 restriction)
    activate  = _c("33", activate_cmd())
    run_cmd   = _c("33", "python main.py")

    if OS == "windows":
        start_script = _c("33", r"scripts\start-windows.bat")
        print("    1.  Activate venv   →   " + activate)
        print("    2.  Run simulator   →   " + run_cmd)
        print()
        print("    Or use the start script:")
        print("        " + start_script)
    else:
        start_script = _c("33", "bash scripts/start-linux.sh")
        print("    1.  Activate venv   →   " + activate)
        print("    2.  Run simulator   →   " + run_cmd)
        print()
        print("    Or use the start script:")
        print("        " + start_script)

    if OS == "raspberry_pi":
        can_cmd = _c("33", "sudo ip link set can0 up type can bitrate 250000")
        print()
        print("    Note: bring up the CAN interface before running:")
        print("        " + can_cmd)

    print()


# ── Entry point ───────────────────────────────────────────────────

def main() -> None:
    print()
    print(_c("1;33", "  ══════════════════════════════════════════"))
    print(_c("1;33", "    Hyva Simulator — Environment Setup"))
    print(_c("1;33", "  ══════════════════════════════════════════"))
    print(f"  Detected OS  :  {_c('36', OS_LABELS[OS])}")
    print(f"  Venv target  :  {VENV_DIR}")
    print()

    check_python()
    create_venv()
    upgrade_pip()
    install_requirements()
    install_windows_extras()
    check_raspi_deps()
    print_summary()


if __name__ == "__main__":
    main()
