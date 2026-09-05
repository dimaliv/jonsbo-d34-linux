"""Encode the D34 numeric HID report. See docs/protocol.md for provenance."""

from collections.abc import Mapping
from datetime import datetime


def packet(values: Mapping[str, float], now: datetime) -> bytes:
    """Build a 65-byte hidraw buffer from sensor readings and local wall time."""
    v = bytearray(33)
    for index, key in ((0, "cpu_temp"), (10, "gpu_temp")):
        value = max(0, min(25599, int(values[key] * 100)))
        v[index], v[index + 1] = divmod(value, 100)
    for index, key in ((6, "cpu_mhz"), (16, "gpu_mhz")):
        v[index], v[index + 1] = divmod(max(0, min(25599, int(values.get(key, 0)))), 100)
    for index, key in ((3, "cpu_usage"), (13, "gpu_usage"), (30, "ram_usage")):
        v[index] = max(0, min(100, int(values.get(key, 0))))
    power = max(0, min(2559999, int(values.get("gpu_power", 0) * 100)))
    v[32], remainder = divmod(power, 10000)
    v[14], v[15] = divmod(remainder, 100)
    v[22:30] = bytes(
        [
            now.year // 100,
            now.year % 100,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
            (now.weekday() + 1) % 7,
        ]
    )
    # hidraw requires a leading zero report ID for unnumbered reports.
    return bytes([0, 0, 1, 2]) + v + bytes(28)
