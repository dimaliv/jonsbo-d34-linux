"""Discover and open only the supported USB HID interface."""

import logging
import os
from pathlib import Path

DESCRIPTOR = bytes.fromhex(
    "06 00 ff 09 01 a1 01 09 02 15 00 26 00 ff 75 08 95 40 81 06 09 02 15 00 26 00 ff 75 08 95 40 91 06 c0"
)


def open_panel(hidraw_root=Path("/sys/class/hidraw"), dev_root=Path("/dev")):
    for h in sorted(hidraw_root.glob("hidraw*")):
        if "HID_ID=0003:00005131:00002007" not in (h / "device/uevent").read_text():
            continue
        if (h / "device/report_descriptor").read_bytes() != DESCRIPTOR:
            raise RuntimeError("Unexpected HID descriptor; refusing to write")
        path = dev_root / h.name
        fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        logging.info("Connected to %s", path)
        return fd
    raise FileNotFoundError("Jonsbo USB 5131:2007 not found")
