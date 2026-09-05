#!/usr/bin/env python3
"""Install or remove the user service without pip or root privileges."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SERVICE = "jonsbo-d34.service"
MARKER = ".jonsbo-d34-install"


def unit_quote(value):
    """Quote a literal systemd path (not shell syntax)."""
    value = str(value)
    if any(char in value for char in ("\n", "\r", "\x00")):
        raise ValueError("Installation paths must not contain newlines or NUL")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def paths():
    home = Path.home()
    config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    data = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    if not config.is_absolute() or not data.is_absolute():
        raise ValueError("XDG_CONFIG_HOME and XDG_DATA_HOME must be absolute paths")
    return data / "jonsbo-d34", config / "jonsbo-d34.conf", config / "systemd/user" / SERVICE


def systemctl(*args):
    subprocess.run(["systemctl", "--user", *args], check=True)


def install(app, config, unit):
    if app.exists() and not (app / MARKER).is_file():
        raise ValueError(f"Refusing to overwrite an unrecognized directory: {app}")
    # Copy only runtime sources. A checkout can subsequently be moved or deleted.
    app.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        SRC / "jonsbo_d34",
        app / "jonsbo_d34",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copy2(SRC / "panel.py", app / "panel.py")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, app / name)
    (app / MARKER).write_text("Installed by jonsbo-d34/src/scripts/install.py\n")
    config.parent.mkdir(parents=True, exist_ok=True)
    if not config.exists():
        shutil.copy2(SRC / "packaging/jonsbo-d34.conf", config)
    # Existing configurations remain byte-for-byte intact; defaults cover old files.
    template = (SRC / "packaging/jonsbo-d34.service.in").read_text()
    # EnvironmentFile accepts a single literal path, not ExecStart-style quoting.
    unit_quote(config)  # Validate control characters before inserting the path.
    template = template.replace("@CONFIG@", str(config).replace("%", "%%"))
    for key, value in (("PYTHON", sys.executable), ("APP", app / "panel.py")):
        template = template.replace(f"@{key}@", unit_quote(value))
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text(template)


def uninstall(app, unit):
    if app.exists() and not (app / MARKER).is_file():
        raise ValueError(f"Refusing to remove an unrecognized directory: {app}")
    if unit.exists():
        systemctl("disable", "--now", SERVICE)
        unit.unlink()
    if app.exists():
        shutil.rmtree(app)
    systemctl("daemon-reload")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument(
        "--dry-run", action="store_true", help="Show paths without changing anything"
    )
    args = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required")
    if os.geteuid() == 0:
        parser.error("Run as your desktop user, without sudo")
    try:
        app, config, unit = paths()
        print(f"Application: {app}\nConfiguration: {config}\nUser service: {unit}")
        if args.dry_run:
            return
        if args.action == "install":
            install(app, config, unit)
            systemctl("daemon-reload")
            systemctl("enable", SERVICE)
            systemctl("restart", SERVICE)
            print("Installed and started. Existing configuration was preserved.")
        else:
            uninstall(app, unit)
            print("Uninstalled. Configuration preserved at", config)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
