# CAN Tools Sample Files — Hyva Simulator v1.5.5

These files test every feature of the CAN Tools File Browser.

---

## DATABASE FILES — show message definitions + SIGNALS table

| File | Format | Status | Notes |
|---|---|---|---|
| `truck_database.dbc` | Vector DBC | ✅ Works | 11 messages, 44 signals, J1939 + OBD-II |
| `truck_database.kcd` | Kvaser KCD/XML | ✅ Works | Same messages, XML format |
| `truck_database.arxml` | AUTOSAR ARXML | ⚠️ 0 messages | cantools ARXML parser requires specific schema — use DBC instead |

Load a database file → click any message row → SIGNALS table shows bit position, factor, offset, unit.

**Recommended format: DBC** — the most widely supported and reliable with cantools.

---

## LOG FILES — show recorded CAN traffic

| File | Format | Frames | Content |
|---|---|---|---|
| `truck_log.csv` | CSV (Timestamp,ID,DLC,Data) | 80 | J1939 engine, speed, tipping, OBD-II |
| `truck_log.json` | JSON array | 36 | Same data, no python-can required |
| `truck_log.asc` | Vector ASCII Log | 46 | python-can LogReader format |
| `truck_log.txt` | Raw hex lines | 37 | Fallback parser, comment lines with # |

Click any frame row → ARB ID and data auto-fill in Build & Send.
J1939 messages (arb_id > 0x7FF) auto-select the J1939 radio button.
Standard 11-bit messages (0x100, 0x200, 0x7E8) auto-select Standard.

---

## NEGATIVE TEST FILES — verify error handling

| File | Expected behaviour |
|---|---|
| `negative_malformed.csv` | 6 valid frames loaded, 4 bad rows silently skipped |
| `negative_empty.json` | Error: "no CAN frames found" |
| `negative_wrong_format.json` | Error: "must contain a JSON array" |

---

## J1939 ID REFERENCE

All J1939 IDs use real SAE J1939/21 encoding (29-bit extended, arb_id > 0x7FF):

| Hex ID | PGN | Description | Auto-selects |
|---|---|---|---|
| `0x0CF00400` | 0xF004 | EEC1 — Engine Speed, Torque | J1939 radio |
| `0x18FEF100` | 0xFEF1 | CCVS — Vehicle Speed | J1939 radio |
| `0x18FEEE00` | 0xFEEE | ET — Engine Temperature | J1939 radio |
| `0x18FEF700` | 0xFEF7 | EFL — Fuel/Oil Levels | J1939 radio |
| `0x18FEF500` | 0xFEF5 | EBC1 — Brake Controller | J1939 radio |
| `0x0C000063` | 0x0000 | Hyva Heartbeat, SA=0x63 | J1939 radio |
| `0x18FF0063` | 0xFF00 | Hyva Sensor Message, SA=0x63 | J1939 radio |
| `0x18FE5A63` | 0xFE5A | Hyva Body Tipped, SA=0x63 | J1939 radio |
| `0x100`, `0x200` | — | Standard 11-bit CAN | Standard radio |
| `0x7E8` | — | OBD-II ECU response (11-bit) | Standard radio |
| `0x7E0` | — | OBD-II tester request (11-bit) | Standard radio |

**Note:** OBD-II uses standard 11-bit IDs (≤ 0x7FF) — they are NOT J1939.

---

## DBC FORMAT — extended ID encoding

In DBC files, 29-bit J1939 IDs must have bit 31 set:

```
extended_dbc_id = raw_id | 0x80000000

Example: 0x0CF00400 (engine speed) = 217056256 raw
         217056256 | 2147483648    = 2364539904  ← write this in BO_ line
```
