from __future__ import annotations

"""
gw_client.py

SSH connection to the Gateway (172.16.0.1) to fetch device version info.

Auth strategy — automatic, in order:
  1. Key-file auth with passphrase
       Windows : assets/keys/id_gateway.ppk  + GW_PASSPHRASE
       Linux/Pi: assets/keys/id_gateway_pem  + GW_PASSPHRASE
     If the GW host key has changed (REMOTE HOST IDENTIFICATION HAS CHANGED):
       → stale known_hosts entry is cleared automatically (ssh-keygen -R 172.16.0.1)
       → connection is retried once with the same key and passphrase
  2. Password auth with GW_PASSWORD (fallback for any key-auth failure)

Both credentials have hardcoded defaults that match the testbench configuration.
Override either via environment variable when the GW credentials change:
    export GW_PASSPHRASE=<new_passphrase>
    export GW_PASSWORD=<new_password>

Remote file read:
    ~/data/osp.core.preferences/hyva.fota.app.properties
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

from simulator.config import GW_HOST, GW_PORT, GW_USER


# ── Credentials ───────────────────────────────────────────────────

# Key passphrase — override via env var.  No hardcoded default in source.
# Set before running: export GW_PASSPHRASE=<passphrase>
GW_PASSPHRASE: str = os.environ.get("GW_PASSPHRASE", "")
if not GW_PASSPHRASE:
    logger.warning(
        "[SSH] GW_PASSPHRASE env var not set — key auth will fail if the key has a passphrase. "
        "Set with: export GW_PASSPHRASE=<passphrase>"
    )

# SSH password fallback — override via env var.  No hardcoded default.
# Set before running: export GW_PASSWORD=<password>
GW_PASSWORD: str = os.environ.get("GW_PASSWORD", "")
if not GW_PASSWORD:
    logger.warning(
        "[SSH] GW_PASSWORD env var not set — password auth fallback will not work. "
        "Set with: export GW_PASSWORD=<password>"
    )

CONNECT_TIMEOUT = 10   # seconds

REMOTE_FILE = "data/osp.core.preferences/hyva.fota.app.properties"

_PROJECT_ROOT    = Path(__file__).resolve().parent.parent.parent
_KEYS_DIR        = _PROJECT_ROOT / "assets" / "keys"
KEY_FILE_WINDOWS = _KEYS_DIR / "id_gateway.ppk"
KEY_FILE_LINUX   = _KEYS_DIR / "id_gateway_pem"


# ── Result type ───────────────────────────────────────────────────

@dataclass
class DeviceInfo:
    gw_version:          str = "—"
    hmi_version:         str = "—"
    release_version:     str = "—"
    original_gw_version: str = "—"


# ── Key file selection ────────────────────────────────────────────

def _select_key_file(is_windows: bool | None = None) -> Path | None:
    """
    Return the correct key file for this OS, or None if the file does not exist.

    is_windows comes from PlatformProfile (authoritative).
    Falls back to sys.platform when called without a profile.
    """
    if is_windows is None:
        is_windows = sys.platform == "win32"

    key_path = KEY_FILE_WINDOWS if is_windows else KEY_FILE_LINUX

    if key_path.exists():
        logger.debug(f"[SSH] Key file: {key_path.name}")
        return key_path

    logger.warning(f"[SSH] Key file not found: {key_path} — will skip key auth")
    return None


# ── Key loading ───────────────────────────────────────────────────

def _available_pem_classes(paramiko_mod: object) -> list[type]:
    """
    Return available PEM key classes from this paramiko version.

    Uses getattr so that classes removed in newer paramiko versions
    (DSSKey removed in 3.0) are silently skipped — no AttributeError
    before the first key type is even attempted.
    """
    available = []
    for name in ("Ed25519Key", "RSAKey", "ECDSAKey", "DSSKey"):
        cls = getattr(paramiko_mod, name, None)
        if cls is not None:
            available.append(cls)
        else:
            logger.debug(f"[SSH] paramiko.{name} not in this version — skipped")
    return available


def _load_key(paramiko_mod: object, path: Path, passphrase: str) -> "paramiko.PKey | None":
    """
    Load a private key from path using the given passphrase.

    PPK (.ppk) → paramiko.PKey.from_path (paramiko 3.x)
    PEM        → Ed25519Key / RSAKey / ECDSAKey / DSSKey (tried in order)

    Returns the loaded key object.
    Raises ValueError with a clear message if no format succeeds.
    """
    # ── PPK (PuTTY) format ─────────────────────────────────────
    if path.suffix.lower() == ".ppk":
        from_path_fn = getattr(paramiko_mod.PKey, "from_path", None)
        if from_path_fn is None:
            raise ValueError(
                f"Cannot load {path.name}: PPK requires paramiko >= 3.0. "
                "Run: pip install --upgrade paramiko"
            )
        try:
            key = from_path_fn(str(path), passphrase=passphrase)
            logger.debug(f"[SSH] Loaded PPK key from {path.name}")
            return key
        except Exception as ex:
            raise ValueError(f"Could not load PPK key from {path.name}: {ex}") from ex

    # ── PEM formats (Ed25519, RSA, ECDSA; DSS on older paramiko) ─
    last_error = ""
    for key_class in _available_pem_classes(paramiko_mod):
        try:
            key = key_class.from_private_key_file(str(path), password=passphrase)
            logger.debug(f"[SSH] Loaded {key_class.__name__} from {path.name}")
            return key
        except Exception as ex:
            last_error = str(ex)
            logger.debug(f"[SSH] {key_class.__name__} load failed: {ex}")

    raise ValueError(f"Could not load key from {path.name}: {last_error}")


# ── Host key handling ─────────────────────────────────────────────

def _clear_stale_host_key(hostname: str) -> None:
    """
    Remove the stale known_hosts entry for hostname.
    Equivalent to: ssh-keygen -R <hostname>

    Called automatically when BadHostKeyException is raised, which happens
    when the GW's SSH host key has changed (firmware update, swap, etc.).
    After clearing, the next connect() will accept the new host key.
    """
    known_hosts = Path.home() / ".ssh" / "known_hosts"
    if not known_hosts.exists():
        logger.debug(f"[SSH] No known_hosts file — nothing to clear for {hostname}")
        return
    try:
        lines = known_hosts.read_text(errors="replace").splitlines(keepends=True)
        kept = [
            line for line in lines
            if not line.startswith(hostname) and not line.startswith(f"[{hostname}]")
        ]
        removed = len(lines) - len(kept)
        known_hosts.write_text("".join(kept))
        logger.info(
            f"[SSH] Cleared {removed} stale known_hosts entry/entries for {hostname} "
            f"(equivalent to: ssh-keygen -R {hostname})"
        )
    except Exception as ex:
        logger.warning(f"[SSH] Could not update known_hosts for {hostname}: {ex}")


def _make_client(paramiko_mod: object) -> "paramiko.SSHClient":
    """
    Return a fresh SSHClient with AutoAddPolicy.
    AutoAddPolicy accepts new host keys automatically.
    We never load system host keys so the client always starts clean.
    """
    client = paramiko_mod.SSHClient()
    client.set_missing_host_key_policy(paramiko_mod.AutoAddPolicy())
    return client


# ── Low-level connect — handles host key change automatically ─────

def _do_connect(paramiko_mod: object, **kwargs: object) -> "paramiko.SSHClient":
    """
    Create a fresh SSHClient, connect, return the connected client.

    Handles BadHostKeyException (GW host key changed) by:
      1. Logging a clear warning.
      2. Clearing the stale known_hosts entry (ssh-keygen -R equivalent).
      3. Creating another fresh client and retrying once.

    A fresh client is used for every attempt to prevent transport state
    from a previous failure contaminating the next attempt.

    Raises on second failure (i.e. does not swallow all errors).
    """
    bad_host_key_cls = getattr(paramiko_mod, "BadHostKeyException", None)

    client = _make_client(paramiko_mod)
    try:
        client.connect(**kwargs)
        return client
    except Exception as ex:
        if bad_host_key_cls and isinstance(ex, bad_host_key_cls):
            logger.warning(
                f"[SSH] GW host key has changed (REMOTE HOST IDENTIFICATION HAS CHANGED). "
                f"Clearing stale entry and retrying — ({ex})"
            )
            _clear_stale_host_key(GW_HOST)
            fresh_client = _make_client(paramiko_mod)
            fresh_client.connect(**kwargs)   # raises if still failing
            return fresh_client
        raise


# ── Auth strategy 1: key + passphrase ────────────────────────────

def _try_key_auth(paramiko_mod: object, key_path: Path) -> "paramiko.SSHClient | None":
    """
    Connect using the key file + GW_PASSPHRASE.

    BadHostKeyException (host key changed) is handled inside _do_connect:
      → stale entry cleared → connection retried automatically.

    Returns the connected client on success, None on failure.
    """
    logger.info(
        f"[SSH] Key auth → {GW_USER}@{GW_HOST}:{GW_PORT} [{key_path.name}]"
    )
    try:
        pkey = _load_key(paramiko_mod, key_path, GW_PASSPHRASE)
        client = _do_connect(
            paramiko_mod,
            hostname      = GW_HOST,
            port          = GW_PORT,
            username      = GW_USER,
            pkey          = pkey,
            timeout       = CONNECT_TIMEOUT,
            allow_agent   = False,
            look_for_keys = False,
        )
        logger.info("[SSH] Key auth succeeded")
        return client
    except ValueError as ex:
        # _load_key raises ValueError — key file problem (format, corrupt, wrong passphrase)
        logger.warning(f"[SSH] Key load failed: {ex}")
    except Exception as ex:
        logger.warning(f"[SSH] Key auth failed: {ex}")

    return None


# ── Auth strategy 2: password fallback ───────────────────────────

def _try_password_auth(paramiko_mod: object) -> "paramiko.SSHClient | None":
    """
    Connect using GW_PASSWORD as a last-resort fallback.

    Some GW firmware versions have PasswordAuthentication=no (publickey only).
    When the server rejects the password method or immediately resets the TCP
    connection, a clear diagnostic message is logged instead of the raw
    'Error reading SSH protocol banner [Errno 104]' that paramiko emits.

    Returns the connected client on success, None on failure.
    """
    logger.info(f"[SSH] Password auth → {GW_USER}@{GW_HOST}:{GW_PORT}")
    try:
        client = _do_connect(
            paramiko_mod,
            hostname      = GW_HOST,
            port          = GW_PORT,
            username      = GW_USER,
            password      = GW_PASSWORD,
            timeout       = CONNECT_TIMEOUT,
            allow_agent   = False,
            look_for_keys = False,
        )
        logger.info("[SSH] Password auth succeeded")
        return client
    except Exception as ex:
        ex_lower = str(ex).lower()
        if (
            "publickey"            in ex_lower
            or "bad authentication" in ex_lower
            or "connection reset"   in ex_lower
            or "banner"             in ex_lower
        ):
            logger.warning(
                "[SSH] GW rejected password auth — firmware only allows publickey. "
                "Ensure the key file and passphrase are correct."
            )
        else:
            logger.warning(f"[SSH] Password auth failed: {ex}")
        return None


# ── Remote file read and parser ───────────────────────────────────

def _read_remote_file(client: "paramiko.SSHClient") -> str:
    """
    Execute `cat ~/REMOTE_FILE` on the GW and return its content.

    Reads stdout and stderr via the channel directly instead of calling
    stdout.read() then stderr.read() sequentially.  The sequential pattern
    can deadlock when the remote process writes enough to stderr to fill
    the SSH pipe buffer before stdout is fully consumed.
    """
    _, stdout, stderr = client.exec_command(
        f"cat ~/{REMOTE_FILE}", timeout=CONNECT_TIMEOUT
    )
    channel = stdout.channel

    # Wait for the remote command to finish (respects the channel timeout).
    channel.recv_exit_status()

    content = stdout.read().decode("utf-8", errors="replace")
    error   = stderr.read().decode("utf-8", errors="replace").strip()

    if error and not content:
        raise RuntimeError(f"Remote command error: {error}")

    logger.info("[SSH] Remote file read successfully")
    return content


def _parse_properties(content: str) -> DeviceInfo:
    """
    Parse a Java .properties file (key=value per line).
    Tries "=" first (standard), falls back to ":" for non-standard GW firmware.
    Skips blank lines and comment lines (#).
    """
    props: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            props[key.strip()] = value.strip()
        elif ":" in line:
            # Non-standard fallback — some firmware variants use colon
            key, _, value = line.partition(":")
            props[key.strip()] = value.strip()

    return DeviceInfo(
        gw_version          = props.get("currentGatewayVersion",  "—"),
        hmi_version         = props.get("currentHmiVersion",       "—"),
        release_version     = props.get("currentReleaseVersion",   "—"),
        original_gw_version = props.get("originalGatewayVersion",  "—"),
    )


# ── Public API ────────────────────────────────────────────────────

def fetch_device_info(is_windows: bool | None = None) -> DeviceInfo:
    """
    Open an SSH session to the GW and return device version info.

    Auth is fully automatic — no setup required on any machine:
      1. Key auth: PPK (Windows) or PEM (Linux/Pi) + GW_PASSPHRASE
         → host key changes handled automatically (ssh-keygen -R equivalent)
      2. Password auth: GW_PASSWORD (fallback)

    is_windows: from PlatformProfile.operating_system == WINDOWS.
                Pass None to auto-detect via sys.platform.

    Raises RuntimeError if all auth methods fail.
    """
    try:
        import paramiko
    except ImportError:
        raise RuntimeError(
            "paramiko is not installed.\n"
            "Run: pip install paramiko>=3.0.0"
        )

    logger.info(f"[SSH] Connecting to {GW_USER}@{GW_HOST}:{GW_PORT}")

    # ── Strategy 1: key + passphrase ─────────────────────────────
    key_path = _select_key_file(is_windows)
    if key_path:
        client = _try_key_auth(paramiko, key_path)
        if client:
            try:
                return _parse_properties(_read_remote_file(client))
            finally:
                client.close()
    else:
        logger.info("[SSH] No key file found — skipping key auth")

    # ── Strategy 2: password fallback ────────────────────────────
    client = _try_password_auth(paramiko)
    if client:
        try:
            return _parse_properties(_read_remote_file(client))
        finally:
            client.close()

    # ── All methods failed ────────────────────────────────────────
    raise RuntimeError(
        f"SSH: all authentication methods failed for "
        f"{GW_USER}@{GW_HOST}:{GW_PORT}.\n"
        "Tried: key auth (with passphrase), password auth.\n"
        "Check that the key file exists in assets/keys/ and "
        "the GW is reachable at 172.16.0.1."
    )
