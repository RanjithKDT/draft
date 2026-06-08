"""
config.py

Shared network and hardware constants used across modules.
Single source of truth — update here to affect all consumers.
"""

# ── Gateway (GW) ──────────────────────────────────────────────────
GW_HOST = "172.16.0.1"
GW_PORT = 22
GW_USER = "gw"

# ── HMI ──────────────────────────────────────────────────────────
# HMI is on the 192.168.x USB-RNDIS network, NOT on the CAN-side 172.16.0.x net.
# Confirmed testbench address: 192.168.82.70 (ccs@hmi via USB ethernet).
# Update here if the HMI gets a different DHCP lease.
HMI_HOST = "192.168.82.70"
HMI_PORT = 22
