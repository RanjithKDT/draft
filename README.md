# Hyva Simulator — v2.0.5

Desktop tool for testing and validating Hyva truck tipping systems.
Simulates sensors, J1939 CAN messages, and hardware signals so the real
Gateway (GW) and HMI can be tested without a physical truck.

Runs on **Windows 10/11**, **Linux**, and **Raspberry Pi** — no code
changes needed between platforms.

---

## Quick start

```bash
# 1. One-time setup
python setup.py            # Windows
python3 setup.py           # Linux / Raspberry Pi

# 2. Activate virtual environment
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # Linux / Raspberry Pi

# 3. Run
python main.py
```

Launcher scripts:

```bash
bash scripts/start-linux.sh          # Linux / Raspberry Pi
scripts\start-windows.bat            # Windows (with CAN)
scripts\start-windows-no-can.bat     # Windows (skip CAN check)
```

Optional flags:

```bash
python main.py --no-gui               # Headless mode — RPC still runs
python main.py --can-channel can1     # Override CAN channel at startup
```

---

## Environment variables

Set these in the shell **before** running the simulator.
The simulator starts without them but SSH auth will not work if they are missing.

| Variable        | Default  | Required for              | How to set                          |
|-----------------|----------|---------------------------|-------------------------------------|
| `GW_PASSPHRASE` | *(empty)* | SSH key passphrase auth  | `export GW_PASSPHRASE=<passphrase>` |
| `GW_PASSWORD`   | *(empty)* | SSH password fallback    | `export GW_PASSWORD=<password>`     |

**Windows:**
```cmd
set GW_PASSPHRASE=my_passphrase
set GW_PASSWORD=my_password
python main.py
```

**Linux / Raspberry Pi:**
```bash
export GW_PASSPHRASE=my_passphrase
export GW_PASSWORD=my_password
python3 main.py
```

> **Security note:** Never hardcode credentials in source code.
> The simulator will log a warning at startup if `GW_PASSWORD` is not set.

---

## Requirements

| Package          | Version   | Notes                                           |
|------------------|-----------|-------------------------------------------------|
| Python           | >= 3.12   | 3.12 required; 3.13 supported                  |
| PySide6          | >= 6.7.0  | Qt6 GUI framework                              |
| loguru           | >= 0.7.0  | Structured logging                             |
| python-interface | == 1.6.1  | HAL interface enforcement                      |
| python-can       | >= 4.3.0  | CAN bus abstraction                            |
| pyserial         | >= 3.5    | Lucid IO / port detection                      |
| qtawesome        | >= 1.3.0  | Font Awesome icons                             |
| paramiko         | >= 3.4.0  | SSH to Gateway                                 |
| rpyc             | >= 6.0.0  | RPC server for test automation                 |
| cantools         | >= 38.0.0 | CAN Tools .dbc/.kcd/.arxml (optional)          |
| gpiod            | any       | Raspberry Pi only                              |
| pywin32, wmi     | any       | Windows only — installed by setup.py           |

---

## Project structure

```
hyva-simulator/
├── main.py
├── setup.py
├── requirements.txt
├── assets/
│   ├── fonts/                      Bundled Inter + Liberation fonts
│   ├── keys/
│   │   ├── id_gateway.ppk          SSH key (Windows — PPK)
│   │   └── id_gateway_pem          SSH key (Linux/Pi — PEM)
│   └── logo/hyva_logo.jpg
├── scripts/
└── simulator/
    ├── simulator.py                Wiring: HAL → CAN → monitor → RPC → GUI
    ├── config.py                   Shared constants (GW/HMI host, port)
    ├── platform/                   OS detection, HAL selection, CAN channel scan
    ├── hal/                        IHal, NoHal, RaspberryPiHal
    ├── ign/                        IgnitionController (LucidIO / GPIO / Software)
    ├── obu/                        J1939 encoder + ObuBridge (cyclic CAN TX)
    ├── can/                        CAN monitor worker + CAN file reader
    ├── monitor/                    ConnectionMonitor (polls all nodes every 1 s)
    ├── network/                    InternetMonitor (internet status — stdlib only)
    ├── playback/                   CsvPlayer (scenario file replay)
    ├── rpc/                        RPC server on port 18200
    ├── ssh/                        SSH client → GW device info
    └── gui/
        ├── constants.py            Shared GUI constants (single source of truth)
        ├── fonts.py
        └── main_window.py          All GUI pages
```

---

## Sensors

| Sensor                   | ID     | Range              | Ramp rate |
|--------------------------|--------|--------------------|-----------| 
| Lateral inclination      | `0x04` | -18.75 to +18.75 ° | 2 °/s    |
| Longitudinal inclination | `0x03` | -20 to +80 °       | 2 °/s    |
| Cylinder pressure        | `0x01` | -32 to +500 bar    | 10 bar/s |
| Joystick position        | `0x09` | -1 to +1           | 0.5/s    |

Sensors ramp toward their target — producing realistic waveforms rather than step changes.

---

## CAN / J1939 messages

| Schedule | Messages                                                                                                    |
|----------|-------------------------------------------------------------------------------------------------------------|
| 100 ms   | HeartbeatEvent (simulator SA=0x63 + all faked node SAs)                                                    |
| 500 ms   | SensorMessage x4 + SensorDiagnosticsEvent x4                                                               |
| 1000 ms  | ProtocolVersionEvent, StateUpdatedEvent, SafetyStatusEvent, ToppleOverStatusEvent, DtsModeEvent, BodyTippedEvent |

Absent nodes (GW, HMI, Trailer Controller, Truck Controller) are auto-detected from heartbeat age and faked automatically.

---

## CAN Tools page

Accessible from the CAN page via the **CAN TOOLS** button.

### Supported file formats

| Category     | Extensions                                   | Library                    |
|--------------|----------------------------------------------|----------------------------|
| CAN database | `.dbc`, `.kcd`, `.arxml`                     | cantools                   |
| CAN log      | `.asc`, `.blf`, `.trc`, `.log`, `.csv`, `.txt` | python-can (built-in fallback) |
| CAN log      | `.json`                                       | built-in                   |

### Workflow

1. **Browse** — pick any supported file. The browser table populates immediately.
2. **Click a row** — Arb ID, data bytes, and frame type auto-fill in Build & Send.
3. **Edit** — adjust values, choose channel (pill), select DLC and interval.
4. **Send** — one-shot send, or enable **Continuous** to send on a timer.

### Build & Send — DLC values

| Group                     | Values                       |
|---------------------------|------------------------------|
| Classical CAN / J1939     | 0, 1, 2, 3, 4, 5, 6, 7, 8   |
| CAN FD only (ISO 11898-1) | 12, 16, 20, 24, 32, 48, 64   |

---

## SSH — Gateway device info

The HOME page **Fetch** button connects to the Gateway (`172.16.0.1:22`) and reads firmware/version properties.

Auth order (automatic, no setup required):

1. Key + passphrase — `id_gateway.ppk` (Windows) or `id_gateway_pem` (Linux/Pi)
2. Password fallback — set `GW_PASSWORD` env var (see [Environment variables](#environment-variables))

---

## RPC automation API (port 18200)

```python
import rpyc
r = rpyc.connect("localhost", 18200).root

r.ping()
r.set_ignition(True)
r.set_sensor_target(0x04, 5.0)        # Lateral = 5 degrees
r.get_all_sensor_values()
r.set_jitter(0x04, True)              # enable noise on lateral sensor
r.load_playback("/path/to/file.csv")
r.start_playback()
r.get_playback_status()
r.get_node_status()
r.get_status()                         # full snapshot
```

All 22 methods return plain Python types. Full method list in `rpc_server.py`.

---

## CSV playback format

| Sensor                   | Recognised column names                           |
|--------------------------|---------------------------------------------------|
| Timestamp                | `timestamp`, `time`, `elapsed`, `elapsed_s`, `t` |
| Lateral inclination      | `inclino_lat`, `lateral`, `lat`                   |
| Longitudinal inclination | `inclino_long`, `longitudinal`, `long`            |
| Cylinder pressure        | `pressure_400`, `pressure`, `cyl_press`           |
| Joystick                 | `joystick_pos`, `joystick`, `joy`                 |

Column names matched case-insensitively. Maximum 1 000 000 rows.
A warning is logged when a file is truncated at this limit.

---

## Development

### Coding standards

- **Type hints** — all functions and methods include Python type hints (return types enforced across all 55 first-party files).
- **PEP 8** — code follows PEP 8 with 79-character line limits.
- **Logging** — loguru at appropriate levels; only meaningful events logged.
- **Error handling** — explicit handling with no silent failures.
- **Modular design** — small, focused functions and classes.
- **Cross-platform** — Windows, Linux, and Raspberry Pi without code changes.
- **No secrets in source** — credentials loaded from env vars only; missing vars produce a startup warning.
- **Single source of truth** — shared GUI constants live in `simulator/gui/constants.py`.

### Testing

Run the simulator and verify:

- GUI launches on all platforms.
- CAN channels are detected correctly.
- Sensors update in real-time.
- Playback from CSV files works.
- RPC server responds to commands.

### Troubleshooting

- **No CAN channels found** — ensure CAN hardware is connected and drivers installed.
- **GPIO not working on Pi** — add user to `gpio` group or run with `sudo`.
- **PySide6 import error** — ensure virtual environment is activated.
- **SSH connection fails** — check Gateway IP, SSH keys, and `GW_PASSPHRASE`/`GW_PASSWORD` env vars.
- **CAN log truncated** — increase `MAX_LOG_FRAMES` in `can_file_reader.py` (default 10 000).

### Git hygiene

The `.gitignore` excludes `__pycache__/` and `*.pyc`.
If compiled files were previously tracked, remove them with:

```bash
git rm -r --cached simulator/**/__pycache__
git commit -m "Remove tracked pyc files"
```

---

## Architecture notes

**Single OS detection** — `platform_detector.detect()` runs once and returns `PlatformProfile`.
All modules read the profile; nothing calls `sys.platform` directly.

**Lazy imports** — optional libraries (`gpiod`, `paramiko`, `rpyc`, `python-can`, `cantools`,
`serial`) are imported only when used. Missing library gives a clear warning + software fallback.
Startup never crashes.

**Concurrent monitoring** — GW and HMI TCP reachability checks run in parallel via
`ThreadPoolExecutor`, keeping worst-case poll latency at one TCP timeout (0.8 s) even
when both hosts are offline.

### Thread model

| Thread                       | Purpose                          |
|------------------------------|----------------------------------|
| Main (Qt)                    | GUI rendering                    |
| ObuBridge (QThread)          | CAN TX — 100 ms tick             |
| CanMonitorWorker (QThread)   | CAN RX + frame table             |
| CsvPlayer (QThread)          | Scenario playback                |
| ConnectionMonitor (daemon)   | Node polling every 1 s           |
| InternetMonitor (QThread)    | Internet status probe every 10 s |
| RpcServer (daemon)           | rpyc on port 18200               |
| _FetchWorker (QThread)       | SSH to GW (one-shot)             |

All shared state protected by `threading.Lock`.
Cross-thread GUI updates use `QueuedConnection`.

---

## Version history

| **2.0.5r2** | 2026-04 | **Code quality & safety pass.** Full line-by-line review of all 55 first-party modules. Fixes: (1) Removed unused `InternetMonitor` imports from 8 page files. (2) Removed duplicate `subprocess`/`sys` imports inside `_ping_once`. (3) Removed hardcoded `"gw"` SSH password — now env-var only with startup warning. (4) Added missing `Callable` + `CanChannel` imports to `simulator.py`. (5) `signal.signal()` wrapped in `try/except` for non-main-thread safety. (6) All 7 J1939 enum classes converted from plain class to `IntEnum` (iterable, membership-testable). (7) `SENSOR_LABEL` + `_SENSOR_RANGE` dicts replace 3 O(n) linear searches in hot 100 ms loop. (8) GW + HMI TCP checks now concurrent via `ThreadPoolExecutor` — worst-case poll latency halved. (9) `atexit` lambda replaced with clean named `_cleanup_arrow()` function. (10) TX errors rate-limited: WARNING on 1st and every 100th repeat instead of silent DEBUG. (11) CAN log truncation now emits WARNING in all 4 parsers. (12) `constants.py` created — `PROJECT_ROOT`, `SIDEBAR_WIDTH`, `BAUDRATE_OPTIONS` centralised; 8+ duplicate definitions removed. (13) `_can_connected_count` moved from `_build_ui()` to `__init__()`. (14) Zero missing return types across all 55 first-party files. (15) 55/55 files pass `ast.parse` syntax check. |
| **2.0.5**   | 2026-04 | **UI + logging fixes.** Back-to-Home button moved to RIGHT side on Guide, Control, Tip by Wire, and EPTO pages. Internet log spam fixed. Internet icon (WiFi) added to net pill. |
| **2.0.4**   | 2026-04 | **UI separator fix.** `RedSepV`/`RedSepH` `WA_StyledBackground` fix. `PageTitleBar` separator truncation fix. Settings sub-page double separator fix. |
| **2.0.3**   | 2026-04 | **Internet status indicator** — live pill in top-right header. New `internet_monitor.py`. |
| **2.0.2**   | 2026-03 | UI fixes and settings page improvements. |
| **2.0.1**   | 2026-03 | Bug fixes. `GoodbyeScreen` crash fixed. |
| **2.0.0**   | 2026-03 | **Major release** — GUI design system + full type hints. |
| **1.5.0–1.5.6** | 2026-03 | Build & Send: DLC dropdown, continuous send, interval control. |
| **1.4.0–1.4.1** | 2026-03 | CAN Tools page. |
| **1.3.0–1.3.5** | 2026-03 | Connection monitoring overhaul. Lucid AIVO sensor voltage output. |
| **1.2.0–1.2.9** | 2026-03 | Live sensor dashboard. |
| **1.1.0–1.1.9** | 2026-02 | SSH auth finalised. Calibrations page. |
| **1.0.5–1.0.9** | 2026-02 | Code quality pass. SSH rewrite. |
| **0.1–0.3** | 2026-01 | Initial build. |


Desktop tool for testing and validating Hyva truck tipping systems.
Simulates sensors, J1939 CAN messages, and hardware signals so the real
Gateway (GW) and HMI can be tested without a physical truck.

Runs on **Windows 10/11**, **Linux**, and **Raspberry Pi** — no code
changes needed between platforms.

---

## Quick start

```bash
# 1. One-time setup
python setup.py            # Windows
python3 setup.py           # Linux / Raspberry Pi

# 2. Activate virtual environment
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # Linux / Raspberry Pi

# 3. Run
python main.py
```

Launcher scripts:

```bash
bash scripts/start-linux.sh          # Linux / Raspberry Pi
scripts\start-windows.bat            # Windows (with CAN)
scripts\start-windows-no-can.bat     # Windows (skip CAN check)
```

Optional flags:

```bash
python main.py --no-gui               # Headless mode — RPC still runs
python main.py --can-channel can1     # Override CAN channel at startup
```

---

## Requirements

| Package          | Version   | Notes                                           |
|------------------|-----------|-------------------------------------------------|
| Python           | >= 3.12   | 3.12 required; 3.13 supported                  |
| PySide6          | >= 6.7.0  | Qt6 GUI framework                              |
| loguru           | >= 0.7.0  | Structured logging                             |
| python-interface | == 1.6.1  | HAL interface enforcement                      |
| python-can       | >= 4.3.0  | CAN bus abstraction                            |
| pyserial         | >= 3.5    | Lucid IO / port detection                      |
| qtawesome        | >= 1.3.0  | Font Awesome icons                             |
| paramiko         | >= 3.4.0  | SSH to Gateway                                 |
| rpyc             | >= 6.0.0  | RPC server for test automation                 |
| cantools         | >= 38.0.0 | CAN Tools .dbc/.kcd/.arxml (optional)          |
| gpiod            | any       | Raspberry Pi only                              |
| pywin32, wmi     | any       | Windows only — installed by setup.py           |

---

## Project structure

```
hyva-simulator/
├── main.py
├── setup.py
├── requirements.txt
├── assets/
│   ├── fonts/                      Bundled Inter + Liberation fonts
│   ├── keys/
│   │   ├── id_gateway.ppk          SSH key (Windows — PPK)
│   │   └── id_gateway_pem          SSH key (Linux/Pi — PEM)
│   └── logo/hyva_logo.jpg
├── scripts/
└── simulator/
    ├── simulator.py                Wiring: HAL → CAN → monitor → RPC → GUI
    ├── config.py                   Shared constants (GW/HMI host, port)
    ├── platform/                   OS detection, HAL selection, CAN channel scan
    ├── hal/                        IHal, NoHal, RaspberryPiHal
    ├── ign/                        IgnitionController (LucidIO / GPIO / Software)
    ├── obu/                        J1939 encoder + ObuBridge (cyclic CAN TX)
    ├── can/                        CAN monitor worker + CAN file reader
    ├── monitor/                    ConnectionMonitor (polls all nodes every 1 s)
    ├── network/                    InternetMonitor (internet status — stdlib only)
    ├── playback/                   CsvPlayer (scenario file replay)
    ├── rpc/                        RPC server on port 18200
    ├── ssh/                        SSH client → GW device info
    └── gui/
        ├── fonts.py
        └── main_window.py          All GUI pages
```

---

## Sensors

| Sensor                   | ID     | Range              | Ramp rate |
|--------------------------|--------|--------------------|-----------|
| Lateral inclination      | `0x04` | -18.75 to +18.75 ° | 2 °/s    |
| Longitudinal inclination | `0x03` | -20 to +80 °       | 2 °/s    |
| Cylinder pressure        | `0x01` | -32 to +500 bar    | 10 bar/s |
| Joystick position        | `0x09` | -1 to +1           | 0.5/s    |

Sensors ramp toward their target — producing realistic waveforms rather than step changes.

---

## CAN / J1939 messages

| Schedule | Messages                                                                                                    |
|----------|-------------------------------------------------------------------------------------------------------------|
| 100 ms   | HeartbeatEvent (simulator SA=0x63 + all faked node SAs)                                                    |
| 500 ms   | SensorMessage x4 + SensorDiagnosticsEvent x4                                                               |
| 1000 ms  | ProtocolVersionEvent, StateUpdatedEvent, SafetyStatusEvent, ToppleOverStatusEvent, DtsModeEvent, BodyTippedEvent |

Absent nodes (GW, HMI, Trailer Controller, Truck Controller) are auto-detected from heartbeat age and faked automatically.

---

## CAN Tools page

Accessible from the CAN page via the **CAN TOOLS** button.

### Supported file formats

| Category     | Extensions                                   | Library                    |
|--------------|----------------------------------------------|----------------------------|
| CAN database | `.dbc`, `.kcd`, `.arxml`                     | cantools                   |
| CAN log      | `.asc`, `.blf`, `.trc`, `.log`, `.csv`, `.txt` | python-can (built-in fallback) |
| CAN log      | `.json`                                       | built-in                   |

### Workflow

1. **Browse** — pick any supported file. The browser table populates immediately.
2. **Click a row** — Arb ID, data bytes, and frame type auto-fill in Build & Send.
3. **Edit** — adjust values, choose channel (pill), select DLC and interval.
4. **Send** — one-shot send, or enable **Continuous** to send on a timer.

### Build & Send — DLC values

| Group                     | Values                       |
|---------------------------|------------------------------|
| Classical CAN / J1939     | 0, 1, 2, 3, 4, 5, 6, 7, 8   |
| CAN FD only (ISO 11898-1) | 12, 16, 20, 24, 32, 48, 64   |

---

## SSH — Gateway device info

The HOME page **Fetch** button connects to the Gateway (`172.16.0.1:22`) and reads firmware/version properties.

Auth order (automatic, no setup required):

1. Key + passphrase — `id_gateway.ppk` (Windows) or `id_gateway_pem` (Linux/Pi)
2. Password fallback

Override when credentials change:

```bash
export GW_PASSPHRASE=<passphrase>
export GW_PASSWORD=<password>
```

---

## RPC automation API (port 18200)

```python
import rpyc
r = rpyc.connect("localhost", 18200).root

r.ping()
r.set_ignition(True)
r.set_sensor_target(0x04, 5.0)        # Lateral = 5 degrees
r.get_all_sensor_values()
r.set_jitter(0x04, True)              # enable noise on lateral sensor
r.load_playback("/path/to/file.csv")
r.start_playback()
r.get_playback_status()
r.get_node_status()
r.get_status()                         # full snapshot
```

All 22 methods return plain Python types. Full method list in `rpc_server.py`.

---

## CSV playback format

| Sensor                   | Recognised column names                           |
|--------------------------|---------------------------------------------------|
| Timestamp                | `timestamp`, `time`, `elapsed`, `elapsed_s`, `t` |
| Lateral inclination      | `inclino_lat`, `lateral`, `lat`                   |
| Longitudinal inclination | `inclino_long`, `longitudinal`, `long`            |
| Cylinder pressure        | `pressure_400`, `pressure`, `cyl_press`           |
| Joystick                 | `joystick_pos`, `joystick`, `joy`                 |

Column names matched case-insensitively. Maximum 1 000 000 rows.

---

## Development

### Coding standards

- **Type hints** — all functions and methods include Python type hints.
- **PEP 8** — code follows PEP 8 with 79-character line limits.
- **Logging** — loguru at appropriate levels; only meaningful events logged.
- **Error handling** — explicit handling with no silent failures.
- **Modular design** — small, focused functions and classes.
- **Cross-platform** — Windows, Linux, and Raspberry Pi without code changes.

### Testing

Run the simulator and verify:

- GUI launches on all platforms.
- CAN channels are detected correctly.
- Sensors update in real-time.
- Playback from CSV files works.
- RPC server responds to commands.

### Troubleshooting

- **No CAN channels found** — ensure CAN hardware is connected and drivers installed.
- **GPIO not working on Pi** — add user to `gpio` group or run with `sudo`.
- **PySide6 import error** — ensure virtual environment is activated.
- **SSH connection fails** — check Gateway IP and SSH keys.

---

## Architecture notes

**Single OS detection** — `platform_detector.detect()` runs once and returns `PlatformProfile`.
All modules read the profile; nothing calls `sys.platform` directly.

**Lazy imports** — optional libraries (`gpiod`, `paramiko`, `rpyc`, `python-can`, `cantools`,
`serial`) are imported only when used. Missing library gives a clear warning + software fallback.
Startup never crashes.

### Thread model

| Thread                       | Purpose                          |
|------------------------------|----------------------------------|
| Main (Qt)                    | GUI rendering                    |
| ObuBridge (QThread)          | CAN TX — 100 ms tick             |
| CanMonitorWorker (QThread)   | CAN RX + frame table             |
| CsvPlayer (QThread)          | Scenario playback                |
| ConnectionMonitor (daemon)   | Node polling every 1 s           |
| InternetMonitor (QThread)    | Internet status probe every 10 s |
| RpcServer (daemon)           | rpyc on port 18200               |
| _FetchWorker (QThread)       | SSH to GW (one-shot)             |

All shared state protected by `threading.Lock`.
Cross-thread GUI updates use `QueuedConnection`.

---

## Version history

| **2.0.5**   | 2026-04 | **UI + logging fixes.** (1) Back-to-Home button moved to RIGHT side of page on Guide, Control, Tip by Wire, and EPTO pages — matches CAN Tools pattern: `PageTitleBar(show_separator=False)` left + pill back button right + full-width `HSep` below. (2) Internet log spam fixed — removed `[NET] Probe ... reachable` and `[NET] State unchanged: ONLINE` debug messages that printed every 10 s; only genuine state transitions are logged. (3) Internet icon added — net pill now shows a WiFi `IconWidget` (FA `fa6s.wifi`, fallback `◎`) matching the UTC globe and date calendar pill style; colour changes amber/green/red with state. |
| **2.0.4**   | 2026-04 | **UI separator fix.** Three root causes addressed: (1) `RedSepV`/`RedSepH` missing `WA_StyledBackground` — invisible on Windows/Fusion. (2) `PageTitleBar` internal `HSep` truncated at pill column edge on CAN and CAN TOOLS pages — added `show_separator: bool = True` parameter. (3) Settings sub-pages had double separator — fixed by `show_separator=False`. `styles.py` `red-sep-v` gains `min-width: 2px`. |
| **2.0.3**   | 2026-04 | **Internet status indicator** — live pill in top-right header. New module `simulator/network/internet_monitor.py` probes TCP reachability every 10 s using stdlib `socket`. Amber `CHECKING…` on startup, green `ONLINE`, red `OFFLINE`. |
| **2.0.2**   | 2026-03 | UI fixes and settings page improvements. Separator height 1 px to 2 px. Settings sub-page headers redesigned with platform strip. Full-width `HSep` added to all 4 settings sub-pages. |
| **2.0.1**   | 2026-03 | Bug fixes. `GoodbyeScreen` crash fixed (local variable `t` shadowed theme alias). Settings sub-pages redesigned: title pill left, back button right, separator beneath. |
| **2.0.0**   | 2026-03 | **Major release — GUI design system + full type hints.** New files: `theme.py`, `icons.py`, `styles.py`, `components.py`. `main_window.py` migrated, `COLORS` dict removed, type hints at 100% coverage across 282 functions / 22 modules. |
| **1.5.0–1.5.6** | 2026-03 | Build & Send: DLC dropdown, continuous send, interval control. GUI design system migration. Full matte finish redesign. |
| **1.4.0–1.4.1** | 2026-03 | CAN Tools page — file browser (.dbc/.kcd/.arxml/.asc/.blf/.csv/.json) + Build & Send panel. |
| **1.3.0–1.3.5** | 2026-03 | Connection monitoring overhaul. Lucid AIVO sensor voltage output. IGN-OFF broadcast. Comprehensive logging audit. |
| **1.2.0–1.2.9** | 2026-03 | Live sensor dashboard. Sensor card polish. PageTitleBar size policy fix. Credits rainbow dot. |
| **1.1.0–1.1.9** | 2026-02 | SSH auth finalised. Calibrations page. pyLucidIo v2.5 upgrade. Goodbye screen. |
| **1.0.5–1.0.9** | 2026-02 | Code quality pass. SSH rewrite with paramiko 3.x fixes and key+passphrase auth. |
| **0.1–0.3** | 2026-01 | Initial build: skeleton, HAL system, CAN, sensors, J1939, OBU Bridge, RPC, CSV playback, SSH, settings. |
