"""
download_fonts.py

Downloads Inter (UI font) and JetBrains Mono (monospace font) into assets/fonts/.
Called automatically by setup.py. Can also be run manually.

WHY THIS EXISTS
  The 4 Liberation fonts (already bundled in assets/fonts/) are the primary fonts
  and work on all platforms with zero downloads. This script adds Inter and
  JetBrains Mono on top for even crisper text — optional, not required.

WHY THE OLD INTER URLS BROKE
  The rsms/inter GitHub repo restructured in v4.0. Font files are no longer
  available as individual raw files. They now live inside a release ZIP.
  Fix: download the ZIP and extract what we need.
"""

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Inter v4.0 — GitHub release ZIP (only correct way to get TTF in v4.0+)
INTER_ZIP_URL  = "https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip"
# Variable font covers all weights (Regular/Medium/SemiBold/Bold) in one file
# The ZIP root contains TTFs directly — NO subfolder (confirmed from actual zip contents)
INTER_ZIP_FILES = {
    "InterVariable.ttf": "InterVariable.ttf",
}
# We also extract individual static TTFs for broader Qt compat
INTER_STATIC_FILES = {
    "Inter-Regular.ttf":  "extras/ttf/Inter-Regular.ttf",
    "Inter-Medium.ttf":   "extras/ttf/Inter-Medium.ttf",
    "Inter-SemiBold.ttf": "extras/ttf/Inter-SemiBold.ttf",
    "Inter-Bold.ttf":     "extras/ttf/Inter-Bold.ttf",
}

# JetBrains Mono — direct TTF, URL is stable
DIRECT_TTF = {
    "JetBrainsMono-Regular.ttf": (
        "https://github.com/JetBrains/JetBrainsMono"
        "/raw/v2.304/fonts/ttf/JetBrainsMono-Regular.ttf"
    ),
}


def _download_inter() -> bool:
    needed = [FONTS_DIR / n for n in {**INTER_ZIP_FILES, **INTER_STATIC_FILES}]
    if all(p.exists() for p in needed):
        for p in needed:
            print(f"  \u2713  {p.name} (already present)")
        return True

    print(f"  \u2193  Downloading Inter v4.0 ZIP ...")
    try:
        with urllib.request.urlopen(INTER_ZIP_URL, timeout=60) as resp:
            data = resp.read()
        print(f"  \u2193  Extracting from ZIP ({len(data) // 1024} KB) ...")
        all_files = {**INTER_ZIP_FILES, **INTER_STATIC_FILES}
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for dest_name, zip_path in all_files.items():
                dest = FONTS_DIR / dest_name
                if dest.exists():
                    print(f"  \u2713  {dest_name} (already present)")
                    continue
                try:
                    dest.write_bytes(zf.read(zip_path))
                    print(f"  \u2713  {dest_name} ({dest.stat().st_size // 1024} KB)")
                except KeyError:
                    print(f"  \u2717  {dest_name} not found at {zip_path!r} inside ZIP")
                    return False
        return True
    except Exception as ex:
        print(f"  \u2717  Inter download failed: {ex}")
        return False


def _download_direct(filename: str, url: str) -> bool:
    dest = FONTS_DIR / filename
    if dest.exists():
        print(f"  \u2713  {filename} (already present)")
        return True
    try:
        print(f"  \u2193  Downloading {filename} ...")
        urllib.request.urlretrieve(url, dest)
        print(f"  \u2713  {filename} ({dest.stat().st_size // 1024} KB)")
        return True
    except Exception as ex:
        print(f"  \u2717  {filename} — failed: {ex}")
        return False


def download_fonts() -> bool:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    results = [_download_inter()]
    for name, url in DIRECT_TTF.items():
        results.append(_download_direct(name, url))

    if all(results):
        print("\n  All extra fonts downloaded.")
    else:
        print("\n  Some fonts failed. App will use Liberation Sans (bundled). Works fine.")
    return all(results)


if __name__ == "__main__":
    print("\n[ Downloading extra fonts ]\n")
    sys.exit(0 if download_fonts() else 1)
