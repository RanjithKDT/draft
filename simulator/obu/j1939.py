"""
j1939.py — J1939 CAN ID helpers + TippingTCS message encoder
No external dependencies (pure struct).

All encodings verified against:
  - TippingTCS.kcd (MuxGroup layout)
  - Live candump from testbench GW + HMI
  - TippingTCSCommunication.py source
"""

import struct
from enum import IntEnum

# ── Simulator source address ──────────────────────────────────────
SA_SIMULATOR   = 0x63   # 99
SA_BROADCAST   = 0xFF   # J1939 broadcast

# ── PGNs used ─────────────────────────────────────────────────────
PGN_SENSOR     = 0xFF00   # SensorMessage     → 8-byte, mux on sensor_id
PGN_EVENT      = 0xFF01   # EventMessage      → 8-byte, mux on event_id

# ── Event IDs (from TippingTCSCommunication.py) ───────────────────
EID_SW_VERSION          = 0x0001   #  1
EID_PROTOCOL_VERSION    = 0x0002   #  2
EID_STATE_UPDATED       = 0x0003   #  3
EID_ONBOARDING_STATUS   = 0x000D   # 13  (Gateway only)
EID_HEARTBEAT           = 0x000F   # 15
EID_SAFETY_STATUS       = 0x0032   # 50
EID_TOPPLE_OVER         = 0x02BC   # 700
EID_DTS_MODE            = 0x03E8   # 1000
EID_BODY_TIPPED         = 0x00C8   # 200
EID_SENSOR_DIAG         = 0x0CE4   # 3300  SensorDiagnosticsEvent

# ── Sensor IDs (from ModelEnums.SensorId) ────────────────────────
class SensorId(IntEnum):
    PRESSURE_400       = 0x01   # pressureCyl      -32..500 bar
    PRESSURE_16        = 0x02   # pressureReturn   0..16 bar
    INCLINO_LONG       = 0x03   # inclinationLong  -20..+80 °
    INCLINO_LAT        = 0x04   # inclinationLat   ±18.75 °
    OIL_TEMP           = 0x05   # oilTemperature
    INCLINO_CYLINDER   = 0x06   # cylinderAngle
    JOYSTICK_POS       = 0x09   # joystickPositive -1..+1
    JOYSTICK_NEG       = 0x0A   # joystickNegative
    EVALVE_POSITION    = 0x0C   # HTEvalve
    DUMP_VALVE         = 0x0D   # dumpValveState
    STEPPER_RELAY      = 0x23   # stepperRelay
    EVALVE_STATUS      = 0x24   # eValveStatus

# ── System state enums ────────────────────────────────────────────
class SystemState(IntEnum):
    INITIALIZATION  = 0
    STARTUP_CHECKS  = 1
    OPERATIONAL     = 2
    SERVICE         = 3
    CALIBRATION     = 4
    SAFETY          = 5
    FOTA            = 6
    MANUAL          = 7
    IGNITION_OFF    = 8

class SystemSubState(IntEnum):
    DEACTIVATED     = 0
    IDLE            = 1

class SafetyErrorType(IntEnum):
    NO_ERROR        = 0

class SafetyState(IntEnum):
    OK_STATE        = 0

class DtsMode(IntEnum):
    UNKNOWN         = 0
    CONNECT         = 1
    CONTROL         = 6

class ToppleOverStatus(IntEnum):
    INACTIVE        = 0

# ── CAN ID helpers ────────────────────────────────────────────────

def make_can_id(pgn: int, sa: int, priority: int = 3) -> int:
    """
    Build 29-bit J1939 CAN arbitration ID.
    For PDU2 (PGN >= 0xF000), destination is part of the PGN itself.
    """
    return (priority << 26) | ((pgn & 0x03FFFF) << 8) | (sa & 0xFF)


# ── Event message encoding ────────────────────────────────────────
#
# Wire format (8 bytes, Intel / little-endian bit ordering):
#   bits  0-1  : EventMessage_event_type  (2 bits, always 0 = Info)
#   bit   2    : EventMessage_dummy_1bit  (1 bit, always 0)
#   bits  3-15 : event_id                (13 bits, LE)
#   bits 16-63 : event-specific payload  (6 bytes)
#
# bytes 0-1 = struct.pack('<H', event_type | (dummy<<2) | (event_id<<3))
# bytes 2-7 = payload, zero-padded to 6 bytes

def _event_header(event_id: int, event_type: int = 0, dummy: int = 0) -> bytes:
    """First 2 bytes of any event message."""
    h = (event_type & 0x3) | ((dummy & 0x1) << 2) | ((event_id & 0x1FFF) << 3)
    return struct.pack('<H', h)


def encode_heartbeat(sa: int = SA_SIMULATOR) -> tuple[int, bytes]:
    """HeartbeatEvent — EID=0x0F, no payload."""
    arb = make_can_id(PGN_EVENT, sa)
    data = _event_header(EID_HEARTBEAT) + b'\x00' * 6
    return arb, data


def encode_protocol_version(version: int = 4, sa: int = SA_SIMULATOR) -> tuple[int, bytes]:
    """ProtocolVersionEvent — EID=0x02, payload: uint32 LE version."""
    arb = make_can_id(PGN_EVENT, sa)
    payload = struct.pack('<I', version) + b'\x00\x00'
    data = _event_header(EID_PROTOCOL_VERSION) + payload
    return arb, data


def encode_state_updated(
    system_state: int = SystemState.OPERATIONAL,
    sub_state: int = SystemSubState.IDLE,
    sa: int = SA_SIMULATOR,
) -> tuple[int, bytes]:
    """StateUpdatedEvent — EID=0x03, payload: systemState(u8) subState(u8) + 4 zeros."""
    arb = make_can_id(PGN_EVENT, sa)
    payload = struct.pack('BB', system_state, sub_state) + b'\x00' * 4
    data = _event_header(EID_STATE_UPDATED) + payload
    return arb, data


def encode_safety_status(
    most_severe_error: int = SafetyErrorType.NO_ERROR,
    state: int = SafetyState.OK_STATE,
    sa: int = SA_SIMULATOR,
) -> tuple[int, bytes]:
    """SafetyStatusEvent — EID=0x32, payload: mostSevereError(u8) state(u8) + 4 zeros."""
    arb = make_can_id(PGN_EVENT, sa)
    payload = struct.pack('BB', most_severe_error, state) + b'\x00' * 4
    data = _event_header(EID_SAFETY_STATUS) + payload
    return arb, data


def encode_dts_mode(
    dts_mode: int = DtsMode.UNKNOWN,
    sa: int = SA_SIMULATOR,
) -> tuple[int, bytes]:
    """DtsModeEvent — EID=0x3E8, payload: dtsMode(u8) + 5 zeros."""
    arb = make_can_id(PGN_EVENT, sa)
    payload = struct.pack('B', dts_mode) + b'\x00' * 5
    data = _event_header(EID_DTS_MODE) + payload
    return arb, data


def encode_topple_over_status(
    status: int = ToppleOverStatus.INACTIVE,
    sa: int = SA_SIMULATOR,
) -> tuple[int, bytes]:
    """ToppleOverStatusEvent — EID=0x2BC, payload: status(u8) + 5 zeros."""
    arb = make_can_id(PGN_EVENT, sa)
    payload = struct.pack('B', status) + b'\x00' * 5
    data = _event_header(EID_TOPPLE_OVER) + payload
    return arb, data


def encode_body_tipped(
    tipped: bool = False,
    sa: int = SA_SIMULATOR,
) -> tuple[int, bytes]:
    """BodyTippedEvent — EID=0xC8, payload: 31-bit dummy + 1-bit tipped."""
    arb = make_can_id(PGN_EVENT, sa)
    # dummy_31bits at offset=16 (bits 0-30 of payload), bodyTipped at bit 31
    val = (1 << 31) if tipped else 0
    payload = struct.pack('<I', val) + b'\x00\x00'
    data = _event_header(EID_BODY_TIPPED) + payload
    return arb, data


def encode_sensor_diagnostics(
    sensor_id: int,
    sensor_status: int = 0,   # 0 = Ok
    sensor_type: int = 0,     # 0 = Voltage
    diag_code: int = 0,
    sa: int = SA_SIMULATOR,
) -> tuple[int, bytes]:
    """
    SensorDiagnosticsEvent — EID=0xCE4
    payload layout (from KCD offsets, all relative to bit 16):
      bits 16-31: sensorId (uint16 LE)
      bits 32-39: sensorStatus (uint8)
      bits 40-47: sensorType (uint8)
      bits 48-63: sensorDiagCode (uint16 LE)
    """
    arb = make_can_id(PGN_EVENT, sa)
    payload = struct.pack('<HBBH', sensor_id, sensor_status, sensor_type, diag_code)
    data = _event_header(EID_SENSOR_DIAG) + payload
    return arb, data


# ── Sensor message encoding ───────────────────────────────────────
#
# Wire format (8 bytes, from KCD + live bus verification):
#   bytes 0-1: sensor_id (uint16 LE)  ← mux key
#   bytes 2-3: 0x0000                 ← padding (part of mux structure)
#   bytes 4-7: value (float32 LE)
#
# Verified from live HMI candump:
#   sensor_id=3 (InclinoLong), value=-0.68  → 03 00 00 00 7B 14 2E BF 
#   sensor_id=4 (InclinoLat),  value=-0.47  → 04 00 00 00 85 EB F1 BE 

def encode_sensor(
    sensor_id: int,
    value: float,
    sa: int = SA_SIMULATOR,
) -> tuple[int, bytes]:
    """SensorMessage — PGN=0xFF00."""
    arb = make_can_id(PGN_SENSOR, sa)
    data = struct.pack('<HHf', sensor_id, 0, value)
    return arb, data
