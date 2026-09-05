# Contributing

Bug fixes, documented hardware results and sensor backends are welcome. Open an
issue before a substantial feature change so its scope and protocol assumptions
can be discussed. Contributions are provided under the project's MIT license.

## Local checks

Runtime code uses only the Python standard library. Development tools are separate:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
PYTHONPATH=src python3 -m unittest discover -s src/tests -v
.venv/bin/python -m build --no-isolation
```

Use `.venv/bin/ruff check --fix .` and `.venv/bin/ruff format .` to apply formatting.
Run `python3 src/scripts/install.py install` with the system Python for real hardware
testing; the installer stores that interpreter's absolute path in the service.

## Layout

```text
src/
  jonsbo_d34/
    cli.py        CLI, locking, signals and reconnect loop
    device.py     USB discovery and descriptor validation
    protocol.py   Pure numeric packet encoder
    sensors.py    Linux readings and CPU-frequency cache
  panel.py        Direct source-checkout entry point
  packaging/      User-service template, config and optional udev rule
  scripts/        Dependency-free user installer/uninstaller
  tests/          Hardware-independent unittest suite
docs/             Protocol, troubleshooting and Russian documentation
```

Only `src/jonsbo_d34` is included in the wheel. Tests run with `PYTHONPATH=src`;
source commands use `python3 src/panel.py` without installing the package.

Keep protocol encoding independent of sensor discovery. Add meaningful regression
tests for protocol changes, sensor selection and error recovery. Do not add USB IDs
on the assumption that visually similar panels share a protocol. Document the
evidence and distinguish host write success from correct physical rendering.

CI runs lint, formatting, unit tests and package builds on Python 3.10–3.14.
Passing CI is not a hardware compatibility claim. Before releasing a hardware
change, record the tested panel and check temperatures, time, frequency, stop/start
and unplug/reconnect behavior on that setup.

## Release preparation

1. Update `src/jonsbo_d34/__init__.py`, `pyproject.toml` and `CHANGELOG.md` together.
2. Run the checks above and inspect the wheel/source archive.
3. Test a fresh user installation and an update preserving existing configuration.
4. Tag a reviewed release and attach the build artifacts through GitHub as needed.

No package upload or release publication happens automatically in CI.
