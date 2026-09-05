"""Command-line interface and reconnecting display service."""

import argparse
import fcntl
import json
import logging
import math
import os
import signal
import threading
from datetime import datetime
from pathlib import Path

from . import __version__
from .device import open_panel
from .protocol import packet
from .sensors import Sensors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diagnose", action="store_true", help="Read sensors and show packet without writing USB"
    )
    parser.add_argument("--once", action="store_true", help="Send one update and exit")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.2,
        help="Seconds between USB updates (positive, default: 0.2)",
    )
    parser.add_argument(
        "--cpu-freq-interval",
        type=float,
        default=1.0,
        help="Seconds between CPU frequency readings (positive, default: 1)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval must be a finite positive number of seconds")
    if not math.isfinite(args.cpu_freq_interval) or args.cpu_freq_interval <= 0:
        parser.error("--cpu-freq-interval must be a finite positive number of seconds")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Update interval: %g seconds", args.interval)
    logging.info("CPU frequency sampling interval: %g seconds", args.cpu_freq_interval)
    if args.diagnose:
        values = Sensors(args.cpu_freq_interval).sample()
        now = datetime.now().astimezone()
        print(
            json.dumps(
                dict(time=now.isoformat(), **values, packet_hex=packet(values, now).hex()), indent=2
            )
        )
        return
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    if not runtime.is_dir():
        parser.exit(1, "No user runtime directory; run inside a local login session.\n")
    lockpath = runtime / f"jonsbo-d34-{os.getuid()}.lock"
    with lockpath.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.exit(1, "Another jonsbo-d34 instance is already running.\n")
        stopped = threading.Event()

        def stop(signum, frame):
            stopped.set()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        fd = None
        sensors = None
        last_error = None
        try:
            while not stopped.is_set():
                try:
                    if sensors is None:
                        sensors = Sensors(args.cpu_freq_interval)
                    if fd is None:
                        fd = open_panel()
                    values = sensors.sample()
                    frame = packet(values, datetime.now().astimezone())
                    written = os.write(fd, frame)
                    if written != len(frame):
                        raise OSError(f"Short HID write: {written}/{len(frame)}")
                    if last_error is not None:
                        logging.info("Updates resumed")
                    last_error = None
                    if args.once:
                        print(json.dumps(dict(written=written, **values)))
                        return
                    stopped.wait(args.interval)
                except (OSError, ValueError, RuntimeError) as exc:
                    if args.once:
                        raise
                    if str(exc) != last_error:
                        logging.error("%s; retrying every 3 seconds", exc)
                        last_error = str(exc)
                    if fd is not None:
                        os.close(fd)
                    fd = None
                    sensors = None
                    stopped.wait(3)
        finally:
            if fd is not None:
                os.close(fd)
